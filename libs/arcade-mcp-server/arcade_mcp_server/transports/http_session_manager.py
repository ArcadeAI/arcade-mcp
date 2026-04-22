"""HTTP Session Manager for MCP servers.

Manages HTTP streaming sessions with optional resumability via event store.
"""

import contextlib
import json
import logging
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Optional
from uuid import uuid4

import anyio
from anyio.abc import TaskStatus
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import InitializationState, ServerSession
from arcade_mcp_server.transports.http_streamable import (
    MCP_PROTOCOL_VERSION_HEADER,
    MCP_SESSION_ID_HEADER,
    EventStore,
    HTTPStreamableTransport,
)
from arcade_mcp_server.types import SUPPORTED_PROTOCOL_VERSIONS

logger = logging.getLogger(__name__)


def _create_transport_error_response(
    status_code: int,
    message: str,
    code: int = -32600,
) -> Response:
    """Create a transport-level error response.

    The body MUST OMIT the id field entirely — transport errors have no
    associated request id. Uses a raw dict, not the JSONRPCError model.
    """
    body = {"jsonrpc": "2.0", "error": {"code": code, "message": message}}
    return Response(
        json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )


def _replay_receive(body: bytes) -> Receive:
    """Return a fresh Receive callable that replays ``body`` as a single
    ``http.request`` message, then yields ``http.disconnect``.

    After the session manager reads and parses the incoming HTTP body (to detect
    ``initialize``), the inner transport creates a new Starlette Request and
    calls ``request.body()`` again. On ASGI servers that do not internally
    buffer (e.g. ``httpx.ASGITransport``), the original receive callable is
    exhausted — the inner call would then hang waiting for more messages.
    This helper lets the outer handler hand the inner handler a receive
    callable that replays the body so the second read succeeds.
    """
    state = {"sent_request": False, "sent_disconnect": False}

    async def receive() -> dict:
        if not state["sent_request"]:
            state["sent_request"] = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        if not state["sent_disconnect"]:
            state["sent_disconnect"] = True
            return {"type": "http.disconnect"}
        # After disconnect, block forever -- the ASGI spec says no further
        # messages are sent after http.disconnect.
        event = anyio.Event()
        await event.wait()
        return {"type": "http.disconnect"}  # unreachable

    return receive


def _validate_origin(request: Request, allowed_origins: list[str] | None) -> Response | None:
    """Validate the Origin header against ``allowed_origins``.

    Returns a 403 Response if invalid, None if OK.
    """
    origin = request.headers.get("origin")

    if origin is None:
        # No Origin header → non-browser client → allow
        return None

    # If allowed_origins is ["*"], allow any
    if allowed_origins is not None and "*" in allowed_origins:
        return None

    # If allowed_origins is None or empty list, reject any Origin
    if allowed_origins is None or len(allowed_origins) == 0:
        return _create_transport_error_response(403, "Forbidden: Origin not allowed", -32600)

    # Check against allowlist
    if origin not in allowed_origins:
        return _create_transport_error_response(403, "Forbidden: Origin not allowed", -32600)

    return None


def _validate_accept_header(request: Request) -> Response | None:
    """Validate Accept header.

    Client MUST include Accept header listing both application/json
    AND text/event-stream. Wildcards satisfy.
    Returns 406 if invalid, None if OK.
    """
    accept = request.headers.get("accept", "")
    accept_types = [t.strip().split(";")[0].strip() for t in accept.split(",")]

    has_json = any(t in ("application/json", "*/*", "application/*") for t in accept_types)
    has_sse = any(t in ("text/event-stream", "*/*", "text/*") for t in accept_types)

    if not (has_json and has_sse):
        return _create_transport_error_response(
            406,
            "Not Acceptable: Client must accept both application/json and text/event-stream",
            -32600,
        )
    return None


