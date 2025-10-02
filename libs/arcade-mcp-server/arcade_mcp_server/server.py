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

from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.executor import ToolExecutor
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
from arcade_mcp_server.session import InitializationState, NotificationManager, ServerSession
from arcade_mcp_server.settings import MCPSettings
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
        name: str = "ArcadeMCP",
        version: str = "0.1.0",
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
        self.name = name or self.__class__.__name__
        self._started = False
        self._lock = asyncio.Lock()

        # Server identity
        self.version = version
        self.title = title or name
        self.instructions = instructions or self._default_instructions()

        # Settings
        self.settings = settings or MCPSettings.from_env()
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

        # Handler registration
        self._handlers = self._register_handlers()

    def _load_config_values(self) -> tuple[str | None, str | None]:
        """Load API key and user_id from credentials file.

        Returns:
            Tuple of (api_key, user_id) from credentials file, or (None, None) if not available
        """
        try:
            from arcade_core.config import config

            api_key = config.api.key if config.api else None
            user_id = config.user.email if config.user else None

            if api_key or user_id:
                config_path = config.get_config_file_path()
                if api_key:
                    logger.info(f"Loaded Arcade API key from {config_path}")
                if user_id:
                    logger.debug(f"Loaded user_id '{user_id}' from {config_path}")
                return api_key, user_id
            else:
                logger.debug("No API key or user_id found in credentials file")
                return None, None
        except Exception as e:
            logger.debug(f"Could not load values from credentials file: {e}")
            return None, None

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
            self.arcade = AsyncArcade(api_key=final_api_key, base_url=api_url)
        else:
            logger.warning(
                "Arcade API key not configured. Tools requiring auth will return a login instruction."
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
    ) -> MCPMessage | None:
        """
        Handle an incoming message.

        Args:
            message: Message to handle
            session: Server session

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
                error={"code": -32600, "message": "Invalid request"},
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
                    "message": "Request not allowed before initialization",
                },
            )

        # Find handler
        handler = self._handlers.get(method)
        if not handler:
            return JSONRPCError(
                id=str(msg_id or "null"),
                error={"code": -32601, "message": f"Method not found: {method}"},
            )

        # Create context and apply middleware
        try:
            # Create request context
            context = (
                await session.create_request_context()
                if session
                else Context(self, request_id=str(msg_id) if msg_id else None)
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

        except Exception:
            logger.exception("Error handling message")
            return JSONRPCError(
                id=str(msg_id or "null"),
                error={"code": -32603, "message": "Internal error"},
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
                error={"code": -32603, "message": "Internal error listing tools"},
            )

    async def _create_tool_context(
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

        # user_id selection
        env = (self.settings.arcade.environment or "").lower()
        user_id = self.settings.arcade.user_id

        # If no user_id from env, try credentials file
        if not user_id:
            _, config_user_id = self._load_config_values()
            user_id = config_user_id

        if user_id:
            tool_context.user_id = user_id
            logger.debug(f"Context user_id set: {user_id}")
        elif env in ("development", "dev", "local"):
            tool_context.user_id = session.session_id if session else None
            logger.debug(f"Context user_id set from session (dev env={env})")
        else:
            tool_context.user_id = session.session_id if session else None
            logger.debug("Context user_id set from session (non-dev env)")

        return tool_context

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
            tool_context = await self._create_tool_context(tool, session)

            # Handle authorization and secrets requirements if required
            if missing_requirements_response := await self._check_tool_requirements(
                tool, tool_context, message, tool_name
            ):
                return missing_requirements_response

            # Attach tool_context to current model context for this request
            mctx = get_current_model_context()
            if mctx is not None:
                mctx.set_tool_context(tool_context)

            # Execute tool
            result = await ToolExecutor.run(
                func=tool.tool,
                definition=tool.definition,
                input_model=tool.input_model,
                output_model=tool.output_model,
                context=tool_context,
                **input_params,
            )

            # Convert result
            if result.value is not None:
                content = convert_to_mcp_content(result.value)

                # structuredContent should be the raw result value as a JSON object
                structured_content = convert_content_to_structured_content(result.value)

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
            error_message = f"Unknown tool: {tool_name}"
            content = convert_to_mcp_content(error_message)

            # structuredContent should be the error as a JSON object
            structured_content = convert_content_to_structured_content({"error": error_message})

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
            return JSONRPCError(
                id=message.id,
                error={"code": -32603, "message": "Internal error calling tool"},
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

    async def _check_tool_requirements(
        self,
        tool: MaterializedTool,
        tool_context: ToolContext,
        message: CallToolRequest,
        tool_name: str,
    ) -> JSONRPCResponse[CallToolResult] | None:
        """Check tool requirements before executing the tool"""
        # Check authorization
        if tool.definition.requirements and tool.definition.requirements.authorization:
            # First check if Arcade API key is configured
            if not self.arcade:
                tool_response = {
                    "message": f"Tool '{tool_name}' cannot be executed because it requires authorization but no Arcade API key is configured.",
                    "llm_instructions": (
                        f"The MCP server cannot execute the '{tool_name}' tool because it requires authorization "
                        "but the Arcade API key is not configured. The developer needs to: "
                        "1) Set the ARCADE_API_KEY environment variable with a valid API key, or "
                        "2) Run 'arcade login' to authenticate. "
                        "Once the API key is configured, restart the MCP server for the changes to take effect."
                    ),
                }
                return self._create_error_response(message, tool_response)

            # Check authorization status
            try:
                auth_result = await self._check_authorization(tool, tool_context.user_id)
                if auth_result.status != "completed":
                    tool_response = {
                        "message": "The tool was not executed because it requires authorization. This is not an error, but the end user must click the link to complete the OAuth2 flow before the tool can be executed.",
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
                tool_response = {
                    "message": f"Tool '{tool_name}' cannot be executed due to an authorization error: {e}",
                    "llm_instructions": f"The '{tool_name}' tool failed authorization. Error: {e}",
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
                tool_response = {
                    "message": f"Tool '{tool_name}' cannot be executed because it requires the following secrets that are not available: {missing_secrets_str}",
                    "llm_instructions": (
                        f"The MCP server is missing required secrets for the '{tool_name}' tool. "
                        f"The developer needs to provide these secrets by either: "
                        f"1) Adding them to a .env file in the server's working directory (e.g., {missing_secrets[0]}=your_secret_value), "
                        f"2) Setting them as environment variables before starting the server (e.g., export {missing_secrets[0]}=your_secret_value). "
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
                error={"code": -32603, "message": "Internal error listing resources"},
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
                error={"code": -32603, "message": "Internal error listing resource templates"},
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
                error={"code": -32002, "message": f"Resource not found: {message.params.uri}"},
            )
        except Exception:
            logger.exception(f"Error reading resource: {message.params.uri}")
            return JSONRPCError(
                id=message.id,
                error={"code": -32603, "message": "Internal error reading resource"},
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
                error={"code": -32603, "message": "Internal error listing prompts"},
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
                error={"code": -32002, "message": f"Prompt not found: {message.params.name}"},
            )
        except Exception:
            logger.exception(f"Error getting prompt: {message.params.name}")
            return JSONRPCError(
                id=message.id,
                error={"code": -32603, "message": "Internal error getting prompt"},
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
