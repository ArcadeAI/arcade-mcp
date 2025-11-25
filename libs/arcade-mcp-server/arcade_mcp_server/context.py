"""
MCP Context System

Provides the primary Context class for MCP tool development. This module contains
the Context class that tools should use for both runtime capabilities and
tool-specific data access.

The Context class combines:
- Runtime capabilities: logging, resources, prompts, sampling, UI, notifications
- Tool-specific data: secrets, user_id, authorization, metadata
- Session management: request/session IDs and MCP protocol handling

Key responsibilities:
- Manage per-request state and the current model context using a ContextVar
- Expose namespaced runtime capabilities (log, resources, etc.)
- Provide access to tool-specific data (secrets, user_id, etc.)
- Delegate to the underlying MCP session and server managers
- Handle MCP protocol communication and lifecycle management

Note: Context instances are automatically created and managed by the MCP server.
Tools receive a populated context instance as a parameter and should not
create Context instances directly.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import weakref
from builtins import list as builtins_list
from contextvars import ContextVar, Token
from typing import Any, cast

from arcade_core.context import ModelContext as ModelContextProtocol
from arcade_core.schema import (
    ToolContext,
)

from arcade_mcp_server.resource_server.base import ResourceOwner
from arcade_mcp_server.types import (
    AudioContent,
    CallToolParams,
    CallToolRequest,
    CallToolResult,
    ClientCapabilities,
    CreateMessageResult,
    ElicitResult,
    ImageContent,
    JSONRPCError,
    LoggingLevel,
    ModelHint,
    ModelPreferences,
    ResourceContents,
    Root,
    SamplingMessage,
    TextContent,
)

# Context variable for current model context
_current_model_context: ContextVar[Context | None] = ContextVar("model_context", default=None)
_flush_lock = asyncio.Lock()


class _ContextComponent:
    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    @property
    def server(self) -> Any:
        return self._ctx.server

    def _require_session(self) -> Any:
        session = self._ctx._session
        if session is None:
            raise ValueError("Session not available")
        return session


class Context(ToolContext):
    """Primary context interface for MCP tools.

    This class provides both runtime capabilities (logging, resources, prompts, etc.)
    and tool-specific data (secrets, user_id, authorization) in a single interface.
    Tools should annotate their context parameter with this class.

    Runtime Capabilities:
        - log: Logging interface (context.log.info(), context.log.error(), etc.)
        - progress: Progress reporting for long-running operations
        - resources: Access to MCP resources (files, data sources, etc.)
        - tools: Call other tools programmatically
        - prompts: Access to MCP prompts and templates
        - sampling: Create messages using the client's model
        - ui: User interaction (elicit input from user)
        - notifications: Send notifications to the client

    Tool-Specific Data (inherited from ToolContext):
        - user_id: The user ID for this tool execution
        - secrets: List of secrets available to this tool
        - authorization: Authorization context if required
        - metadata: Additional metadata for the tool execution

    Example:
        ```python
        from arcade_mcp_server import Context, tool

        @tool
        async def my_tool(context: Context) -> str:
            '''Example tool'''
            # Runtime capabilities
            await context.log.info("Processing request")

            return "result"
        ```

    Note: Instances are automatically created and managed by the MCP server.
    Tools receive a populated context instance as a parameter.
    """

    # Mark as implementing the protocol
    __protocols__ = (ModelContextProtocol,) if ModelContextProtocol is not object else ()

    def __init__(
        self,
        server: Any,
        session: Any | None = None,
        request_id: str | None = None,
        resource_owner: ResourceOwner | None = None,
    ):
        """Initialize context with server reference."""
        super().__init__()
        self._server: weakref.ref[Any] = weakref.ref(server)
        self._session: Any | None = session
        self._tokens: list[Token] = []
        self._notification_queue: set[str] = set()
        self._request_id: str | None = request_id

        # Resource owner from front-door auth (if the server is protected)
        self._resource_owner: ResourceOwner | None = resource_owner

        # Namespaced adapters
        self._log = Logs(self)
        self._progress = Progress(self)
        self._resources = Resources(self)
        self._tools = Tools(self)
        self._prompts = Prompts(self)
        self._sampling = Sampling(self)
        self._ui = UI(self)
        self._notifications = Notifications(self)

    @property
    def server(self) -> Any:
        """Get the server instance."""
        server = self._server()
        if server is None:
            raise RuntimeError("Server instance is no longer available")
        return server

    def set_session(self, session: Any) -> None:
        """Set the session for this context."""
        self._session = session

    def set_request_id(self, request_id: str) -> None:
        """Set the request ID for this context."""
        self._request_id = request_id

    def set_tool_context(
        self,
        toolContext: ToolContext,
    ) -> None:
        """Populate the tool context fields for this model context."""
        self.authorization = toolContext.authorization
        self.secrets = toolContext.secrets
        self.metadata = toolContext.metadata
        self.user_id = toolContext.user_id

    async def __aenter__(self) -> Context:
        """Enter the context manager and set as current model context."""
        # Set this as current model context
        token = _current_model_context.set(self)
        self._tokens.append(token)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager and clear current model context."""
        # Flush any pending notifications
        await self._flush_notifications()

        # Reset context
        if self._tokens:
            token = self._tokens.pop()
            _current_model_context.reset(token)

    # ============ ModelContext protocol properties ============
    @property
    def log(self) -> Logs:
        """Logging interface for the tool.

        Provides methods for different log levels:
        - log.debug(message): Debug-level logging
        - log.info(message): Info-level logging
        - log.warning(message): Warning-level logging
        - log.error(message): Error-level logging
        - log.log(level, message): Log at a specific level

        Example:
            ```python
            await context.log.info("Processing started")
            await context.log.error("Something went wrong")
            ```
        """
        return self._log

    @property
    def progress(self) -> Progress:
        """Progress reporting for long-running operations.

        Use this to report progress back to the client during lengthy operations.

        Example:
            ```python
            await context.progress.report(0.5, total=1.0, message="Halfway done")
            ```
        """
        return self._progress

    @property
    def resources(self) -> Resources:
        """Interface for accessing MCP resources"""
        return self._resources

    @property
    def tools(self) -> Tools:
        """Interface for calling other tools programmatically.

        Allows tools to call other tools within the same session.

        Example:
            ```python
            result = await context.tools.call_raw("other_tool", {"param": "value"})
            ```
        """
        return self._tools

    @property
    def prompts(self) -> Prompts:
        """Interface for accessing MCP prompts and templates"""
        return self._prompts

    @property
    def sampling(self) -> Sampling:
        """Create messages using the client's model.

        Allows tools to generate text using the connected model.

        Example:
            ```python
            response = await context.sampling.create_message(
                "Summarize this text: " + text,
                temperature=0.7
            )
            ```
        """
        return self._sampling

    @property
    def ui(self) -> UI:
        """User interaction (elicitation) capabilities.

        Provides methods for interacting with the user, such as eliciting input.

        Example:
            ```python
            result = await context.ui.elicit(
                "Please provide your name",
                schema={"type": "object", "properties": {"name": {"type": "string"}}}
            )
            ```
        """
        return self._ui

    @property
    def notifications(self) -> Notifications:
        """
        Interface for sending notifications to the client
        such as tool list changes.

        Example:
            ```python
            await context.notifications.tools.list_changed()
            ```
        """
        return self._notifications

    @property
    def request_id(self) -> str | None:
        """Get the current request ID.

        Returns:
            The unique identifier for this MCP request, or None if not available.
        """
        return self._request_id

    @property
    def session_id(self) -> str | None:
        """Get the current session ID.

        Returns:
            The unique identifier for this MCP session, or None if not available.
        """
        if self._session is None:
            return None
        return getattr(self._session, "session_id", None)

    # Private helpers
    def _check_client_capability(self, capability: ClientCapabilities) -> bool:
        """Check if client has a capability."""
        if self._session is None:
            return False
        return cast(bool, self._session.check_client_capability(capability))

    def _parse_model_preferences(
        self, prefs: ModelPreferences | str | list[str] | None
    ) -> ModelPreferences | None:
        """Parse model preferences into standard format."""
        if prefs is None:
            return None
        elif isinstance(prefs, ModelPreferences):
            return prefs
        elif isinstance(prefs, str):
            return ModelPreferences(hints=[ModelHint(name=prefs)])
        elif isinstance(prefs, list):
            return ModelPreferences(hints=[ModelHint(name=h) for h in prefs])
        else:
            raise ValueError(f"Invalid model preferences type: {type(prefs)}")

    def _try_flush_notifications(self) -> None:
        """Try to flush notifications if in async context."""
        try:
            loop = asyncio.get_running_loop()
            if loop and not loop.is_running():
                return
            flush_task = asyncio.create_task(self._flush_notifications())
            flush_task.add_done_callback(lambda _: self._notification_queue.clear())
        except RuntimeError:
            # No event loop
            pass

    async def _flush_notifications(self) -> None:
        """Send all queued notifications."""
        async with _flush_lock:
            if not self._notification_queue or self._session is None:
                return

            nm = getattr(self.server, "notification_manager", None)
            if nm is None:
                return

            try:
                client_ids = []
                if (
                    self._session
                    and hasattr(self._session, "session_id")
                    and self._session.session_id
                ):
                    client_ids = [self._session.session_id]

                if "notifications/tools/list_changed" in self._notification_queue:
                    await nm.notify_tool_list_changed(client_ids)
                if "notifications/resources/list_changed" in self._notification_queue:
                    await nm.notify_resource_list_changed(client_ids)
                if "notifications/prompts/list_changed" in self._notification_queue:
                    pass

                self._notification_queue.clear()
            except Exception:
                # Don't let notification failures break the request
                logging.debug("Failed to send notifications", exc_info=True)