def _validate_protocol_version_header(
    request: Request,
    session: ServerSession | None = None,
    *,
    is_stateless: bool = False,
    is_initialize: bool = False,
) -> tuple[Response | None, str | None]:
    """Validate MCP-Protocol-Version header.

    Returns (error_response, version_from_header).
    """
    header_version = request.headers.get(MCP_PROTOCOL_VERSION_HEADER)

    if is_stateless:
        # Stateless: header is REQUIRED
        if header_version is None:
            return (
                _create_transport_error_response(
                    400, "Bad Request: MCP-Protocol-Version header is required in stateless mode"
                ),
                None,
            )
        if header_version not in SUPPORTED_PROTOCOL_VERSIONS:
            return (
                _create_transport_error_response(
                    400, f"Bad Request: Unsupported protocol version: {header_version}"
                ),
                None,
            )
        return None, header_version

    # Stateful mode
    if is_initialize:
        # Initialize IS version negotiation — skip header validation
        return None, header_version

    if header_version is not None:
        if header_version not in SUPPORTED_PROTOCOL_VERSIONS:
            return (
                _create_transport_error_response(
                    400, f"Bad Request: Unsupported protocol version: {header_version}"
                ),
                None,
            )
        # Hardening: if session has negotiated version, header must match
        if (
            session is not None
            and session.negotiated_version is not None
            and header_version != session.negotiated_version
        ):
            return (
                _create_transport_error_response(
                    400,
                    f"Bad Request: MCP-Protocol-Version {header_version} "
                    f"does not match negotiated version {session.negotiated_version}",
                ),
                None,
            )

    return None, header_version


