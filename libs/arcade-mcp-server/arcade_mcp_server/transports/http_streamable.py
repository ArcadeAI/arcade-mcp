"""HTTP Streamable Transport for MCP servers.

This module implements HTTP transport with Server-Sent Events (SSE) streaming support,
following the patterns from the sample library.

Design overview
- The transport provides a duplex, in-process message channel between the HTTP layer
  and the MCP session using anyio memory streams:
  - read side (transport -> session):
    - `_read_stream_writer` (SendStream[SessionMessage | Exception])
    - `_read_stream` (ReceiveStream[SessionMessage | Exception])
  - write side (session -> transport):
    - `_write_stream` (SendStream[SessionMessage])
    - `_write_stream_reader` (ReceiveStream[SessionMessage])

- The transport writes inbound client messages (parsed from HTTP requests) to
  `_read_stream_writer`; the session consumes them from `_read_stream`.

- The session writes outbound server messages to `_write_stream`; the transport's
  `message_router` task consumes them from `_write_stream_reader` and fans them out
  to the correct per-request stream maintained in `_request_streams[request_id]`.

- Response modes:
  - JSON response mode: a single HTTP JSON response is returned by awaiting the
    first terminal message (JSONRPCResponse or JSONRPCError) for the request.
  - SSE response mode: a long-lived stream of events is sent as SSE; the stream
    is closed when a terminal message is observed for the request.

- A standalone GET SSE stream uses the special key `GET_STREAM_KEY` to deliver
  server-initiated events without a preceding POST.

- Optional resumability can be enabled by providing an `EventStore` implementation.
"""

import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import cast

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel, TypeAdapter
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import (
    INTERNAL_ERROR,
    INVALID_REQUEST,
    PARSE_ERROR,
    ErrorData,
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPMessage,
    RequestId,
    SessionMessage,
)

logger = logging.getLogger(__name__)

# Header names
MCP_SESSION_ID_HEADER = "Mcp-Session-Id"
MCP_PROTOCOL_VERSION_HEADER = "MCP-Protocol-Version"
LAST_EVENT_ID_HEADER = "Last-Event-ID"

# Content types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_SSE = "text/event-stream"

# Special key for the standalone GET stream
GET_STREAM_KEY = "_GET_stream"

# Session ID validation pattern (visible ASCII characters)
SESSION_ID_PATTERN = re.compile(r"^[\x21-\x7E]+$")

# Type aliases
StreamId = str
EventId = str


@dataclass
class EventMessage:
    """A JSONRPCMessage with an optional event ID for stream resumability."""

    message: MCPMessage
    event_id: str | None = None


EventCallback = Callable[[EventMessage], Awaitable[None]]


class EventStore:
    """Interface for resumability support via event storage."""

    async def store_event(self, stream_id: StreamId, message: MCPMessage) -> EventId:
        """Store an event for later retrieval."""
        raise NotImplementedError

    async def replay_events_after(
        self,
        last_event_id: EventId,
        send_callback: EventCallback,
    ) -> StreamId | None:
        """Replay events after the specified event ID."""
        raise NotImplementedError