# =====================
# Namespaced adapters
# =====================
# These thin, per-domain facades (log, progress, resources, tools, prompts,
# sampling, ui, notifications) expose a stable, developer-friendly API on
# Context (e.g., context.log.info(...), context.resources.list()).
#
# They delegate all work to the active MCP session and server managers, keeping
# transport and server-specific details encapsulated in one place.
# This design:
# - avoids leaking MCP internals into the developer surface
# - preserves a cohesive, testable Context API with clear async boundaries
# - allows runtime implementations to evolve without breaking tool code
#
# In short: adapters provide the ergonomics tools rely on, while the underlying
# implementation remains decoupled and replaceable.


class Logs(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def log(
        self,
        level: str,
        message: str,
        logger_name: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        session = self._ctx._session
        if session is None:
            return
        level_typed = cast(LoggingLevel, level)
        data = {"msg": message, "extra": extra}
        await session.send_log_message(
            level=level_typed,
            data=data,
            logger=logger_name,
        )

    async def __call__(
        self,
        level: str,
        message: str,
        logger_name: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:  # compatibility shim
        await self.log(level, message, logger_name=logger_name, extra=extra)

    async def debug(self, message: str, **kwargs: Any) -> None:
        await self.log("debug", message, **kwargs)

    async def info(self, message: str, **kwargs: Any) -> None:
        await self.log("info", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        await self.log("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        await self.log("error", message, **kwargs)


class Progress(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def report(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        session = self._ctx._session
        if session is None:
            return
        progress_token = None
        if hasattr(session, "_request_meta") and session._request_meta is not None:
            progress_token = getattr(session._request_meta, "progressToken", None)
        if progress_token is None:
            return
        await session.send_progress_notification(
            progress_token=progress_token,
            progress=progress,
            total=total,
            message=message,
        )


class Resources(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def read(self, uri: str) -> list[ResourceContents]:
        if self._ctx.server is None:
            raise ValueError("Context is not available outside of a request")
        result = await self._ctx.server._mcp_read_resource(uri)
        return cast(list[ResourceContents], result)

    async def get(self, uri: str) -> ResourceContents:
        contents = await self.read(uri)
        if not contents:
            raise ValueError(f"Resource not found: {uri}")
        return contents[0]

    async def list_roots(self) -> list[Root]:
        if self._ctx._session is None:
            return []
        result = await self._ctx._session.list_roots()
        return result.roots if hasattr(result, "roots") else []

    async def list(self) -> list[Root]:
        # Convert Resource objects to Root objects
        resources = await self._ctx.server._resource_manager.list_resources()
        # Resources have uri and name which map to Root
        return [Root(uri=r.uri, name=r.name) for r in resources]

    async def list_templates(self) -> builtins_list[Any]:
        templates = await self._ctx.server._resource_manager.list_resource_templates()
        return cast(builtins_list[Any], templates)


class Tools(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def list(self) -> list[Any]:
        tools = await self._ctx.server._tool_manager.list_tools()
        return cast(list[Any], tools)

    async def call_raw(self, name: str, params: dict[str, Any]) -> CallToolResult:
        internal_id = f"internal-{uuid.uuid4()}"
        request = CallToolRequest(
            id=internal_id,
            params=CallToolParams(name=name, arguments=params),
        )

        response = await self._ctx.server._handle_call_tool(request, self._ctx._session)

        if isinstance(response, JSONRPCError):
            error_message = response.error.get("message", "Unknown error")
            return CallToolResult(
                content=[TextContent(type="text", text=error_message)],
                structuredContent={"error": error_message},
                isError=True,
            )

        return cast(CallToolResult, response.result)


class Prompts(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def list(self) -> list[Any]:
        prompts = await self._ctx.server._prompt_manager.list_prompts()
        return cast(list[Any], prompts)

    async def get(self, name: str, arguments: dict[str, str] | None = None) -> Any:
        return await self._ctx.server._prompt_manager.get_prompt(name, arguments)


class Sampling(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def create_message(
        self,
        messages: str | list[str | SamplingMessage],
        system_prompt: str | None = None,
        include_context: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model_preferences: ModelPreferences | str | list[str] | None = None,
    ) -> TextContent | ImageContent | AudioContent | CreateMessageResult:
        if self._ctx._session is None:
            raise ValueError("Session not available")

        # Convert messages to proper format
        if isinstance(messages, str):
            sampling_messages = [
                SamplingMessage(content=TextContent(text=messages, type="text"), role="user")
            ]
        elif isinstance(messages, list):
            sampling_messages = []
            for m in messages:
                if isinstance(m, str):
                    sampling_messages.append(
                        SamplingMessage(content=TextContent(text=m, type="text"), role="user")
                    )
                else:
                    sampling_messages.append(m)
        else:
            sampling_messages = messages

        # Parse model preferences
        parsed_prefs = self._ctx._parse_model_preferences(model_preferences)

        # Check client capabilities
        if not self._ctx._check_client_capability(ClientCapabilities(sampling={})):
            raise ValueError("Client does not support sampling")

        result = await self._ctx._session.create_message(
            messages=sampling_messages,
            system_prompt=system_prompt,
            include_context=include_context,
            temperature=temperature,
            max_tokens=max_tokens or 512,
            model_preferences=parsed_prefs,
        )

        return result.content if hasattr(result, "content") else result  # type: ignore[no-any-return]


class UI(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    def _validate_elicitation_schema(self, schema: dict[str, Any]) -> None:
        """Validate that the schema conforms to MCP elicitation restrictions."""
        if not isinstance(schema, dict):
            raise TypeError("Schema must be a dictionary")

        if schema.get("type") != "object":
            raise ValueError("Schema must have type 'object'")

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise TypeError("Schema properties must be a dictionary")

        # Validate each property
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                raise TypeError(f"Property '{prop_name}' schema must be a dictionary")

            prop_type = prop_schema.get("type")
            if prop_type not in ["string", "number", "integer", "boolean"]:
                raise ValueError(
                    f"Property '{prop_name}' has unsupported type '{prop_type}'. Only primitive types are allowed."
                )

            # Validate string formats
            if prop_type == "string" and "format" in prop_schema:
                allowed_formats = ["email", "uri", "date", "date-time"]
                if prop_schema["format"] not in allowed_formats:
                    raise ValueError(
                        f"Property '{prop_name}' has unsupported format '{prop_schema['format']}'. Allowed: {allowed_formats}"
                    )

    async def elicit(
        self, message: str, schema: dict[str, Any] | None = None, timeout: float = 300.0
    ) -> ElicitResult:
        if self._ctx._session is None:
            raise ValueError("Session not available")
        if schema is None:
            schema = {"type": "object", "properties": {}}

        # Validate schema conforms to MCP restrictions
        self._validate_elicitation_schema(schema)

        result = await self._ctx._session.elicit(
            message=message,
            requested_schema=schema,
            timeout=timeout,
        )
        return cast(ElicitResult, result)


class _NotificationsTools(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def list_changed(self) -> None:
        self._ctx._notification_queue.add("notifications/tools/list_changed")
        self._ctx._try_flush_notifications()


class _NotificationsResources(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def list_changed(self) -> None:
        self._ctx._notification_queue.add("notifications/resources/list_changed")
        self._ctx._try_flush_notifications()


class _NotificationsPrompts(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

    async def list_changed(self) -> None:
        self._ctx._notification_queue.add("notifications/prompts/list_changed")
        self._ctx._try_flush_notifications()


class Notifications(_ContextComponent):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self._tools = _NotificationsTools(ctx)
        self._resources = _NotificationsResources(ctx)
        self._prompts = _NotificationsPrompts(ctx)

    @property
    def tools(self) -> _NotificationsTools:
        return self._tools

    @property
    def resources(self) -> _NotificationsResources:
        return self._resources

    @property
    def prompts(self) -> _NotificationsPrompts:
        return self._prompts


def get_current_model_context() -> Context | None:
    """Get the current model context if available."""
    return _current_model_context.get()


def set_current_model_context(context: Context | None, token: Token | None = None) -> Token:
    """Set the current model context and return a token to reset it."""
    if token is not None:
        _current_model_context.reset(token)
        return token
    return _current_model_context.set(context)