class HTTPSessionManager:
    """Manages HTTP streaming sessions with optional resumability.

    This class abstracts session management, event storage, and request handling
    for HTTP streaming transports. It handles:

    1. Session tracking for clients
    2. Resumability via optional event store
    3. Connection management and lifecycle
    4. Request handling and transport setup

    Important: Only one HTTPSessionManager instance should be created per application.
    The instance cannot be reused after its run() context has completed.
    """

    def __init__(
        self,
        server: MCPServer,
        event_store: Optional[EventStore] = None,
        json_response: bool = False,
        stateless: bool = False,
    ):
        """Initialize HTTP session manager.

        Args:
            server: The MCP server instance
            event_store: Optional event store for resumability
            json_response: Whether to use JSON responses instead of SSE
            stateless: If True, creates fresh transport for each request
        """
        self.server = server
        self.event_store = event_store
        self.json_response = json_response
        self.stateless = stateless

        # Session tracking (only used if not stateless)
        self._session_creation_lock = anyio.Lock()
        self._server_instances: dict[str, HTTPStreamableTransport] = {}

        # Task group will be set during lifespan
        self._task_group: Optional[anyio.abc.TaskGroup] = None

        # Thread-safe tracking of run() calls
        self._run_lock = anyio.Lock()
        self._has_started = False

    @contextlib.asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Run the session manager with lifecycle management.

        This creates and manages the task group for all session operations.

        Important: This method can only be called once per instance.
        Create a new instance if you need to restart.
        """
        async with self._run_lock:
            if self._has_started:
                raise RuntimeError(
                    "HTTPSessionManager.run() can only be called once per instance. "
                    "Create a new instance if you need to run again."
                )
            self._has_started = True

        async with anyio.create_task_group() as tg:
            self._task_group = tg
            logger.info("HTTP session manager started")
            try:
                yield
            finally:
                logger.info("HTTP session manager shutting down")
                tg.cancel_scope.cancel()
                self._task_group = None
                self._server_instances.clear()

    async def handle_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process ASGI request with proper session handling.

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if self._task_group is None:
            raise RuntimeError("Task group is not initialized. Make sure to use run().")

        request = Request(scope, receive)

        # --- Origin validation (ALL methods, before anything else) ---
        allowed_origins = getattr(self.server, "allowed_origins", None)
        origin_error = _validate_origin(request, allowed_origins)
        if origin_error is not None:
            await origin_error(scope, receive, send)
            return

        # --- Handle OPTIONS (CORS preflight) ---
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "*")
            cors_origin = (
                origin
                if (allowed_origins and "*" in allowed_origins)
                else (origin if allowed_origins and origin in allowed_origins else "*")
            )
            response = Response(
                content=None,
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": cors_origin,
                    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id, MCP-Protocol-Version",
                    "Access-Control-Max-Age": "86400",
                },
            )
            await response(scope, receive, send)
            return

        if self.stateless:
            await self._handle_stateless_request(scope, receive, send)
        else:
            await self._handle_stateful_request(scope, receive, send)

    async def _handle_stateless_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process request in stateless mode - new transport per request."""
        request = Request(scope, receive)

        # --- Detect if this is an initialize request ---
        is_initialize = False
        body_bytes: bytes | None = None
        if request.method == "POST":
            try:
                body_bytes = await request.body()
                raw = json.loads(body_bytes) if body_bytes else {}
                is_initialize = isinstance(raw, dict) and raw.get("method") == "initialize"
            except Exception:  # noqa: S110
                pass

        # Replay the body for the inner transport so ASGI servers that do not
        # buffer receive() (e.g. httpx.ASGITransport) can still read the body.
        inner_receive: Receive = _replay_receive(body_bytes) if body_bytes is not None else receive

        # --- Accept header validation (POST only, skip initialize) ---
        if request.method == "POST" and not is_initialize:
            accept_error = _validate_accept_header(request)
            if accept_error is not None:
                await accept_error(scope, receive, send)
                return

        # --- Protocol version header validation (required in stateless) ---
        version_error, header_version = _validate_protocol_version_header(
            request, is_stateless=True
        )
        if version_error is not None:
            await version_error(scope, receive, send)
            return

        # --- Stateless version conflict check for initialize ---
        if is_initialize and header_version:
            try:
                raw = json.loads(body_bytes) if body_bytes else {}
                init_version = raw.get("params", {}).get("protocolVersion")
                if init_version and init_version != header_version:
                    error_resp = _create_transport_error_response(
                        400,
                        "Bad Request: MCP-Protocol-Version header conflicts with initialize protocolVersion",
                    )
                    await error_resp(scope, receive, send)
                    return
            except Exception:  # noqa: S110
                pass

        logger.debug("Stateless mode: Creating new transport for this request")

        # Create transport without session ID in stateless mode
        http_transport = HTTPStreamableTransport(
            mcp_session_id=None,
            is_json_response_enabled=self.json_response,
            event_store=None,  # No event store in stateless mode
        )

        # Start server in a new task
        async def run_stateless_server(
            *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED
        ) -> None:
            async with http_transport.connect() as streams:
                read_stream, write_stream = streams
                task_status.started()
                try:
                    # Create a new session for this request
                    session = ServerSession(
                        server=self.server,
                        read_stream=read_stream,
                        write_stream=write_stream,
                        init_options={"transport_type": "http"},
                        stateless=True,
                    )

                    # --- Stateless auto-initialize ---
                    if header_version:
                        session.negotiated_version = header_version
                        session._negotiated_capabilities = self.server._build_capabilities(
                            version=header_version, stateless=True
                        )
                        session.initialization_state = InitializationState.INITIALIZED

                    # Set the session on the transport
                    http_transport.session = session

                    # Run the session (start + loop until closed)
                    await session.run()

                    # Brief yield to allow cleanup
                    await anyio.sleep(0)
                except Exception:
                    logger.exception("Stateless session crashed")

        if self._task_group is None:
            raise RuntimeError("Task group not initialized")
        await self._task_group.start(run_stateless_server)

        # Handle the HTTP request (replay body so inner Request() can read it)
        await http_transport.handle_request(scope, inner_receive, send)

        # Terminate the transport
        await http_transport.terminate()

    async def _handle_stateful_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process request in stateful mode - maintain session state."""
        request = Request(scope, receive)
        request_mcp_session_id = request.headers.get(MCP_SESSION_ID_HEADER)

        # --- Detect if this is an initialize request ---
        is_initialize = False
        body_bytes: bytes | None = None
        if request.method == "POST" and request_mcp_session_id is None:
            try:
                body_bytes = await request.body()
                raw = json.loads(body_bytes) if body_bytes else {}
                is_initialize = isinstance(raw, dict) and raw.get("method") == "initialize"
            except Exception:  # noqa: S110
                pass

        # If we consumed the body, provide a replay receive so the inner
        # transport (which creates its own Request and calls .body()) can
        # still read it on ASGI hosts that don't buffer receive().
        inner_receive: Receive = _replay_receive(body_bytes) if body_bytes is not None else receive

        # --- Accept header validation (POST only, skip initialize) ---
        if request.method == "POST" and not is_initialize:
            accept_error = _validate_accept_header(request)
            if accept_error is not None:
                await accept_error(scope, receive, send)
                return

        # --- Protocol version header validation ---
        # Find the session for the transport (if existing)
        session: ServerSession | None = None
        if request_mcp_session_id and request_mcp_session_id in self._server_instances:
            transport = self._server_instances[request_mcp_session_id]
            session = transport.session

        version_error, _ = _validate_protocol_version_header(
            request, session=session, is_initialize=is_initialize
        )
        if version_error is not None:
            await version_error(scope, receive, send)
            return

        # Existing session case
        if request_mcp_session_id and request_mcp_session_id in self._server_instances:
            transport = self._server_instances[request_mcp_session_id]
            logger.debug("Session already exists, handling request directly")
            await transport.handle_request(scope, inner_receive, send)
            return

        if request_mcp_session_id is None:
            # New session case
            logger.debug("Creating new transport")
            async with self._session_creation_lock:
                new_session_id = uuid4().hex
                http_transport = HTTPStreamableTransport(
                    mcp_session_id=new_session_id,
                    is_json_response_enabled=self.json_response,
                    event_store=self.event_store,
                )

                if http_transport.mcp_session_id is None:
                    raise RuntimeError("MCP session ID not set")
                self._server_instances[http_transport.mcp_session_id] = http_transport
                logger.info(f"Created new transport with session ID: {new_session_id}")

                # Define the server runner
                async def run_server(
                    *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED
                ) -> None:
                    async with http_transport.connect() as streams:
                        read_stream, write_stream = streams
                        task_status.started()
                        try:
                            # Create a session for this connection
                            session = ServerSession(
                                server=self.server,
                                read_stream=read_stream,
                                write_stream=write_stream,
                                init_options={"transport_type": "http"},
                            )

                            # Set the session on the transport
                            http_transport.session = session

                            # Run the session (start + loop until closed)
                            await session.run()

                            # Brief yield to allow cleanup
                            await anyio.sleep(0)
                        except Exception as e:
                            logger.error(
                                f"Session {http_transport.mcp_session_id} crashed: {e}",
                                exc_info=True,
                            )
                        finally:
                            # Clean up on crash
                            if (
                                http_transport.mcp_session_id
                                and http_transport.mcp_session_id in self._server_instances
                                and not http_transport.is_terminated
                            ):
                                logger.info(
                                    f"Cleaning up crashed session {http_transport.mcp_session_id}"
                                )
                                del self._server_instances[http_transport.mcp_session_id]

                if self._task_group is None:
                    raise RuntimeError("Task group not initialized")
                await self._task_group.start(run_server)

                # Handle the HTTP request (replay body so inner Request() can
                # read it on ASGI hosts that do not buffer receive()).
                await http_transport.handle_request(scope, inner_receive, send)
        else:
            # Invalid session ID
            response = Response(
                "Bad Request: No valid session ID provided",
                status_code=HTTPStatus.BAD_REQUEST,
            )
            await response(scope, receive, send)