class HTTPStreamableTransport:
    """HTTP transport with SSE streaming support for MCP.

    Responsibilities
    - Parse HTTP requests into JSON-RPC messages and enqueue them on the
      transport→session read stream (via `_read_stream_writer`).
    - Consume session→transport messages from `_write_stream_reader` in a
      background `message_router`, routing them to per-request streams in
      `_request_streams` keyed by the JSON-RPC request id (or `GET_STREAM_KEY`
      for the standalone GET SSE stream).
    - Serve responses back to the HTTP client:
      - JSON response mode: wait for the first terminal response and return a
        single `application/json` body.
      - SSE mode: stream each outbound `SessionMessage` as an SSE event with
        appropriate headers and close on terminal response.

    Streams created in `connect()`
    - `_read_stream_writer` / `_read_stream`: transport→session channel for inbound
      client messages.
    - `_write_stream` / `_write_stream_reader`: session→transport channel for outbound
      server messages, consumed by the `message_router`.

    These in-memory channels provide backpressure and decouple HTTP from the session
    loop while keeping the implementation fully async.
    """

    def __init__(
        self,
        mcp_session_id: str | None,
        session: ServerSession | None = None,
        is_json_response_enabled: bool = False,
        event_store: EventStore | None = None,
    ):
        """Initialize HTTP streamable transport.

        Args:
            mcp_session_id: Session identifier (must be visible ASCII)
            session: Server session for handling requests
            is_json_response_enabled: If True, return JSON responses instead of SSE
            event_store: Optional event store for resumability
        """
        if mcp_session_id and not SESSION_ID_PATTERN.fullmatch(mcp_session_id):
            raise ValueError("Session ID must only contain visible ASCII characters")

        self.mcp_session_id = mcp_session_id
        self.session = session
        self.is_json_response_enabled = is_json_response_enabled
        self._event_store = event_store
        self._request_streams: dict[
            RequestId,
            tuple[MemoryObjectSendStream[EventMessage], MemoryObjectReceiveStream[EventMessage]],
        ] = {}
        self._terminated = False

        # Streams for connection
        self._read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception] | None = None
        self._read_stream: MemoryObjectReceiveStream[SessionMessage | Exception] | None = None
        self._write_stream: MemoryObjectSendStream[str | SessionMessage] | None = None
        self._write_stream_reader: MemoryObjectReceiveStream[str | SessionMessage] | None = None

    def _parse_mcp_message(self, obj: str | dict[str, object] | MCPMessage) -> MCPMessage:
        """Parse incoming data into a typed MCPMessage.

        Accepts a raw JSON string, already-parsed dict, or an existing MCPMessage.
        """
        if isinstance(obj, BaseModel):
            # Already a pydantic model; trust caller and cast to MCPMessage
            return cast(MCPMessage, obj)

        parsed: dict[str, object]
        if isinstance(obj, str):
            try:
                maybe = json.loads(obj)
            except Exception as exc:  # parse error - treat as invalid request
                raise ValueError(f"Invalid JSON: {exc}")
            if not isinstance(maybe, dict):
                raise TypeError("JSON must be an object")
            parsed = maybe
        elif isinstance(obj, dict):
            parsed = obj
        else:
            raise TypeError("Unsupported message type")

        try:
            return TypeAdapter(MCPMessage).validate_python(parsed)
        except Exception:
            # Fallback: treat as error
            return JSONRPCError(
                id=str(parsed.get("id", "null")),
                error={"code": -32600, "message": "Invalid message"},
            )

    @property
    def is_terminated(self) -> bool:
        """Check if transport has been terminated."""
        return self._terminated

    def _create_error_response(
        self,
        error_message: str,
        status_code: HTTPStatus,
        error_code: int = INVALID_REQUEST,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Create an error response."""
        response_headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        }
        if headers:
            response_headers.update(headers)

        if self.mcp_session_id:
            response_headers[MCP_SESSION_ID_HEADER] = self.mcp_session_id

        error_response = JSONRPCError(
            jsonrpc="2.0",
            id="server-error",
            error=ErrorData(code=error_code, message=error_message).model_dump(exclude_none=True),
        )

        return Response(
            error_response.model_dump_json(by_alias=True, exclude_none=True),
            status_code=status_code,
            headers=response_headers,
        )

    def _create_json_response(
        self,
        response_message: JSONRPCMessage | None,
        status_code: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Create a JSON response."""
        response_headers = {"Content-Type": CONTENT_TYPE_JSON}
        if headers:
            response_headers.update(headers)

        if self.mcp_session_id:
            response_headers[MCP_SESSION_ID_HEADER] = self.mcp_session_id

        return Response(
            response_message.model_dump_json(by_alias=True, exclude_none=True)
            if response_message
            else None,
            status_code=status_code,
            headers=response_headers,
        )

    def _get_session_id(self, request: Request) -> str | None:
        """Extract session ID from request headers."""
        return request.headers.get(MCP_SESSION_ID_HEADER)

    def _create_event_data(self, event_message: EventMessage) -> dict[str, str]:
        """Create event data dictionary from EventMessage."""
        event_data = {
            "event": "message",
            "data": event_message.message.model_dump_json(by_alias=True, exclude_none=True),
        }

        if event_message.event_id:
            event_data["id"] = event_message.event_id

        return event_data

    async def _clean_up_memory_streams(self, request_id: RequestId) -> None:
        """Clean up memory streams for a request."""
        if request_id in self._request_streams:
            try:
                await self._request_streams[request_id][0].aclose()
                await self._request_streams[request_id][1].aclose()
            except Exception:
                logger.debug("Error closing memory streams - may already be closed")
            finally:
                self._request_streams.pop(request_id, None)

    async def handle_request(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle incoming HTTP requests."""
        request = Request(scope, receive)

        if self._terminated:
            response = self._create_error_response(
                "Not Found: Session has been terminated",
                HTTPStatus.NOT_FOUND,
            )
            await response(scope, receive, send)
            return

        if request.method == "POST":
            await self._handle_post_request(scope, request, receive, send)
        elif request.method == "GET":
            await self._handle_get_request(request, send)
        elif request.method == "DELETE":
            await self._handle_delete_request(request, send)
        else:
            await self._handle_unsupported_request(request, send)

    def _check_accept_headers(self, request: Request) -> tuple[bool, bool]:
        """Check if request accepts required media types."""
        accept_header = request.headers.get("accept", "")
        accept_types = [media_type.strip() for media_type in accept_header.split(",")]

        has_json = any(media_type.startswith(CONTENT_TYPE_JSON) for media_type in accept_types)
        has_sse = any(media_type.startswith(CONTENT_TYPE_SSE) for media_type in accept_types)

        return has_json, has_sse

    def _check_content_type(self, request: Request) -> bool:
        """Check if request has correct Content-Type."""
        content_type = request.headers.get("content-type", "")
        content_type_parts = [part.strip() for part in content_type.split(";")[0].split(",")]

        return any(part == CONTENT_TYPE_JSON for part in content_type_parts)

    async def _handle_post_request(
        self, scope: Scope, request: Request, receive: Receive, send: Send
    ) -> None:
        """Handle POST requests containing JSON-RPC messages."""
        writer = self._read_stream_writer
        if writer is None:
            raise ValueError("No read stream writer available. Ensure connect() is called first.")

        try:
            # Check Accept headers
            has_json, has_sse = self._check_accept_headers(request)
            if self.is_json_response_enabled:
                if not has_json:
                    response = self._create_error_response(
                        "Not Acceptable: Client must accept application/json",
                        HTTPStatus.NOT_ACCEPTABLE,
                    )
                    await response(scope, receive, send)
                    return
            else:
                if not has_sse:
                    response = self._create_error_response(
                        "Not Acceptable: Client must accept text/event-stream",
                        HTTPStatus.NOT_ACCEPTABLE,
                    )
                    await response(scope, receive, send)
                    return

            # Validate Content-Type for POST payloads only when JSON mode
            if self.is_json_response_enabled and not self._check_content_type(request):
                response = self._create_error_response(
                    "Unsupported Media Type: Content-Type must be application/json",
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                )
                await response(scope, receive, send)
                return

            # Parse the body
            body = await request.body()
            body_str = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)

            try:
                raw_message = json.loads(body)
            except json.JSONDecodeError as e:
                response = self._create_error_response(
                    f"Parse error: {e!s}", HTTPStatus.BAD_REQUEST, PARSE_ERROR
                )
                await response(scope, receive, send)
                return

            # Accept either well-typed messages or raw dicts
            message_dict = raw_message if isinstance(raw_message, dict) else {}
            try:
                message = self._parse_mcp_message(message_dict or body_str)
            except Exception as exc:
                response = self._create_error_response(
                    f"Invalid request: {exc}",
                    HTTPStatus.BAD_REQUEST,
                    INVALID_REQUEST,
                )
                await response(scope, receive, send)
                return

            # Check if this is an initialization request
            # Determine initialization by dict method when validation fallback used
            is_initialization_request = (
                isinstance(message, JSONRPCRequest) and message.method == "initialize"
            )

            if is_initialization_request:
                if self.mcp_session_id:
                    request_session_id = self._get_session_id(request)
                    if request_session_id and request_session_id != self.mcp_session_id:
                        response = self._create_error_response(
                            "Not Found: Invalid or expired session ID",
                            HTTPStatus.NOT_FOUND,
                        )
                        await response(scope, receive, send)
                        return
            elif not await self._validate_request_headers(request, send):
                return

            # Extract resource owner from scope (set by ASGI Resource Server middleware)
            resource_owner = request.scope.get("resource_owner")

            # For notifications and responses, return 202 Accepted
            if not isinstance(message, JSONRPCRequest):
                response = self._create_json_response(None, HTTPStatus.ACCEPTED)
                await response(scope, receive, send)

                # Process the message
                session_message = SessionMessage(
                    message=message,
                    resource_owner=resource_owner,
                )
                await writer.send(session_message)
                return

            # Handle requests
            request_id = str(message.id)
            self._request_streams[request_id] = anyio.create_memory_object_stream[EventMessage](0)
            request_stream_reader = self._request_streams[request_id][1]

            if self.is_json_response_enabled:
                session_message = SessionMessage(
                    message=message,
                    resource_owner=resource_owner,
                )
                await writer.send(session_message)

                try:
                    response_message = None
                    async for event_message in request_stream_reader:
                        if isinstance(event_message.message, (JSONRPCResponse, JSONRPCError)):
                            response_message = event_message.message
                            break

                    if response_message:
                        response = self._create_json_response(response_message)
                        await response(scope, receive, send)
                    else:
                        logger.error("No response received before stream closed")
                        response = self._create_error_response(
                            "Error processing request: No response received",
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                        )
                        await response(scope, receive, send)
                except Exception:
                    logger.exception("Error processing JSON response")
                    response = self._create_error_response(
                        "Error processing request",
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        INTERNAL_ERROR,
                    )
                    await response(scope, receive, send)
                finally:
                    await self._clean_up_memory_streams(request_id)
            else:
                # SSE response mode
                sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[
                    dict[str, str]
                ](0)

                async def sse_writer() -> None:
                    try:
                        async with sse_stream_writer, request_stream_reader:
                            async for event_message in request_stream_reader:
                                event_data = self._create_event_data(event_message)
                                await sse_stream_writer.send(event_data)

                                if isinstance(
                                    event_message.message, (JSONRPCResponse, JSONRPCError)
                                ):
                                    break
                    except Exception:
                        logger.exception("Error in SSE writer")
                    finally:
                        logger.debug("Closing SSE writer")
                        await self._clean_up_memory_streams(request_id)

                headers = {
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "Content-Type": CONTENT_TYPE_SSE,
                    **({MCP_SESSION_ID_HEADER: self.mcp_session_id} if self.mcp_session_id else {}),
                }

                response = EventSourceResponse(
                    content=sse_stream_reader,
                    data_sender_callable=sse_writer,
                    headers=headers,
                )

                try:
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(response, scope, receive, send)
                        # Send SessionMessage object
                        session_message = SessionMessage(
                            message=message,
                            resource_owner=resource_owner,
                        )
                        await writer.send(session_message)
                except Exception:
                    logger.exception("SSE response error")
                    await sse_stream_writer.aclose()
                    await sse_stream_reader.aclose()
                    await self._clean_up_memory_streams(request_id)

        except Exception as err:
            logger.exception("Error handling POST request")
            response = self._create_error_response(
                f"Error handling POST request: {err}",
                HTTPStatus.INTERNAL_SERVER_ERROR,
                INTERNAL_ERROR,
            )
            await response(scope, receive, send)
            if writer:
                await writer.send(Exception(err))

    async def _handle_get_request(self, request: Request, send: Send) -> None:
        """Handle GET request to establish SSE."""
        writer = self._read_stream_writer
        if writer is None:
            raise ValueError("No read stream writer available. Ensure connect() is called first.")

        # Validate Accept header
        _, has_sse = self._check_accept_headers(request)

        if not has_sse:
            error_response = self._create_error_response(
                "Not Acceptable: Client must accept text/event-stream",
                HTTPStatus.NOT_ACCEPTABLE,
            )
            await error_response(request.scope, request.receive, send)
            return

        if not await self._validate_request_headers(request, send):
            return

        # Handle resumability
        if last_event_id := request.headers.get(LAST_EVENT_ID_HEADER):
            await self._replay_events(last_event_id, request, send)
            return

        headers = {
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": CONTENT_TYPE_SSE,
        }

        if self.mcp_session_id:
            headers[MCP_SESSION_ID_HEADER] = self.mcp_session_id

        # Check if we already have an active GET stream
        if GET_STREAM_KEY in self._request_streams:
            error_response = self._create_error_response(
                "Conflict: Only one SSE stream is allowed per session",
                HTTPStatus.CONFLICT,
            )
            await error_response(request.scope, request.receive, send)
            return

        # Create SSE stream
        sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[dict[str, str]](0)

        async def standalone_sse_writer() -> None:
            try:
                self._request_streams[GET_STREAM_KEY] = anyio.create_memory_object_stream[
                    EventMessage
                ](0)
                standalone_stream_reader = self._request_streams[GET_STREAM_KEY][1]

                async with sse_stream_writer, standalone_stream_reader:
                    async for event_message in standalone_stream_reader:
                        event_data = self._create_event_data(event_message)
                        await sse_stream_writer.send(event_data)
            except Exception:
                logger.exception("Error in standalone SSE writer")
            finally:
                logger.debug("Closing standalone SSE writer")
                await self._clean_up_memory_streams(GET_STREAM_KEY)

        sse_response: EventSourceResponse = EventSourceResponse(
            content=sse_stream_reader,
            data_sender_callable=standalone_sse_writer,
            headers=headers,
        )

        try:
            await sse_response(request.scope, request.receive, send)
        except Exception:
            logger.exception("Error in standalone SSE response")
            await sse_stream_writer.aclose()
            await sse_stream_reader.aclose()
            await self._clean_up_memory_streams(GET_STREAM_KEY)

    async def _handle_delete_request(self, request: Request, send: Send) -> None:
        """Handle DELETE requests for session termination."""
        if not self.mcp_session_id:
            response = self._create_error_response(
                "Method Not Allowed: Session termination not supported",
                HTTPStatus.METHOD_NOT_ALLOWED,
            )
            await response(request.scope, request.receive, send)
            return

        if not await self._validate_request_headers(request, send):
            return

        await self.terminate()

        response = self._create_json_response(None, HTTPStatus.OK)
        await response(request.scope, request.receive, send)

    async def terminate(self) -> None:
        """Terminate the current session."""
        self._terminated = True
        logger.info(f"Terminating session: {self.mcp_session_id}")

        # Close all request streams
        request_stream_keys = list(self._request_streams.keys())
        for key in request_stream_keys:
            await self._clean_up_memory_streams(key)
        self._request_streams.clear()

        try:
            if self._read_stream_writer:
                await self._read_stream_writer.aclose()
            if self._read_stream:
                await self._read_stream.aclose()
            if self._write_stream_reader:
                await self._write_stream_reader.aclose()
            if self._write_stream:
                await self._write_stream.aclose()
        except Exception as e:
            logger.debug(f"Error closing streams: {e}")

    async def _handle_unsupported_request(self, request: Request, send: Send) -> None:
        """Handle unsupported HTTP methods."""
        headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Allow": "GET, POST, DELETE",
        }
        if self.mcp_session_id:
            headers[MCP_SESSION_ID_HEADER] = self.mcp_session_id

        response = self._create_error_response(
            "Method Not Allowed",
            HTTPStatus.METHOD_NOT_ALLOWED,
            headers=headers,
        )
        await response(request.scope, request.receive, send)

    async def _validate_request_headers(self, request: Request, send: Send) -> bool:
        """Validate request headers."""
        return await self._validate_session(request, send)

    async def _validate_session(self, request: Request, send: Send) -> bool:
        """Validate session ID in request."""
        if not self.mcp_session_id:
            return True

        request_session_id = self._get_session_id(request)

        if not request_session_id:
            response = self._create_error_response(
                "Bad Request: Missing session ID",
                HTTPStatus.BAD_REQUEST,
            )
            await response(request.scope, request.receive, send)
            return False

        if request_session_id != self.mcp_session_id:
            response = self._create_error_response(
                "Not Found: Invalid or expired session ID",
                HTTPStatus.NOT_FOUND,
            )
            await response(request.scope, request.receive, send)
            return False

        return True

    async def _replay_events(self, last_event_id: str, request: Request, send: Send) -> None:
        """Replay events after the specified event ID."""
        event_store = self._event_store
        if not event_store:
            return

        try:
            headers = {
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Content-Type": CONTENT_TYPE_SSE,
            }

            if self.mcp_session_id:
                headers[MCP_SESSION_ID_HEADER] = self.mcp_session_id

            sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[
                dict[str, str]
            ](0)

            async def replay_sender() -> None:
                try:
                    async with sse_stream_writer:

                        async def send_event(event_message: EventMessage) -> None:
                            event_data = self._create_event_data(event_message)
                            await sse_stream_writer.send(event_data)

                        stream_id = await event_store.replay_events_after(last_event_id, send_event)

                        if stream_id and stream_id not in self._request_streams:
                            self._request_streams[stream_id] = anyio.create_memory_object_stream[
                                EventMessage
                            ](0)
                            msg_reader = self._request_streams[stream_id][1]

                            async with msg_reader:
                                async for event_message in msg_reader:
                                    event_data = self._create_event_data(event_message)
                                    await sse_stream_writer.send(event_data)
                except Exception:
                    logger.exception("Error in replay sender")

            sse_response: EventSourceResponse = EventSourceResponse(
                content=sse_stream_reader,
                data_sender_callable=replay_sender,
                headers=headers,
            )

            try:
                await sse_response(request.scope, request.receive, send)
            except Exception:
                logger.exception("Error in replay response")
            finally:
                await sse_stream_writer.aclose()
                await sse_stream_reader.aclose()

        except Exception:
            logger.exception("Error replaying events")
            error_response = self._create_error_response(
                "Error replaying events",
                HTTPStatus.INTERNAL_SERVER_ERROR,
                INTERNAL_ERROR,
            )
            await error_response(request.scope, request.receive, send)

    @asynccontextmanager
    async def connect(
        self,
    ) -> AsyncIterator[
        tuple[
            MemoryObjectReceiveStream[SessionMessage | Exception],
            MemoryObjectSendStream[str | SessionMessage],
        ]
    ]:
        """Context manager providing read and write streams for connection.

        Creates the in-memory channels used by the transport and starts the
        `message_router` task responsible for routing outbound messages from
        the session to the correct per-request stream (or the standalone GET
        stream identified by `GET_STREAM_KEY`).
        """
        # Create memory streams with buffer
        read_stream_writer, read_stream = anyio.create_memory_object_stream[
            SessionMessage | Exception
        ](100)
        write_stream, write_stream_reader = anyio.create_memory_object_stream[str | SessionMessage](
            100
        )

        # Store the streams
        self._read_stream_writer = read_stream_writer
        self._read_stream = read_stream
        self._write_stream_reader = write_stream_reader
        self._write_stream = write_stream

        # Start message router
        async with anyio.create_task_group() as tg:

            async def message_router() -> None:
                try:
                    async for session_message in write_stream_reader:
                        # Accept either a SessionMessage wrapper or a raw JSON string
                        try:
                            if isinstance(session_message, SessionMessage):
                                message = session_message.message
                            elif isinstance(session_message, str):
                                message = self._parse_mcp_message(session_message)
                            elif isinstance(session_message, BaseModel):
                                message = cast(JSONRPCMessage, session_message)
                            else:
                                logger.error(
                                    f"Unsupported outbound message type: {type(session_message)}"
                                )
                                continue
                        except Exception:
                            logger.exception("Failed to parse outbound message from session")
                            continue
                        target_request_id = None

                        # Check if this is a response
                        if isinstance(message, (JSONRPCResponse, JSONRPCError)):
                            target_request_id = str(message.id)

                        request_stream_id = (
                            target_request_id if target_request_id else GET_STREAM_KEY
                        )

                        # Store event if we have an event store
                        event_id = None
                        if self._event_store:
                            event_id = await self._event_store.store_event(
                                request_stream_id,
                                message,  # type: ignore[arg-type]
                            )
                            logger.debug(f"Stored {event_id} from {request_stream_id}")

                        if request_stream_id in self._request_streams:
                            try:
                                await self._request_streams[request_stream_id][0].send(
                                    EventMessage(message, event_id)  # type: ignore[arg-type]
                                )
                            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                                self._request_streams.pop(request_stream_id, None)
                except Exception:
                    logger.exception("Error in message router")

            tg.start_soon(message_router)

            try:
                yield read_stream, write_stream
            finally:
                for stream_id in list(self._request_streams.keys()):
                    await self._clean_up_memory_streams(stream_id)
                self._request_streams.clear()

                try:
                    await read_stream_writer.aclose()
                    await read_stream.aclose()
                    await write_stream_reader.aclose()
                    await write_stream.aclose()
                except Exception as e:
                    logger.debug(f"Error closing streams: {e}")
