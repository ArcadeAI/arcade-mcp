"""
MCP Server Session

Manages per-session state and provides session-level operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from enum import Enum
from typing import Any

import anyio

from arcade_mcp_server.context import Context
from arcade_mcp_server.exceptions import (
    ElicitationModeNotSupportedError,
    ElicitationNotSupportedError,
    RequestError,
    SessionError,
    SessionNotInitializedError,
)
from arcade_mcp_server.resource_server.base import ResourceOwner
from arcade_mcp_server.types import (
    CancelledNotification,
    CancelledParams,
    ClientCapabilities,
    CompleteResult,
    CreateMessageResult,
    ElicitResult,
    InitializeParams,
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCRequest,
    ListRootsResult,
    LoggingLevel,
    LoggingMessageNotification,
    LoggingMessageParams,
    ProgressNotification,
    ProgressNotificationParams,
    PromptListChangedNotification,
    ResourceListChangedNotification,
    SessionMessage,
    ToolListChangedNotification,
)

logger = logging.getLogger(__name__)


class InitializationState(Enum):
    """Session initialization states."""

    NOT_INITIALIZED = 1
    INITIALIZING = 2
    INITIALIZED = 3


class RequestManager:
    """
    Manages server-initiated requests to the client.

    Handles request/response correlation for bidirectional communication.
    """

    def __init__(self, write_stream: Any):
        """Initialize request manager."""
        self._write_stream = write_stream
        self._pending_requests: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()
        self._closed = asyncio.Event()

    def is_closed(self) -> bool:
        """Return True if the manager has been closed/cancelled."""
        return self._closed.is_set()

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 400.0,
    ) -> Any:
        """
        Send a request to the client and wait for response.

        Args:
            method: Request method
            params: Request parameters
            timeout: Request timeout in seconds

        Returns:
            Response result

        Raises:
            MCPTimeoutError: If request times out
            ProtocolError: If response is an error
        """
        if self._closed.is_set():
            raise SessionError("Session closed")
        request_id = str(uuid.uuid4())

        # Create request
        request = JSONRPCRequest(
            id=request_id,
            method=method,
            params=params or {},
        )

        # Create future for response
        future: asyncio.Future[Any] = asyncio.Future()
        async with self._lock:
            if self._closed.is_set():
                raise SessionError("Session closed")
            self._pending_requests[request_id] = future

        try:
            # Send request
            message = request.model_dump_json(exclude_none=True) + "\n"
            logger.debug(f"Sending server->client request method={method} id={request_id}")
            await self._write_stream.send(message)

            # Wait for response
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.debug(f"Received response for id={request_id} method={method}")
            return result

        finally:
            # Clean up
            async with self._lock:
                self._pending_requests.pop(request_id, None)

    async def handle_response(self, message: dict[str, Any]) -> None:
        """
        Handle a response message from the client.

        Args:
            message: Response message
        """
        if self._closed.is_set():
            # Drop any late responses after closure
            return
        request_id = message.get("id")
        if not request_id:
            logger.debug("Received response without id; ignoring")
            return

        async with self._lock:
            future = self._pending_requests.get(str(request_id))
        if future and not future.done():
            if "error" in message:
                logger.debug(f"Response id={request_id} contains error; propagating")
                future.set_exception(RequestError(f"Request failed: {message['error']}"))
            else:
                logger.debug(f"Correlated response id={request_id} -> completing future")
                future.set_result(message.get("result"))
        else:
            logger.debug(
                f"No pending future for response id={request_id}; possibly late or mismatched"
            )

    async def cancel_all(self, reason: str | None = None) -> None:
        """Cancel all pending requests and notify the client.

        Sends a CancelledNotification for each in-flight request and
        completes their futures with SessionError so awaiters unblock.
        """
        # Mark closed first to prevent new requests
        if not self._closed.is_set():
            self._closed.set()
        # Snapshot current pending ids and futures
        async with self._lock:
            pending_items = list(self._pending_requests.items())
            # Clear the map eagerly to prevent races with late responses
            self._pending_requests.clear()

        if not pending_items:
            return

        # Best-effort notify client of cancellations
        notifications = []
        for request_id, _future in pending_items:
            notification = CancelledNotification(
                params=CancelledParams(requestId=request_id, reason=reason)
            )
            notifications.append(notification)

        try:
            for note in notifications:
                message = note.model_dump_json(exclude_none=True, by_alias=True) + "\n"
                await self._write_stream.send(message)
        except Exception:
            # Swallow transport errors during shutdown; proceed to cancel futures
            logging.debug(
                "Failed to send cancellation notifications during shutdown", exc_info=True
            )

        # Cancel futures so any waiters are released
        for _request_id, future in pending_items:
            if not future.done():
                future.set_exception(SessionError("Session closed"))


class NotificationManager:
    """Broadcasts server-initiated listChanged notifications to sessions."""

    def __init__(self, server: Any):
        self._server = server

    async def _broadcast(
        self, notification: JSONRPCMessage, session_ids: list[str] | None = None
    ) -> None:
        # Do not broadcast before server is started
        if not getattr(self._server, "_started", False):
            return
        async with self._server._sessions_lock:
            if session_ids is None:
                sessions = list(self._server._sessions.values())
            else:
                sessions = [
                    self._server._sessions.get(sid)
                    for sid in session_ids
                    if sid in self._server._sessions
                ]
        for s in sessions:
            if s is None:
                continue
            try:
                await s.send_notification(notification)
            except Exception:
                logger.debug("Failed to notify a session", exc_info=True)

    async def notify_tool_list_changed(self, session_ids: list[str] | None = None) -> None:
        await self._broadcast(ToolListChangedNotification(), session_ids)

    async def notify_resource_list_changed(self, session_ids: list[str] | None = None) -> None:
        await self._broadcast(ResourceListChangedNotification(), session_ids)

    async def notify_prompt_list_changed(self, session_ids: list[str] | None = None) -> None:
        await self._broadcast(PromptListChangedNotification(), session_ids)


class ServerSession:
    """
    MCP server session handling a single client connection.

    Manages:
    - Session state and lifecycle
    - Client capabilities
    - Request/response handling
    - Notification sending
    """

    def __init__(
        self,
        server: Any,
        session_id: str | None = None,
        read_stream: Any | None = None,
        write_stream: Any | None = None,
        init_options: Any | None = None,
        stateless: bool = False,
    ):
        """
        Initialize server session.

        Args:
            server: Parent server instance
            session_id: Session identifier (generated if not provided)
            read_stream: Stream for reading messages
            write_stream: Stream for writing messages
            init_options: Initialization options
            stateless: Whether session is stateless
        """
        self.server = server
        self.session_id = session_id or str(uuid.uuid4())
        self.read_stream = read_stream
        self.write_stream = write_stream
        self.init_options = init_options or {}
        self.stateless = stateless

        # Session state
        self.initialization_state = InitializationState.NOT_INITIALIZED
        self.client_params: InitializeParams | None = None
        self._session_data: dict[str, Any] = {}

        # Version negotiation state (set during initialize)
        self.negotiated_version: str | None = None
        self._negotiated_capabilities: dict[str, Any] = {}

        # Client capabilities (set during initialize)
        self._client_capabilities: ClientCapabilities | None = None

        # Request management
        self._request_manager = RequestManager(write_stream) if write_stream else None

        # Context for current request
        self._current_context: Context | None = None

    def supports_version(self, version: str) -> bool:
        """Whether negotiated version includes all features of the given version.
        Uses feature-set subset check -- NOT lexical string comparison."""
        from arcade_mcp_server.types import VERSION_FEATURES

        if self.negotiated_version is None:
            return False
        negotiated_features = VERSION_FEATURES.get(self.negotiated_version, set())
        required_features = VERSION_FEATURES.get(version, set())
        return required_features.issubset(negotiated_features)

    def has_feature(self, feature: str) -> bool:
        """Whether negotiated version supports a specific feature."""
        from arcade_mcp_server.types import version_has_feature

        if self.negotiated_version is None:
            return False
        return version_has_feature(self.negotiated_version, feature)

    def has_capability(self, dotted_name: str) -> bool:
        """Check if a nested sub-capability was negotiated (dot notation).

        has_capability("tasks") -> capabilities["tasks"] exists
        has_capability("tasks.list") -> capabilities["tasks"]["list"] exists
        """
        parts = dotted_name.split(".")
        current: Any = self._negotiated_capabilities
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def set_client_params(self, params: InitializeParams) -> None:
        """Set client initialization parameters."""
        self.client_params = params
        # Extract client capabilities (params may be a dict in tests)
        if isinstance(params, dict):
            caps = params.get("capabilities")  # type: ignore[union-attr]
            if isinstance(caps, ClientCapabilities):
                self._client_capabilities = caps
            elif isinstance(caps, dict):
                self._client_capabilities = ClientCapabilities(**caps)
        elif hasattr(params, "capabilities"):
            self._client_capabilities = params.capabilities
        self.initialization_state = InitializationState.INITIALIZING

    def mark_initialized(self) -> None:
        """Mark session as initialized."""
        self.initialization_state = InitializationState.INITIALIZED

    def check_client_capability(self, capability: ClientCapabilities) -> bool:
        """
        Check if client has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if client has capability
        """
        if not self.client_params or not self.client_params.capabilities:
            return False

        client_caps = self.client_params.capabilities

        # Check specific capabilities
        # Use hasattr to check for attributes that might be in extra fields
        if (
            hasattr(capability, "tools")
            and capability.tools
            and not (hasattr(client_caps, "tools") and client_caps.tools)
        ):
            return False
        if (
            hasattr(capability, "resources")
            and capability.resources
            and not (hasattr(client_caps, "resources") and client_caps.resources)
        ):
            return False
        if (
            hasattr(capability, "prompts")
            and capability.prompts
            and not (hasattr(client_caps, "prompts") and client_caps.prompts)
        ):
            return False
        return not (
            hasattr(capability, "logging")
            and capability.logging
            and not (hasattr(client_caps, "logging") and client_caps.logging)
        )

    async def run(self) -> None:
        """
        Run the session message loop.

        Reads messages from the stream and processes them concurrently
        to allow server-initiated requests to be handled while tools execute.
        """
        if not self.read_stream:
            raise SessionError("No read stream available")

        async with anyio.create_task_group() as tg:
            try:
                async for message in self.read_stream:
                    if message:
                        # Process messages concurrently so the loop can continue reading
                        tg.start_soon(self._process_message, message)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                await self.server.logger.exception("Session error")
                raise SessionError(f"Session error: {e}") from e
            finally:
                # Cleanup
                if self._request_manager:
                    # Cancel any pending requests
                    await self._cleanup_pending_requests()

    async def _process_message(self, message: str | Any) -> None:
        """Process a single message.

        Args:
            message: Either a JSON string (stdio) or SessionMessage object (http)
        """
        try:
            if isinstance(message, str):
                data = json.loads(message)
                resource_owner = None
            elif isinstance(message, SessionMessage):
                # We must keep exclude_none=True to avoid Pydantic union type coersion
                # when reconstructing models from dict (e.g., RequestId = str | int)
                data = message.message.model_dump(exclude_none=True)
                resource_owner = message.resource_owner
            else:
                logger.error(f"Unexpected message type: {type(message)}")
                return

            # Check if it's a response to our request
            if "id" in data and "method" not in data:
                if self._request_manager:
                    logger.debug(
                        f"Session received response message id={data.get('id')} -> routing to RequestManager"
                    )
                    await self._request_manager.handle_response(data)
                return

            # Otherwise, process as incoming request
            response = await self.server.handle_message(data, self, resource_owner=resource_owner)

            # Send response if any
            if response and self.write_stream:
                if hasattr(response, "model_dump_json"):
                    if isinstance(response, JSONRPCError):
                        # §5.1: error responses MUST include "id" even when null
                        response_data = response.model_dump_json(by_alias=True)
                    else:
                        response_data = response.model_dump_json(exclude_none=True, by_alias=True)
                else:
                    response_data = json.dumps(response)

                if not response_data.endswith("\n"):
                    response_data += "\n"

                await self.write_stream.send(response_data)

        except json.JSONDecodeError:
            await self._send_error_response(
                None,
                -32700,
                "Parse error",
            )
        except Exception as e:
            await self._send_error_response(
                None,
                -32603,
                (
                    f"✗ Internal server error\n\n"
                    f"  An unexpected error occurred: {e!s}\n\n"
                    f"  To troubleshoot:\n"
                    f"  1. Check server logs for detailed information\n"
                    f"  2. Verify the message format is correct\n"
                    f"  3. Try the request again\n\n"
                    f"  The error has been logged."
                ),
            )

    async def _send_error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
    ) -> None:
        """Send an error response."""
        if not self.write_stream:
            return

        error_response = JSONRPCError(
            id=request_id,
            error={"code": code, "message": message},
        )

        # §5.1: error responses MUST include "id" even when null
        response_data = error_response.model_dump_json(by_alias=True) + "\n"
        await self.write_stream.send(response_data)

    async def _cleanup_pending_requests(self) -> None:
        """Clean up any pending requests."""
        if self._request_manager:
            # Cancel all pending futures and notify client
            await self._request_manager.cancel_all(reason="Session closed")

    # Notification methods
    async def send_notification(self, notification: JSONRPCMessage) -> None:
        """Send a notification to the client."""
        if not self.write_stream:
            return

        # by_alias=True ensures Pydantic Field aliases (e.g. meta -> _meta) are
        # serialized using the wire-format keys required by the MCP spec.
        message = notification.model_dump_json(exclude_none=True, by_alias=True) + "\n"
        await self.write_stream.send(message)

    async def send_progress_notification(
        self,
        progress_token: str | int,
        progress: float,
        total: float | None = None,
        message: str | None = None,
        _meta: dict[str, Any] | None = None,
    ) -> None:
        """Send a progress notification."""
        notification = ProgressNotification(
            params=ProgressNotificationParams(
                progressToken=progress_token,
                progress=progress,
                total=total,
                message=message,
                meta=_meta,
            )
        )
        await self.send_notification(notification)

    async def send_log_message(
        self,
        level: LoggingLevel,
        data: Any,
        logger: str | None = None,
    ) -> None:
        """Send a log message notification."""
        notification = LoggingMessageNotification(
            params=LoggingMessageParams(
                level=level,
                data=data,
                logger=logger,
            )
        )
        await self.send_notification(notification)

    async def send_tool_list_changed(self) -> None:
        """Send tool list changed notification."""
        await self.send_notification(ToolListChangedNotification())

    async def send_resource_list_changed(self) -> None:
        """Send resource list changed notification."""
        await self.send_notification(ResourceListChangedNotification())

    async def send_prompt_list_changed(self) -> None:
        """Send prompt list changed notification."""
        await self.send_notification(PromptListChangedNotification())

    # Server-initiated requests
    async def create_message(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        system_prompt: str | None = None,
        include_context: str | None = None,
        temperature: float | None = None,
        model_preferences: dict[str, Any] | None = None,
        stop_sequences: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        _meta: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> CreateMessageResult:
        """
        Send a sampling request to the client.

        Args:
            messages: Messages to sample
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt
            include_context: Context to include
            temperature: Sampling temperature
            model_preferences: Model preferences
            stop_sequences: Stop sequences
            metadata: Request metadata
            tools: Tools available for the model (2025-11-25 only)
            tool_choice: Tool choice mode (2025-11-25 only)
            timeout: Request timeout

        Returns:
            Sampling result
        """
        if not self._request_manager:
            raise SessionError("Cannot send requests without request manager")

        if self.initialization_state != InitializationState.INITIALIZED:
            raise SessionNotInitializedError(
                "Cannot send sampling request before session is initialized"
            )

        # Determine if the client supports tools in sampling
        client_has_sampling_tools = False
        if self.negotiated_version == "2025-11-25":
            client_caps = self._client_capabilities
            if (
                client_caps is not None
                and isinstance(client_caps.sampling, dict)
                and "tools" in client_caps.sampling
            ):
                client_has_sampling_tools = True

        # Tools are only included if both caller passed them AND client supports them
        tools_allowed = tools is not None and client_has_sampling_tools

        # Validate message content for tool_use/tool_result constraints
        # (only relevant for 2025-11-25 sessions with sampling.tools capability)
        if client_has_sampling_tools:
            self._validate_sampling_messages(messages)

        # Gate includeContext on client capability
        if (
            include_context is not None
            and include_context != "none"
            and self.negotiated_version == "2025-11-25"
        ):
            client_caps = self._client_capabilities
            context_allowed = (
                client_caps is not None
                and isinstance(client_caps.sampling, dict)
                and "context" in client_caps.sampling
            )
            if not context_allowed:
                include_context = None  # strip it

        params: dict[str, Any] = {
            "messages": messages,
            "maxTokens": max_tokens,
        }

        # Add optional parameters
        if system_prompt is not None:
            params["systemPrompt"] = system_prompt
        if include_context is not None:
            params["includeContext"] = include_context
        if temperature is not None:
            params["temperature"] = temperature
        if model_preferences is not None:
            params["modelPreferences"] = model_preferences
        if stop_sequences is not None:
            params["stopSequences"] = stop_sequences
        if metadata is not None:
            params["metadata"] = metadata

        # Include tools/toolChoice only when allowed
        if tools_allowed and tools is not None:
            params["tools"] = tools
            if tool_choice is not None:
                params["toolChoice"] = tool_choice

        # Attach _meta if provided (e.g. related-task meta from background tasks)
        if _meta is not None:
            params["_meta"] = _meta

        result = await self._request_manager.send_request(
            "sampling/createMessage",
            params,
            timeout,
        )

        return CreateMessageResult(**result)

    @staticmethod
    def _validate_sampling_messages(messages: list[dict[str, Any]]) -> None:
        """Validate message content for tool_use/tool_result constraints.

        - User messages with tool_result content must contain ONLY tool results.
        - Every assistant message with tool_use must be followed by a user message
          with only tool_result content blocks.
        """
        for i, msg in enumerate(messages):
            content = msg.get("content")
            if content is None:
                continue

            # Normalize to list
            blocks = content if isinstance(content, list) else [content]

            role = msg.get("role")

            # Check: user messages with any tool_result must be ALL tool_result
            if role == "user":
                has_tool_result = any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks
                )
                if has_tool_result:
                    all_tool_result = all(
                        isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks
                    )
                    if not all_tool_result:
                        raise ValueError(
                            "user messages with tool results must contain only tool results"
                        )

            # Check: assistant messages with tool_use must be followed by user
            # message with all tool_result blocks
            if role == "assistant":
                has_tool_use = any(
                    isinstance(b, dict) and b.get("type") == "tool_use" for b in blocks
                )
                if has_tool_use:
                    if i + 1 >= len(messages):
                        raise ValueError(
                            "assistant message with tool_use must be followed by a "
                            "user message containing tool result blocks"
                        )
                    next_msg = messages[i + 1]
                    next_role = next_msg.get("role")
                    next_content = next_msg.get("content")
                    next_blocks = (
                        next_content
                        if isinstance(next_content, list)
                        else [next_content]
                        if next_content is not None
                        else []
                    )
                    if next_role != "user" or not all(
                        isinstance(b, dict) and b.get("type") == "tool_result" for b in next_blocks
                    ):
                        raise ValueError(
                            "assistant message with tool_use must be followed by a "
                            "user message containing tool result blocks"
                        )

    async def list_roots(self, timeout: float = 60.0) -> ListRootsResult:
        """
        Request roots list from the client.

        Args:
            timeout: Request timeout

        Returns:
            Roots list result
        """
        if not self._request_manager:
            raise SessionError("Cannot send requests without request manager")

        result = await self._request_manager.send_request(
            "roots/list",
            None,
            timeout,
        )

        return ListRootsResult(**result)

    async def complete(
        self,
        ref: dict[str, Any],
        argument: dict[str, Any],
        timeout: float = 60.0,
    ) -> CompleteResult:
        """
        Request completion from the client.

        Args:
            ref: Completion reference
            argument: Completion argument
            timeout: Request timeout

        Returns:
            Completion result
        """
        if not self._request_manager:
            raise SessionError("Cannot send requests without request manager")

        result = await self._request_manager.send_request(
            "completion/complete",
            {"ref": ref, "argument": argument},
            timeout,
        )

        return CompleteResult(**result)

    def _check_elicitation_capability(self, mode: str) -> None:
        """Check that the client supports the requested elicitation mode.

        Spec elicitation.mdx:72: "Servers MUST NOT send elicitation requests
        with modes that are not supported by the client."

        Rules:
        - client_capabilities is None (e.g. tests, 2025-06-18 without caps): allow form
        - client declared caps but no "elicitation" key: forbid all
        - elicitation: {} (empty dict): default to form-only
        - elicitation: {form: {}} : form allowed, url rejected
        - elicitation: {url: {}} : url allowed, form rejected
        - elicitation: {form: {}, url: {}}: both allowed
        """
        client_caps = self._client_capabilities

        # Get elicitation capability value
        elicitation_cap: Any = None
        if client_caps is not None:
            if isinstance(client_caps, ClientCapabilities):
                elicitation_cap = client_caps.elicitation
            elif isinstance(client_caps, dict):
                elicitation_cap = client_caps.get("elicitation")
            else:
                elicitation_cap = getattr(client_caps, "elicitation", None)

        # If client declared capabilities but elicitation is absent -> forbid all
        if client_caps is not None and elicitation_cap is None:
            raise ElicitationNotSupportedError("Client did not declare elicitation capability")

        # client_caps is None (tests / legacy) -> allow form only
        if client_caps is None:
            if mode == "url":
                raise ElicitationModeNotSupportedError(
                    "URL elicitation mode not supported: no client capabilities declared"
                )
            return

        # Normalize to dict
        if hasattr(elicitation_cap, "model_dump"):
            elicitation_cap = elicitation_cap.model_dump(exclude_none=True)

        # At this point elicitation_cap is a dict (possibly empty)
        if not isinstance(elicitation_cap, dict):
            elicitation_cap = {}

        if mode == "url":
            if "url" not in elicitation_cap:
                raise ElicitationModeNotSupportedError(
                    "Client does not support URL elicitation mode"
                )
        else:
            # form mode (default)
            # Empty dict -> default to form support (spec)
            # URL-only (only "url" key, no "form") -> form rejected
            if elicitation_cap and "form" not in elicitation_cap and "url" in elicitation_cap:
                raise ElicitationModeNotSupportedError(
                    "Client only supports URL elicitation mode, not form"
                )

    async def elicit(
        self,
        message: str,
        requested_schema: dict[str, Any] | None = None,
        mode: str | None = None,
        url: str | None = None,
        elicitation_id: str | None = None,
        _meta: dict[str, Any] | None = None,
        timeout: float = 300.0,
    ) -> ElicitResult:
        """
        Send an elicitation request to the client.

        Args:
            message: Elicitation message to display
            requested_schema: JSON schema for the requested response (form mode)
            mode: Elicitation mode - "form" (default) or "url" (2025-11-25 only)
            url: URL for URL-mode elicitation
            elicitation_id: Elicitation ID for URL-mode elicitation
            timeout: Request timeout

        Returns:
            Elicitation result
        """
        if not self._request_manager:
            raise SessionError("Cannot send requests without request manager")

        if self.initialization_state != InitializationState.INITIALIZED:
            raise SessionNotInitializedError(
                "Cannot send elicitation request before session is initialized"
            )

        # Default to form mode
        effective_mode = mode or "form"

        # Version gate: URL mode requires 2025-11-25
        if effective_mode == "url" and self.negotiated_version != "2025-11-25":
            raise SessionError("URL elicitation mode requires protocol version 2025-11-25")

        # URL mode validation
        if effective_mode == "url" and (not url or not elicitation_id):
            raise ValueError("URL mode elicitation requires both 'url' and 'elicitation_id'")

        # Capability gate
        self._check_elicitation_capability(effective_mode)

        if effective_mode == "url":
            params: dict[str, Any] = {
                "mode": "url",
                "url": url,
                "elicitationId": elicitation_id,
                "message": message,
            }
        else:
            params = {
                "message": message,
            }
            if requested_schema is not None:
                params["requestedSchema"] = requested_schema

        # Attach _meta if provided (e.g. related-task meta from background tasks)
        if _meta is not None:
            params["_meta"] = _meta

        result = await self._request_manager.send_request(
            "elicitation/create",
            params,
            timeout,
        )

        return ElicitResult(**result)

    async def send_elicitation_complete(self, elicitation_id: str) -> None:
        """Send a notifications/elicitation/complete notification to this session's client.

        This MUST be sent only to the client that initiated the elicitation
        (elicitation.mdx:398), NOT broadcast to all sessions.
        """
        if not self.write_stream:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/elicitation/complete",
            "params": {"elicitationId": elicitation_id},
        }
        try:
            message = json.dumps(notification) + "\n"
            await self.write_stream.send(message)
        except Exception:
            # Swallow errors if stream is disconnected
            logger.debug("Failed to send elicitation complete notification", exc_info=True)

    # Context management
    async def create_request_context(self, resource_owner: ResourceOwner | None = None) -> Context:
        """Create a context for the current request.

        Args:
            resource_owner: The authenticated resource owner from front-door auth.
        """
        context = Context(
            server=self.server,
            resource_owner=resource_owner,
        )
        context.set_session(self)
        self._current_context = context
        return context

    async def cleanup_request_context(self, context: Context) -> None:
        """Clean up request context."""
        # Flush any pending notifications
        await context._flush_notifications()
        self._current_context = None
