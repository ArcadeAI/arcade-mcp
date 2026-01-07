"""
MCP Server Implementation

Provides request handling, middleware orchestration, and manager-backed
operations for tools, resources, prompts, sampling, logging, and roots.

Key notes:
- For every incoming request, a new MCP ModelContext is created and set as
  current via a ContextVar for the request lifetime
- Tool invocations receive a ToolContext (wrapped by TDK as needed) and are
  executed via ToolExecutor
- Managers (tool, resource, prompt) back the namespaced operations
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, cast

from arcade_core.auth_tokens import get_valid_access_token
from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.executor import ToolExecutor
from arcade_core.network.org_transport import build_org_scoped_async_http_client
from arcade_core.schema import ToolAuthorizationContext, ToolContext
from arcade_core.schema import ToolAuthRequirement as CoreToolAuthRequirement
from arcadepy import ArcadeError, AsyncArcade
from arcadepy.types.auth_authorize_params import AuthRequirement, AuthRequirementOauth2

from arcade_mcp_server.context import Context, get_current_model_context, set_current_model_context
from arcade_mcp_server.convert import convert_content_to_structured_content, convert_to_mcp_content
from arcade_mcp_server.exceptions import NotFoundError, ToolRuntimeError
from arcade_mcp_server.lifespan import LifespanManager
from arcade_mcp_server.managers import PromptManager, ResourceManager, ToolManager
from arcade_mcp_server.middleware import (
    CallNext,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    Middleware,
    MiddlewareContext,
)
from arcade_mcp_server.resource_server.base import ResourceOwner
from arcade_mcp_server.session import InitializationState, NotificationManager, ServerSession
from arcade_mcp_server.settings import MCPSettings, ServerSettings
from arcade_mcp_server.types import (
    LATEST_PROTOCOL_VERSION,
    BlobResourceContents,
    CallToolRequest,
    CallToolResult,
    CompleteRequest,
    CreateMessageRequest,
    ElicitRequest,
    GetPromptRequest,
    GetPromptResult,
    Implementation,
    InitializeRequest,
    InitializeResult,
    JSONRPCError,
    JSONRPCResponse,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListResourceTemplatesRequest,
    ListResourceTemplatesResult,
    ListRootsRequest,
    ListToolsRequest,
    ListToolsResult,
    MCPMessage,
    PingRequest,
    ReadResourceRequest,
    ReadResourceResult,
    ServerCapabilities,
    SetLevelRequest,
    SubscribeRequest,
    TextResourceContents,
    UnsubscribeRequest,
)
from arcade_mcp_server.usage import ServerTracker

logger = logging.getLogger("arcade.mcp")


class MCPServer:
    """
    MCP Server with middleware and context support.

    This server provides:
    - Middleware chain for extensible request processing
    - Context injection for tools
    - Component managers for tools, resources, and prompts
    - Bidirectional communication support to MCP clients
    """

    # Public manager properties near top
    @property
    def tools(self) -> ToolManager:
        """Access the ToolManager for runtime tool operations."""
        return self._tool_manager

    @property
    def resources(self) -> ResourceManager:
        """Access the ResourceManager for runtime resource operations."""
        return self._resource_manager

    @property
    def prompts(self) -> PromptManager:
        """Access the PromptManager for runtime prompt operations."""
        return self._prompt_manager

    def __init__(
        self,
        catalog: ToolCatalog,
        *,
        name: str | None = None,
        version: str | None = None,
        title: str | None = None,
        instructions: str | None = None,
        settings: MCPSettings | None = None,
        middleware: list[Middleware] | None = None,
        lifespan: Callable[[Any], Any] | None = None,
        auth_disabled: bool = False,
        arcade_api_key: str | None = None,
        arcade_api_url: str | None = None,
    ):
        """
        Initialize MCP server.

        Args:
            catalog: Tool catalog
            name: Server name
            version: Server version
            title: Server title for display
            instructions: Server instructions
            settings: MCP settings (uses env if not provided)
            middleware: List of middleware to apply
            lifespan: Lifespan manager function
            auth_disabled: Disable authentication
            arcade_api_key: Arcade API key (overrides settings)
            arcade_api_url: Arcade API URL (overrides settings)
        """
        self._started = False
        self._lock = asyncio.Lock()

        # Settings (load first so we can use values from it)
        self.settings = settings or MCPSettings.from_env()

        # Server info
        self.name = name if name else self.settings.server.name
        self.version = version if version else self.settings.server.version
        if title:
            self.title = title
        elif (
            self.settings.server.title
            and self.settings.server.title != ServerSettings.model_fields["title"].default
        ):
            self.title = self.settings.server.title
        else:
            self.title = self.name

        self.instructions = (
            instructions or self.settings.server.instructions or self._default_instructions()
        )

        self.auth_disabled = auth_disabled or self.settings.arcade.auth_disabled

        # Initialize Arcade client
        # Fallback to API key in ~/.arcade/credentials.yaml if not provided
        self._init_arcade_client(
            arcade_api_key or self.settings.arcade.api_key,
            arcade_api_url or self.settings.arcade.api_url,
        )

        # Component managers (passive)
        self._tool_manager = ToolManager()
        self._resource_manager = ResourceManager()
        self._prompt_manager = PromptManager()

        # Centralized notifications
        self.notification_manager = NotificationManager(self)

        # Subscribe to changes -> broadcast
        self._tool_manager.subscribe(
            lambda *_: asyncio.get_event_loop().create_task(  # type: ignore[arg-type]
                self.notification_manager.notify_tool_list_changed()
            )
        )
        self._resource_manager.subscribe(
            lambda *_: asyncio.get_event_loop().create_task(  # type: ignore[arg-type]
                self.notification_manager.notify_resource_list_changed()
            )
        )
        self._prompt_manager.subscribe(
            lambda *_: asyncio.get_event_loop().create_task(  # type: ignore[arg-type]
                self.notification_manager.notify_prompt_list_changed()
            )
        )

        # Defer loading tools from catalog to server start to ensure readiness
        self._initial_catalog = catalog

        # Middleware chain
        self.middleware: list[Middleware] = []
        self._init_middleware(middleware)

        # Lifespan management
        self.lifespan_manager = LifespanManager(self, lifespan)

        # Session management
        self._sessions: dict[str, ServerSession] = {}
        self._sessions_lock = asyncio.Lock()

        # Usage tracking
        self._tracker = ServerTracker()

        # Handler registration
        self._handlers = self._register_handlers()

    def _load_config_values(self) -> tuple[str | None, str | None]:
        """Load access token and user_id from credentials file.

        Returns:
            Tuple of (access_token, user_id) from credentials file, or (None, None) if not available
        """
        try:
            from arcade_core.config import config

            access_token = get_valid_access_token()
            user_id = config.user.email if config.user else None

            if access_token or user_id:
                config_path = config.get_config_file_path()
                if access_token:
                    logger.info(f"Loaded Arcade access token from {config_path}")
                if user_id:
                    logger.debug(f"Loaded user_id '{user_id}' from {config_path}")
                return access_token, user_id
            else:
                logger.debug(
                    "No access token or user_id found in credentials file. If this is unexpected, run 'arcade login' to authenticate."
                )
                return None, None
        except Exception as e:
            logger.debug(f"Could not load values from credentials file: {e}")
            return None, None

    def _load_org_project_context(self) -> tuple[str, str] | None:
        """
        Load org/project context from the shared Arcade config (same source as the CLI).
        Returns (org_id, project_id) when both are available; otherwise None.
        """
        try:
            from arcade_core.config import config

            context = getattr(config, "context", None)
            if context and context.org_id and context.project_id:
                return context.org_id, context.project_id
            logger.debug("Org/project context not found in arcade_core.config")
        except Exception as e:
            logger.debug(f"Could not load org/project context from config: {e}")
        return None

    def _init_arcade_client(self, api_key: str | None, api_url: str | None) -> None:
        """Initialize Arcade client for runtime authorization."""
        self.arcade: AsyncArcade | None = None

        if not api_url:
            api_url = os.environ.get("ARCADE_API_URL", "https://api.arcade.dev")

        final_api_key = api_key

        # If no API key provided, try to load from credentials file
        if not final_api_key:
            config_api_key, _ = self._load_config_values()
            final_api_key = config_api_key

        if final_api_key:
            logger.info(f"Using Arcade client with API URL: {api_url}")
            client_kwargs: dict[str, Any] = {"api_key": final_api_key, "base_url": api_url}

            # Non-service keys need org/project URL rewriting
            if not final_api_key.startswith("arc_"):
                context = self._load_org_project_context()
                if context:
                    org_id, project_id = context
                    client_kwargs["http_client"] = build_org_scoped_async_http_client(
                        org_id, project_id
                    )
                    logger.info(
                        "Configured org-scoped Arcade client for org '%s' project '%s'",
                        org_id,
                        project_id,
                    )
                else:
                    logger.warning(
                        "Expected to find org/project context in arcade_core.config but no org/project context "
                        "was found; using non-scoped Arcade client."
                    )

            self.arcade = AsyncArcade(**client_kwargs)
        else:
            logger.warning(
                "Arcade access token not configured. Tools requiring auth will return a login instruction."
            )

    def _init_middleware(self, custom_middleware: list[Middleware] | None) -> None:
        """Initialize middleware chain."""
        # Always add error handling first (innermost)
        self.middleware.append(
            ErrorHandlingMiddleware(mask_error_details=self.settings.middleware.mask_error_details)
        )

        # Add logging if enabled
        if self.settings.middleware.enable_logging:
            self.middleware.append(LoggingMiddleware(log_level=self.settings.middleware.log_level))

        # Add custom middleware
        if custom_middleware:
            self.middleware.extend(custom_middleware)

    def _register_handlers(self) -> dict[str, Callable]:
        """Register method handlers."""
        return {
            "ping": self._handle_ping,
            "initialize": self._handle_initialize,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "resources/list": self._handle_list_resources,
            "resources/templates/list": self._handle_list_resource_templates,
            "resources/read": self._handle_read_resource,
            "prompts/list": self._handle_list_prompts,
            "prompts/get": self._handle_get_prompt,
            "logging/setLevel": self._handle_set_log_level,
        }

    def _default_instructions(self) -> str:
        """Get default server instructions."""
        return (
            "The Arcade MCP Server provides access to tools defined in Arcade toolkits. "
            "Use 'tools/list' to see available tools and 'tools/call' to execute them."
        )

    async def _start(self) -> None:
        """Start server components (called by MCPComponent.start)."""
        await self._tool_manager.start()
        # Load initial catalog now that manager is started
        try:
            await self._tool_manager.load_from_catalog(self._initial_catalog)
        except Exception:
            logger.exception("Failed to load tools from initial catalog")

        # Check for missing secrets and log warnings (only when worker routes are disabled)
        await self._check_and_warn_missing_secrets()

        await self._resource_manager.start()
        await self._prompt_manager.start()
        await self.lifespan_manager.startup()

    async def _stop(self) -> None:
        """Stop server components (called by MCPComponent.stop)."""
        # Stop all sessions
        async with self._sessions_lock:
            sessions = list(self._sessions.values())
        for _session in sessions:
            # Sessions should handle their own cleanup
            pass

        await self._prompt_manager.stop()
        await self._resource_manager.stop()
        await self._tool_manager.stop()

        # Stop lifespan
        await self.lifespan_manager.shutdown()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                logger.debug(f"{self.name} already started")
                return
            logger.info(f"Starting {self.name}")
            try:
                await self._start()
                self._started = True
                logger.info(f"{self.name} started successfully")
            except Exception:
                logger.exception(f"Failed to start {self.name}")
                raise

    async def stop(self) -> None:
        async with self._lock:
            if not self._started:
                logger.debug(f"{self.name} not started")
                return
            logger.info(f"Stopping {self.name}")
            try:
                await self._stop()
                self._started = False
                logger.info(f"{self.name} stopped successfully")
            except Exception:
                logger.exception(f"Failed to stop {self.name}")
                # best-effort on stop

    async def run_connection(
        self,
        read_stream: Any,
        write_stream: Any,
        init_options: Any = None,
    ) -> None:
        """
        Run a single MCP connection.

        Args:
            read_stream: Stream for reading messages
            write_stream: Stream for writing messages
            init_options: Connection initialization options
        """

        # Create session
        session = ServerSession(
            server=self,
            read_stream=read_stream,
            write_stream=write_stream,
            init_options=init_options,
        )

        # Register session
        async with self._sessions_lock:
            self._sessions[session.session_id] = session

        try:
            logger.info(f"Starting session {session.session_id}")
            await session.run()
        except Exception:
            logger.exception("Session error")
            raise
        finally:
            # Unregister session
            async with self._sessions_lock:
                self._sessions.pop(session.session_id, None)
            logger.info(f"Session {session.session_id} ended")

    async def handle_message(
        self,
        message: Any,
        session: ServerSession | None = None,
        resource_owner: ResourceOwner | None = None,
    ) -> MCPMessage | None:
        """
        Handle an incoming message.

        Args:
            message: Message to handle
            session: Server session
            resource_owner: Authenticated resource owner from front-door auth

        Returns:
            Response message or None
        """
        # Validate message
        if (
            not isinstance(message, dict)
            or not message.get("method")
            or not isinstance(message["method"], str)
        ):
            return JSONRPCError(
                id="null",
                error={
                    "code": -32600,
                    "message": (
                        "✗ Invalid request\n\n"
                        "  The request is not a valid JSON-RPC message.\n\n"
                        "  To fix:\n"
                        "  1. Ensure request has 'method' field\n"
                        "  2. Verify JSON structure is correct\n"
                        "  3. Check JSON-RPC 2.0 specification\n\n"
                        '  Expected format: {"jsonrpc": "2.0", "method": "...", "params": {...}, "id": ...}'
                    ),
                },
            )

        method = message["method"]
        msg_id = message.get("id")

        # Handle notifications (no response needed)
        if method and method.startswith("notifications/"):
            if method == "notifications/initialized" and session:
                session.mark_initialized()
            return None

        # Check if this is a response to a server-initiated request
        if "id" in message and "method" not in message:
            # This is handled in the session's message processing
            return None

        # Check initialization state
        if (
            session
            and session.initialization_state != InitializationState.INITIALIZED
            and method not in ["initialize", "ping"]
        ):
            return JSONRPCError(
                id=str(msg_id or "null"),
                error={
                    "code": -32600,
                    "message": (
                        "✗ Not initialized\n\n"
                        "  This request cannot be processed before the session is initialized.\n\n"
                        "  To fix:\n"
                        "  1. Send an 'initialize' request first\n"
                        "  2. Wait for initialization to complete\n"
                        "  3. Send 'notifications/initialized' notification\n\n"
                        "  Only 'initialize' and 'ping' methods are allowed before initialization."
                    ),
                },
            )

        # Find handler
        handler = self._handlers.get(method)
        if not handler:
            return JSONRPCError(
                id=str(msg_id or "null"),
                error={
                    "code": -32601,
                    "message": (
                        f"✗ Method not found: {method}\n\n"
                        f"  The requested method is not supported by this server.\n\n"
                        f"  Supported methods:\n"
                        f"    - initialize, ping\n"
                        f"    - tools/list, tools/call\n"
                        f"    - resources/list, resources/read, resources/templates/list\n"
                        f"    - prompts/list, prompts/get\n"
                        f"    - logging/setLevel\n\n"
                        f"  Check the MCP specification for valid method names."
                    ),
                },
            )

        # Create context and apply middleware
        try:
            # Store the request's meta in the session
            if session:
                params = message.get("params", {})
                meta = params.get("_meta")
                session.set_request_meta(meta)

            # Create request context
            context = (
                await session.create_request_context(resource_owner=resource_owner)
                if session
                else Context(
                    self,
                    request_id=str(msg_id) if msg_id else None,
                    resource_owner=resource_owner,
                )
            )

            # Set as current model context
            token = set_current_model_context(context)

            try:
                # Create middleware context
                middleware_context = MiddlewareContext(
                    message=message,
                    mcp_context=context,
                    source="client",
                    type="request",
                    method=method,
                    request_id=str(msg_id) if msg_id else None,
                    session_id=session.session_id if session else None,
                )

                # Parse message based on method
                parsed_message = self._parse_message(message, method or "")

                # Apply middleware chain
                async def final_handler(_: MiddlewareContext[Any]) -> Any:
                    return await handler(parsed_message, session=session)

                result = await self._apply_middleware(middleware_context, final_handler)

                from typing import cast

                return cast(MCPMessage | None, result)

            finally:
                # Clean up context
                set_current_model_context(None, token)
                if session:
                    await session.cleanup_request_context(context)
                    session.clear_request_meta()

        except Exception:
            logger.exception("Error handling message")
            return JSONRPCError(
                id=str(msg_id or "null"),
                error={
                    "code": -32603,
                    "message": (
                        "✗ Internal server error\n\n"
                        "  An unexpected error occurred while processing the request.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for detailed error information\n"
                        "  2. Verify the request parameters are valid\n"
                        "  3. Try the request again\n"
                        "  4. Contact support if the issue persists\n\n"
                        "  The error has been logged for investigation."
                    ),
                },
            )

    def _parse_message(self, message: dict[str, Any], method: str) -> Any:
        """Parse raw message dict into typed message based on method."""
        message_types = {
            "ping": PingRequest,
            "initialize": InitializeRequest,
            "tools/list": ListToolsRequest,
            "tools/call": CallToolRequest,
            "resources/list": ListResourcesRequest,
            "resources/read": ReadResourceRequest,
            "resources/subscribe": SubscribeRequest,
            "resources/unsubscribe": UnsubscribeRequest,
            "resources/templates/list": ListResourceTemplatesRequest,
            "prompts/list": ListPromptsRequest,
            "prompts/get": GetPromptRequest,
            "logging/setLevel": SetLevelRequest,
            "sampling/createMessage": CreateMessageRequest,
            "completion/complete": CompleteRequest,
            "roots/list": ListRootsRequest,
            "elicitation/create": ElicitRequest,
        }

        message_type = message_types.get(method)
        if message_type is not None:
            # Use constructor for compatibility across Pydantic versions
            return message_type(**message)
        return message

    async def _apply_middleware(
        self,
        context: MiddlewareContext[Any],
        final_handler: Callable[[MiddlewareContext[Any]], Any] | CallNext[Any, Any],
    ) -> Any:
        """Apply middleware chain to a request."""

        # Build chain from outside in
        async def chain_fn(ctx: MiddlewareContext[Any]) -> Any:
            return await final_handler(ctx)

        chain: CallNext[Any, Any] = cast(CallNext[Any, Any], chain_fn)

        for middleware in reversed(self.middleware):

            async def make_handler(
                ctx: MiddlewareContext[Any],
                next_handler: CallNext[Any, Any] = chain,
                mw: Middleware = middleware,
            ) -> Any:
                return await mw(ctx, next_handler)

            chain = make_handler  # type: ignore[assignment]

        # Execute chain
        return await chain(context)

    # Handler methods
    async def _handle_ping(
        self,
        message: PingRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[Any]:
        """Handle ping request."""
        return JSONRPCResponse(id=message.id, result={})

    async def _handle_initialize(
        self,
        message: InitializeRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[InitializeResult]:
        """Handle initialize request."""
        if session:
            session.set_client_params(message.params)

        result = InitializeResult(
            protocolVersion=LATEST_PROTOCOL_VERSION,
            capabilities=ServerCapabilities(
                tools={"listChanged": True},
                logging={},
                prompts={"listChanged": True},
                resources={"subscribe": True, "listChanged": True},
            ),
            serverInfo=Implementation(
                name=self.name,
                version=self.version,
                title=self.title,
            ),
            instructions=self.instructions,
        )

        return JSONRPCResponse(id=message.id, result=result)

    async def _handle_list_tools(
        self,
        message: ListToolsRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListToolsResult] | JSONRPCError:
        """Handle list tools request."""
        try:
            tools = await self._tool_manager.list_tools()
            return JSONRPCResponse(id=message.id, result=ListToolsResult(tools=tools))
        except Exception:
            logger.exception("Error listing tools")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        "✗ Failed to list tools\n\n"
                        "  An error occurred while retrieving the tool list.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for details\n"
                        "  2. Verify toolkits are properly loaded\n"
                        "  3. Restart the server if needed\n\n"
                        "  The error has been logged."
                    ),
                },
            )

    def _create_tool_context(
        self, tool: MaterializedTool, session: ServerSession | None = None
    ) -> ToolContext:
        """Create a tool context from a tool definition and session"""
        tool_context = ToolContext()

        # secrets
        if tool.definition.requirements and tool.definition.requirements.secrets:
            for secret in tool.definition.requirements.secrets:
                if secret.key in self.settings.tool_secrets():
                    tool_context.set_secret(secret.key, self.settings.tool_secrets()[secret.key])
                elif secret.key in os.environ:
                    tool_context.set_secret(secret.key, os.environ[secret.key])

        tool_context.user_id = self._select_user_id(session)

        return tool_context

    def _select_user_id(self, session: ServerSession | None = None) -> str | None:
        """Select the user_id for the tool's context.

        User ID selection priority:
        - Authenticated user from front-door auth
        - Configured user_id from settings
        - Configured user_id from credentials file
        - Use session ID if no other user_id is available

        Args:
            session: Server session

        Returns:
            User ID for the context
        """
        env = (self.settings.arcade.environment or "").lower()

        # First priority: resource owner from front-door auth (from current model context)
        mctx = get_current_model_context()
        if mctx is not None and hasattr(mctx, "_resource_owner") and mctx._resource_owner:
            user_id = mctx._resource_owner.user_id
            logger.debug(f"Context user_id set from Authorization Server 'sub' claim: {user_id}")
            return cast(str, user_id)

        # Second priority: configured user_id from settings
        if (settings_user_id := self.settings.arcade.user_id) is not None:
            logger.debug(f"Context user_id set from settings: {settings_user_id}")
            return settings_user_id

        # Third priority: configured user_id from credentials file
        _, config_user_id = self._load_config_values()
        if config_user_id:
            logger.debug(f"Context user_id set from credentials file: {config_user_id}")
            return config_user_id

        # Fourth priority: use session ID if no other user_id is available
        if env in ("development", "dev", "local"):
            logger.debug(f"Context user_id set from session (dev env={env})")
        else:
            logger.debug("Context user_id set from session (non-dev env)")

        return session.session_id if session else None

    async def _check_and_warn_missing_secrets(self) -> None:
        """
        Check for missing tool secrets and log warnings.

        This method is called during server startup to provide early feedback
        about missing configuration. It only runs when worker routes are disabled
        (when ARCADE_WORKER_SECRET is not set), as worker routes receive secrets
        with tool execution information.
        """
        # Skip validation if worker routes are enabled
        if self.settings.arcade.server_secret:
            logger.debug("Skipping secret validation check - worker routes are enabled")
            return

        # Get all available secrets from settings and environment
        available_secrets = set(self.settings.tool_secrets().keys()) | set(os.environ.keys())

        # Check each tool for missing secrets
        managed_tools = await self._tool_manager.registry.list()
        for managed_tool in managed_tools:
            tool = managed_tool["materialized"]
            if tool.definition.requirements and tool.definition.requirements.secrets:
                missing_secrets = []
                for secret_requirement in tool.definition.requirements.secrets:
                    if secret_requirement.key not in available_secrets:
                        missing_secrets.append(secret_requirement.key)

                if missing_secrets:
                    secret_list = "', '".join(missing_secrets)
                    tool_name = tool.definition.name
                    logger.warning(
                        f"Tool '{tool_name}' declares secret(s) '{secret_list}' which is/are not set. It will return an error if called."
                    )

    async def _handle_call_tool(
        self,
        message: CallToolRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[CallToolResult] | JSONRPCError:
        """Handle tool call request."""
        tool_name = message.params.name
        input_params = message.params.arguments or {}

        try:
            # Get tool
            tool = await self._tool_manager.get_tool(tool_name)

            # Create tool context
            tool_context = self._create_tool_context(tool, session)

            # Check restrictions for unauthenticated HTTP transport
            if transport_restriction_response := self._check_transport_restrictions(
                tool, tool_context, message, tool_name, session
            ):
                self._tracker.track_tool_call(False, "transport restriction")
                return transport_restriction_response

            # Handle authorization and secrets requirements if required
            if missing_requirements_response := await self._check_tool_requirements(
                tool, tool_context, message, tool_name, session
            ):
                self._tracker.track_tool_call(False, "missing requirements")
                return missing_requirements_response

            # Attach tool_context to current model context for this request
            mctx = get_current_model_context()
            saved_tool_context: ToolContext | None = None

            if mctx is not None:
                # Save the current tool context so we can restore it after the call
                # This prevents context leakage from callee back to caller in the case of tool chaining.
                saved_tool_context = ToolContext(
                    authorization=mctx.authorization,
                    secrets=mctx.secrets,
                    metadata=mctx.metadata,
                    user_id=mctx.user_id,
                )
                mctx.set_tool_context(tool_context)

            try:
                # Execute tool
                result = await ToolExecutor.run(
                    func=tool.tool,
                    definition=tool.definition,
                    input_model=tool.input_model,
                    output_model=tool.output_model,
                    context=mctx if mctx is not None else tool_context,
                    **input_params,
                )
            finally:
                # Restore the original tool context to prevent context leakage to parent tools in the case of tool chaining.
                if mctx is not None and saved_tool_context is not None:
                    mctx.set_tool_context(saved_tool_context)

            # Convert result
            if result.value is not None:
                content = convert_to_mcp_content(result.value)

                # structuredContent should be the raw result value as a JSON object
                structured_content = convert_content_to_structured_content(result.value)

                self._tracker.track_tool_call(True)
                return JSONRPCResponse(
                    id=message.id,
                    result=CallToolResult(
                        content=content,
                        structuredContent=structured_content,
                        isError=False,
                    ),
                )
            else:
                error = result.error or "Error calling tool"
                content = convert_to_mcp_content(str(error))

                # structuredContent should be the error as a JSON object
                structured_content = convert_content_to_structured_content({"error": str(error)})

                self._tracker.track_tool_call(False, "error during tool execution")
                return JSONRPCResponse(
                    id=message.id,
                    result=CallToolResult(
                        content=content,
                        structuredContent=structured_content,
                        isError=True,
                    ),
                )
        except NotFoundError:
            # Match test expectation: return a normal response with isError=True
            error_message = f"✗ Unknown tool: {tool_name}\n\n"
            error_message += "  The requested tool does not exist or is not loaded.\n\n"
            error_message += "  To fix:\n"
            error_message += "  1. Check the tool name is correct\n"
            error_message += "  2. List available tools with tools/list\n"
            error_message += "  3. Ensure the server is properly installed\n\n"
            error_message += "  Available tools can be found by calling the tools/list method."

            content = convert_to_mcp_content(error_message)

            # structuredContent should be the error as a JSON object
            structured_content = convert_content_to_structured_content({"error": error_message})

            self._tracker.track_tool_call(False, "unknown tool")
            return JSONRPCResponse(
                id=message.id,
                result=CallToolResult(
                    content=content,
                    structuredContent=structured_content,
                    isError=True,
                ),
            )
        except Exception:
            logger.exception("Error calling tool")
            self._tracker.track_tool_call(False, "internal error calling tool")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        "✗ Tool execution failed\n\n"
                        "  An unexpected error occurred while executing the tool.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for detailed error information\n"
                        "  2. Verify all required parameters are provided\n"
                        "  3. Ensure required secrets/authorization are configured\n"
                        "  4. Try the tool again\n\n"
                        "  The error has been logged."
                    ),
                },
            )

    def _create_error_response(
        self, message: CallToolRequest, tool_response: dict[str, Any]
    ) -> JSONRPCResponse[CallToolResult]:
        """Create a consistent error response for tool requirement failures"""
        content = convert_to_mcp_content(tool_response)
        structured_content = convert_content_to_structured_content(tool_response)
        return JSONRPCResponse(
            id=message.id,
            result=CallToolResult(
                content=content,
                structuredContent=structured_content,
                isError=True,
            ),
        )

    def _check_transport_restrictions(
        self,
        tool: MaterializedTool,
        tool_context: ToolContext,
        message: CallToolRequest,
        tool_name: str,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[CallToolResult] | None:
        """Check transport restrictions for tools requiring auth or secrets.

        Tools requiring authorization or secrets are blocked on unauthenticated HTTP
        transport for security reasons. However, if the HTTP transport has front-door
        authentication enabled (resource_owner is present), these tools are allowed
        since we can safely identify the end-user and handle their authorization.
        """
        # Check transport restrictions for tools requiring auth or secrets
        if session and session.init_options:
            transport_type = session.init_options.get("transport_type")
            if transport_type != "stdio":
                # Get resource_owner from current model context (set during handle_message)
                mctx = get_current_model_context()
                is_authenticated = (
                    mctx is not None
                    and hasattr(mctx, "_resource_owner")
                    and mctx._resource_owner is not None
                )

                requirements = tool.definition.requirements
                if (
                    requirements
                    and (requirements.authorization or requirements.secrets)
                    and not is_authenticated
                ):
                    documentation_url = "https://docs.arcade.dev/en/guides/create-tools/tool-basics/compare-server-types"
                    user_message = "✗ Unsupported transport\n\n"
                    user_message += f"  Tool '{tool_name}' cannot run over HTTP transport for security reasons.\n"
                    user_message += f"  This tool requires {'authorization' if requirements.authorization else 'secrets'}.\n\n"
                    user_message += "  To fix:\n"
                    user_message += "  1. Use STDIO transport instead of HTTP\n"
                    user_message += f"  2. See documentation: {documentation_url}\n\n"
                    user_message += "  HTTP transport doesn't support tools needing user authorization or secrets."

                    tool_response = {
                        "message": user_message,
                        "llm_instructions": (
                            f"Please show the following link to the end user formatted as markdown: [Compare Server Types]({documentation_url})\n"
                            "Inform the end user that the provided link contains documentation on how to configure the server to use the correct transport."
                        ),
                    }
                    return self._create_error_response(message, tool_response)
        return None

    async def _check_tool_requirements(
        self,
        tool: MaterializedTool,
        tool_context: ToolContext,
        message: CallToolRequest,
        tool_name: str,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[CallToolResult] | None:
        """Check tool requirements before executing the tool"""
        # Check authorization
        if tool.definition.requirements and tool.definition.requirements.authorization:
            # First check if Arcade API key is configured
            if not self.arcade:
                user_message = "✗ Missing Arcade API key\n\n"
                user_message += (
                    f"  Tool '{tool_name}' requires authorization but no API key is configured.\n\n"
                )
                user_message += "  To fix, either:\n"
                user_message += "  1. Run arcade login:     arcade login\n"
                user_message += "  2. Set environment var:  export ARCADE_API_KEY=your_key_here\n"
                user_message += "  3. Add to .env file:     ARCADE_API_KEY=your_key_here\n\n"
                user_message += "  Then restart the server."

                tool_response = {
                    "message": user_message,
                    "llm_instructions": (
                        f"The MCP server cannot execute the '{tool_name}' tool because it requires authorization "
                        "but the Arcade API key is not configured. The developer needs to: "
                        "1) Run 'arcade login' to authenticate, or "
                        "2) Set the ARCADE_API_KEY environment variable with a valid API key, or "
                        "3) Add ARCADE_API_KEY to the .env file. "
                        "Once the API key is configured, restart the MCP server for the changes to take effect."
                    ),
                }
                return self._create_error_response(message, tool_response)

            # Check authorization status
            try:
                auth_result = await self._check_authorization(tool, tool_context.user_id)
                if auth_result.status != "completed":
                    user_message = "⚠ Authorization required\n\n"
                    user_message += (
                        f"  Tool '{tool_name}' needs your permission to access your account.\n\n"
                    )
                    user_message += "  To authorize:\n"
                    user_message += f"  1. Click this link: {auth_result.url}\n"
                    user_message += "  2. Grant the requested permissions\n"
                    user_message += "  3. Return here and try again\n\n"
                    user_message += "  This is a one-time setup for this tool."

                    tool_response = {
                        "message": user_message,
                        "llm_instructions": f"Please show the following link to the end user formatted as markdown: {auth_result.url} \nInform the end user that the tool requires their authorization to be completed before the tool can be executed.",
                        "authorization_url": auth_result.url,
                    }
                    return self._create_error_response(message, tool_response)
                # Inject the authorization token into the tool context
                tool_context.authorization = ToolAuthorizationContext(
                    token=auth_result.context.token,
                    user_info=auth_result.context.user_info
                    if auth_result.context.user_info
                    else {},
                )
            except ToolRuntimeError as e:
                # Handle any other authorization errors
                user_message = "✗ Authorization error\n\n"
                user_message += f"  Tool '{tool_name}' failed to authorize.\n\n"
                user_message += f"  Error: {e}\n\n"
                user_message += "  To fix:\n"
                user_message += "  1. Check your API key is valid\n"
                user_message += "  2. Verify you have necessary permissions\n"
                user_message += "  3. Try running: arcade login\n\n"
                user_message += "  Then restart the server."

                tool_response = {
                    "message": user_message,
                    "llm_instructions": f"The '{tool_name}' tool failed authorization. Error: {e}. The developer should check their API key and permissions.",
                }
                return self._create_error_response(message, tool_response)

        # Check secrets
        if tool.definition.requirements and tool.definition.requirements.secrets:
            missing_secrets = []
            for secret_requirement in tool.definition.requirements.secrets:
                try:
                    tool_context.get_secret(secret_requirement.key)
                except ValueError:
                    missing_secrets.append(secret_requirement.key)
            if missing_secrets:
                missing_secrets_str = ", ".join(missing_secrets)

                # Create actionable error message
                fix_instructions = "\n\n  To fix, either:\n"
                fix_instructions += "  1. Add to .env file:\n"
                for secret in missing_secrets:
                    fix_instructions += f"       {secret}=your_value_here\n"
                fix_instructions += "  2. Set environment variable:\n"
                for secret in missing_secrets:
                    fix_instructions += f"       export {secret}=your_value_here\n"
                fix_instructions += "\n  Then restart the server."

                user_message = f"✗ Missing {'secret' if len(missing_secrets) == 1 else 'secrets'}: {missing_secrets_str}\n\n"
                user_message += f"  Tool '{tool_name}' requires {'this secret' if len(missing_secrets) == 1 else 'these secrets'} but {'it is' if len(missing_secrets) == 1 else 'they are'} not configured."
                user_message += fix_instructions

                tool_response = {
                    "message": user_message,
                    "llm_instructions": (
                        f"The MCP server is missing required secrets for the '{tool_name}' tool. "
                        f"The developer needs to provide {'this secret' if len(missing_secrets) == 1 else 'these secrets'} by either: "
                        f"1) Adding {'it' if len(missing_secrets) == 1 else 'them'} to a .env file in the server's working directory (e.g., {missing_secrets[0]}=your_secret_value), or "
                        f"2) Setting {'it' if len(missing_secrets) == 1 else 'them'} as environment variable{'s' if len(missing_secrets) > 1 else ''} before starting the server (e.g., export {missing_secrets[0]}=your_secret_value). "
                        "Once the secrets are configured, restart the MCP server for the changes to take effect."
                    ),
                }
                return self._create_error_response(message, tool_response)

        return None

    async def _check_authorization(
        self,
        tool: MaterializedTool,
        user_id: str | None = None,
    ) -> Any:
        """Check tool authorization.

        Note: This method assumes self.arcade is not None. The caller should
        check for the presence of the Arcade API key before calling this method.
        """
        if not self.arcade:
            raise ToolRuntimeError(
                "Authorization check called without Arcade API key configured. "
                "This should be checked by the caller."
            )

        req = tool.definition.requirements.authorization
        provider_id = str(getattr(req, "provider_id", ""))
        provider_type = str(getattr(req, "provider_type", ""))
        # TypedDict requires concrete type; supply empty scopes if absent when oauth2 provider
        oauth2_req = (
            AuthRequirementOauth2(
                scopes=(req.oauth2.scopes or []) if req.oauth2 is not None else []
            )
            if isinstance(req, CoreToolAuthRequirement) and provider_type.lower() == "oauth2"
            else AuthRequirementOauth2()
        )
        auth_req = AuthRequirement(
            provider_id=provider_id,
            provider_type=provider_type,
            oauth2=oauth2_req,
        )

        # Log a warning if user_id is not set
        final_user_id = user_id or "anonymous"
        if final_user_id == "anonymous":
            logger.warning(
                "No user_id available for authorization, defaulting to 'anonymous'. "
                "Set ARCADE_USER_ID as environment variable or run 'arcade login'."
            )

        try:
            response = await self.arcade.auth.authorize(
                auth_requirement=auth_req,
                user_id=final_user_id,
            )
        except ArcadeError as e:
            logger.exception("Error authorizing tool")
            raise ToolRuntimeError(f"Authorization failed: {e}") from e
        else:
            return response

    async def _handle_list_resources(
        self,
        message: ListResourcesRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListResourcesResult] | JSONRPCError:
        """Handle list resources request."""
        try:
            resources = await self._resource_manager.list_resources()
            return JSONRPCResponse(id=message.id, result=ListResourcesResult(resources=resources))
        except Exception:
            logger.exception("Error listing resources")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        "✗ Failed to list resources\n\n"
                        "  An error occurred while retrieving the resource list.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for details\n"
                        "  2. Verify resource providers are properly configured\n"
                        "  3. Restart the server if needed\n\n"
                        "  The error has been logged."
                    ),
                },
            )

    async def _handle_list_resource_templates(
        self,
        message: ListResourceTemplatesRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListResourceTemplatesResult] | JSONRPCError:
        """Handle list resource templates request."""
        try:
            templates = await self._resource_manager.list_resource_templates()
            return JSONRPCResponse(
                id=message.id,
                result=ListResourceTemplatesResult(resourceTemplates=templates),
            )
        except Exception:
            logger.exception("Error listing resource templates")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        "✗ Failed to list resource templates\n\n"
                        "  An error occurred while retrieving resource templates.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for details\n"
                        "  2. Verify resource templates are properly configured\n"
                        "  3. Restart the server if needed\n\n"
                        "  The error has been logged."
                    ),
                },
            )

    async def _handle_read_resource(
        self,
        message: ReadResourceRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ReadResourceResult] | JSONRPCError:
        """Handle read resource request."""
        try:
            contents = await self._resource_manager.read_resource(message.params.uri)
            # Narrow to allowed types for ReadResourceResult
            allowed_contents = [
                c for c in contents if isinstance(c, (TextResourceContents, BlobResourceContents))
            ]
            return JSONRPCResponse(
                id=message.id,
                result=ReadResourceResult(contents=allowed_contents),
            )
        except NotFoundError:
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32002,
                    "message": (
                        f"✗ Resource not found: {message.params.uri}\n\n"
                        f"  The requested resource does not exist.\n\n"
                        f"  To fix:\n"
                        f"  1. Check the resource URI is correct\n"
                        f"  2. List available resources with resources/list\n"
                        f"  3. Verify the resource provider is loaded\n\n"
                        f"  Resource URIs are case-sensitive."
                    ),
                },
            )
        except Exception:
            logger.exception(f"Error reading resource: {message.params.uri}")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        f"✗ Failed to read resource\n\n"
                        f"  An error occurred while reading: {message.params.uri}\n\n"
                        f"  To troubleshoot:\n"
                        f"  1. Check server logs for details\n"
                        f"  2. Verify you have access to the resource\n"
                        f"  3. Ensure the resource is not corrupted\n"
                        f"  4. Try again or contact support\n\n"
                        f"  The error has been logged."
                    ),
                },
            )

    async def _handle_list_prompts(
        self,
        message: ListPromptsRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListPromptsResult] | JSONRPCError:
        """Handle list prompts request."""
        try:
            prompts = await self._prompt_manager.list_prompts()
            return JSONRPCResponse(id=message.id, result=ListPromptsResult(prompts=prompts))
        except Exception:
            logger.exception("Error listing prompts")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        "✗ Failed to list prompts\n\n"
                        "  An error occurred while retrieving the prompt list.\n\n"
                        "  To troubleshoot:\n"
                        "  1. Check server logs for details\n"
                        "  2. Verify prompt providers are properly configured\n"
                        "  3. Restart the server if needed\n\n"
                        "  The error has been logged."
                    ),
                },
            )

    async def _handle_get_prompt(
        self,
        message: GetPromptRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[GetPromptResult] | JSONRPCError:
        """Handle get prompt request."""
        try:
            result = await self._prompt_manager.get_prompt(
                message.params.name,
                message.params.arguments if hasattr(message.params, "arguments") else None,
            )
            return JSONRPCResponse(id=message.id, result=result)
        except NotFoundError:
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32002,
                    "message": (
                        f"✗ Prompt not found: {message.params.name}\n\n"
                        f"  The requested prompt does not exist.\n\n"
                        f"  To fix:\n"
                        f"  1. Check the prompt name is correct\n"
                        f"  2. List available prompts with prompts/list\n"
                        f"  3. Verify the prompt provider is loaded\n\n"
                        f"  Prompt names are case-sensitive."
                    ),
                },
            )
        except Exception:
            logger.exception(f"Error getting prompt: {message.params.name}")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": (
                        f"✗ Failed to get prompt\n\n"
                        f"  An error occurred while retrieving prompt: {message.params.name}\n\n"
                        f"  To troubleshoot:\n"
                        f"  1. Check server logs for details\n"
                        f"  2. Verify the prompt arguments are valid\n"
                        f"  3. Ensure the prompt is properly configured\n"
                        f"  4. Try again or contact support\n\n"
                        f"  The error has been logged."
                    ),
                },
            )

    async def _handle_set_log_level(
        self,
        message: SetLevelRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[Any] | JSONRPCError:
        """Handle set log level request."""
        try:
            level_name = str(
                message.params.level.value
                if hasattr(message.params.level, "value")
                else message.params.level
            )
            logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
        except Exception:
            logger.setLevel(logging.INFO)

        return JSONRPCResponse(id=message.id, result={})

    # Resource support for Context
    async def _mcp_read_resource(self, uri: str) -> list[Any]:
        """Read a resource (for Context.read_resource)."""
        return await self._resource_manager.read_resource(uri)
