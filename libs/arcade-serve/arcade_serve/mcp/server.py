import asyncio
import json
import logging
import os
import uuid
from enum import Enum
from typing import Any, Callable, Union

from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolAuthorizationContext, ToolContext, ToolMetadataItem
from arcade_tdk import create_tool_logger, create_tool_notifier
from arcadepy import ArcadeError, AsyncArcade
from arcadepy.types.auth_authorize_params import (
    AuthRequirement,
    AuthRequirementOauth2,
)
from arcadepy.types.shared import AuthorizationResponse

from arcade_serve.mcp.convert import convert_to_mcp_content, create_mcp_tool
from arcade_serve.mcp.local_auth import MockArcadeClient
from arcade_serve.mcp.message_processor import (
    create_message_processor,
)
from arcade_serve.mcp.notification_adapter import MCPNotificationBackend
from arcade_serve.mcp.notification_manager import (
    NotificationCapability,
    NotificationManager,
)
from arcade_serve.mcp.types import (
    CallToolRequest,
    CallToolResponse,
    CallToolResult,
    CancelRequest,
    DictResult,
    Implementation,
    InitializeRequest,
    InitializeResponse,
    InitializeResult,
    JSONRPCError,
    JSONRPCResponse,
    ListPromptsRequest,
    ListPromptsResponse,
    ListResourcesRequest,
    ListResourcesResponse,
    ListToolsRequest,
    ListToolsResponse,
    ListToolsResult,
    PingRequest,
    PingResponse,
    ServerCapabilities,
    SetLevelRequest,
    SetLevelResponse,
    ShutdownRequest,
    ShutdownResponse,
    SubscribeRequest,
    SubscribeResponse,
    Tool,
    UnsubscribeRequest,
    UnsubscribeResponse,
)

logger = logging.getLogger("arcade.mcp")

MCP_PROTOCOL_VERSION = "2024-11-05"


class MessageMethod(str, Enum):
    """Enumeration of supported MCP message methods"""

    PING = "ping"
    INITIALIZE = "initialize"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    CANCEL = "$/cancelRequest"
    SHUTDOWN = "shutdown"
    LIST_RESOURCES = "resources/list"
    LIST_PROMPTS = "prompts/list"
    SET_LOG_LEVEL = "logging/setLevel"
    # Notification subscription methods
    SUBSCRIBE = "notifications/subscribe"
    UNSUBSCRIBE = "notifications/unsubscribe"


class MCPServer:
    """
    Unified async MCP server that manages connections, middleware, and tool invocation.
    Handles protocol-level messages (ping, initialize, list_tools, call_tool, etc.).
    """

    def __init__(
        self,
        catalog: ToolCatalog,
        auth_disabled: bool = False,
        local_context: dict[str, Any] | None = None,
        arcade_api_key: str | None = None,
        arcade_api_url: str | None = None,
        enable_logging: bool | None = None,
    ):
        """
        Initialize the MCP server.

        Args:
            catalog: The tool catalog to use
            auth_disabled: Whether authentication is disabled for this server
            local_context: Local context configuration from worker.toml
            arcade_api_key: API key for Arcade (if using real client)
            arcade_api_url: API URL for Arcade (if using real client)
            enable_logging: Optional flag to enable or disable extra logging (unused)
        """
        self.tool_catalog = catalog
        self.auth_disabled = auth_disabled
        self.local_context = local_context or {}

        # Initialize message processor for middleware handling
        self.message_processor = create_message_processor()

        # Initialize arcade client (real or mock)
        self._init_arcade_client(arcade_api_key, arcade_api_url)

        # Transport-specific write streams for notification delivery
        self.write_streams: dict[str, Any] = {}

        # Per-client log levels
        self.client_log_levels: dict[str, str] = {}

        # Initialize notification manager
        self.notification_manager: NotificationManager | None = None
        self._init_notification_manager()

        self.dispatch_table: dict[str, Callable] = {
            MessageMethod.PING: self._handle_ping,
            MessageMethod.INITIALIZE: self._handle_initialize,
            MessageMethod.LIST_TOOLS: self._handle_list_tools,
            MessageMethod.CALL_TOOL: self._handle_call_tool,
            MessageMethod.CANCEL: self._handle_cancel,
            MessageMethod.SHUTDOWN: self._handle_shutdown,
            MessageMethod.LIST_RESOURCES: self._handle_list_resources,
            MessageMethod.LIST_PROMPTS: self._handle_list_prompts,
            MessageMethod.SET_LOG_LEVEL: self._handle_set_log_level,
            MessageMethod.SUBSCRIBE: self._handle_subscribe,
            MessageMethod.UNSUBSCRIBE: self._handle_unsubscribe,
        }

    def _init_arcade_client(self, arcade_api_key: str | None, arcade_api_url: str | None) -> None:
        """
        Initialize the arcade client (real or mock based on configuration).

        Args:
            arcade_api_key: API key for real Arcade client
            arcade_api_url: API URL for real Arcade client
        """
        # Check if we have local auth providers configured
        local_auth_providers = self.local_context.get("local_auth_providers")

        if local_auth_providers and not arcade_api_key:
            # Use mock client for local development
            logger.info("Using mock Arcade client with local auth providers")
            self.arcade = MockArcadeClient(auth_providers=local_auth_providers)
        else:
            # Use real Arcade client
            if not arcade_api_key:
                arcade_api_key = os.environ.get("ARCADE_API_KEY")
            if not arcade_api_url:
                arcade_api_url = os.environ.get("ARCADE_API_URL", "https://api.arcade.dev")

            if arcade_api_key:
                logger.info(f"Using Arcade client with API URL: {arcade_api_url}")
                self.arcade = AsyncArcade(
                    api_key=arcade_api_key,
                    base_url=arcade_api_url,
                )
            else:
                logger.warning(
                    "No Arcade API key found. Auth-required tools will fail. "
                    "Set ARCADE_API_KEY to enable auth-required tools."
                )
                # Use mock client with no providers as fallback
                self.arcade = MockArcadeClient()

    def _init_notification_manager(self) -> None:
        """Initialize the notification manager with self as the sender."""

        # Create a NotificationSender that uses the server's write streams
        class ServerNotificationSender:
            def __init__(self, server: "MCPServer"):
                self.server = server

            async def send_notification(self, client_id: str, notification: dict[str, Any]) -> bool:
                """Send a notification to a specific client."""
                write_stream = self.server.write_streams.get(client_id)
                if write_stream:
                    try:
                        # Ensure each notification is a single NDJSON line
                        message = json.dumps(notification)
                        if not message.endswith("\n"):
                            message += "\n"
                        await write_stream.send(message)
                        return True  # noqa: TRY300
                    except Exception as e:
                        logger.debug(f"Failed to send notification to client {client_id}: {e}")
                        return False
                return False

        self.notification_manager = NotificationManager(
            sender=ServerNotificationSender(self),
            rate_limit_per_minute=60,
            default_debounce_ms=100,
        )

    async def run_connection(
        self,
        read_stream: Any,
        write_stream: Any,
        init_options: Any,
    ) -> None:
        """
        Handle a single MCP connection (SSE or stdio).

        Args:
            read_stream: Async iterable yielding incoming messages.
            write_stream: Object with an async send(message) method.
            init_options: Initialization options for the connection.
        """
        # Generate a user ID if possible
        user_id = self._get_user_id(init_options)

        # Register write stream for notifications
        self.write_streams[user_id] = write_stream

        # Start notification manager if not already started
        if self.notification_manager and not hasattr(self, "_notification_manager_started"):
            await self.notification_manager.start()
            self._notification_manager_started = True

        try:
            logger.info(f"Starting MCP connection for user {user_id}")

            # Register client with notification manager
            if self.notification_manager:
                await self.notification_manager.register_client(user_id, [])

            async for message in read_stream:
                # Process the message
                response = await self.handle_message(message, user_id=user_id)

                # Skip sending responses for None (e.g., notifications)
                if response is None:
                    continue

                await self._send_response(write_stream, response)

        except asyncio.CancelledError:
            logger.info("Connection cancelled")
        except Exception:
            logger.exception("Error in connection")
        finally:
            # Cleanup on connection close
            if user_id in self.write_streams:
                del self.write_streams[user_id]

            if self.notification_manager:
                await self.notification_manager.unregister_client(user_id)

    def _get_user_id(self, init_options: Any) -> str:
        """
        Get the user ID for a connection.

        Args:
            init_options: Initialization options for the connection

        Returns:
            A user ID string
        """
        try:
            from arcade_core.config import config

            # Prefer config.user.email if available
            if config.user and config.user.email:
                return config.user.email
        except ValueError:
            logger.debug("No logged in user for MCP Server")

        fallback = str(uuid.uuid4())
        if os.environ.get("ARCADE_USER_ID", None):
            return os.environ.get("ARCADE_USER_ID", fallback)
        elif isinstance(init_options, dict):
            user_id = init_options.get("user_id")
            if user_id:
                return str(user_id)
        # Fallback to random UUID
        return str(fallback)

    async def _send_response(self, write_stream: Any, response: Any) -> None:
        """
        Send a response to the client.

        Args:
            write_stream: Stream to write the response to
            response: Response object to send
        """
        # Ensure the response is properly serialized to JSON
        if hasattr(response, "model_dump_json"):
            # It's a Pydantic model, serialize it
            json_response = response.model_dump_json()
            # Ensure it ends with a newline for JSON-RPC-over-stdio
            if not json_response.endswith("\n"):
                json_response += "\n"
            logger.debug(f"Sending response: {json_response[:200]}...")
            await write_stream.send(json_response)
        elif isinstance(response, dict):
            # It's a dict, convert to JSON
            import json

            json_response = json.dumps(response)
            # Ensure it ends with a newline for JSON-RPC-over-stdio
            if not json_response.endswith("\n"):
                json_response += "\n"
            logger.debug(f"Sending response: {json_response[:200]}...")
            await write_stream.send(json_response)
        else:
            # It's already a string or something else
            response_str = str(response)
            # Ensure it ends with a newline for JSON-RPC-over-stdio
            if not response_str.endswith("\n"):
                response_str += "\n"
            logger.debug(f"Sending raw response type: {type(response)}")
            await write_stream.send(response_str)

    async def handle_message(self, message: Any, user_id: str | None = None) -> Any:  # noqa: C901
        """
        Handle an incoming MCP message. Processes it through middleware and dispatches
        to the appropriate handler based on the message method.

        Args:
            message: The raw incoming message
            user_id: Optional user ID for authentication

        Returns:
            A properly formatted response message
        """
        # Pre-process message through middleware
        processed = await self.message_processor.process_request(message)

        # Handle special case for JSON string initialize requests
        if isinstance(processed, str):
            try:
                import json

                parsed = json.loads(processed)
                if (
                    isinstance(parsed, dict)
                    and parsed.get("method") == MessageMethod.INITIALIZE
                    and "id" in parsed
                ):
                    # This is an initialize request
                    init_response = await self._handle_initialize(
                        InitializeRequest(**parsed), user_id=user_id
                    )
                    return init_response
            except Exception:
                logger.exception("Error processing JSON string")
                # Not parseable JSON, continue with normal processing
                pass

        # Get method from processed message (handle both dict and object)
        method = None
        if isinstance(processed, dict):
            method = processed.get("method")
        elif hasattr(processed, "method"):
            method = getattr(processed, "method", None)

        # Handle notifications (methods starting with "notifications/")
        if method and method.startswith("notifications/"):
            await self._handle_notification(method, processed)
            return None

        # Handle regular methods using the dispatch table
        if method in self.dispatch_table:
            # Convert dict to appropriate request type if needed
            if isinstance(processed, dict):
                # Convert based on method type
                if method == MessageMethod.INITIALIZE:
                    processed = InitializeRequest(**processed)
                elif method == MessageMethod.CALL_TOOL:
                    processed = CallToolRequest(**processed)
                elif method == MessageMethod.LIST_TOOLS:
                    processed = ListToolsRequest(**processed)
                elif method == MessageMethod.PING:
                    processed = PingRequest(**processed)
                elif method == MessageMethod.SUBSCRIBE:
                    processed = SubscribeRequest(**processed)
                elif method == MessageMethod.UNSUBSCRIBE:
                    processed = UnsubscribeRequest(**processed)
                elif method == MessageMethod.LIST_RESOURCES:
                    processed = ListResourcesRequest(**processed)
                elif method == MessageMethod.LIST_PROMPTS:
                    processed = ListPromptsRequest(**processed)
                elif method == MessageMethod.SET_LOG_LEVEL:
                    processed = SetLevelRequest(**processed)
                elif method == MessageMethod.SHUTDOWN:
                    processed = ShutdownRequest(**processed)
                elif method == MessageMethod.CANCEL:
                    processed = CancelRequest(**processed)

            # Methods that need user_id
            if method in [
                MessageMethod.CALL_TOOL,
                MessageMethod.INITIALIZE,
                MessageMethod.SUBSCRIBE,
                MessageMethod.UNSUBSCRIBE,
            ]:
                return await self.dispatch_table[method](processed, user_id=user_id)
            # For other methods, just pass the processed message
            return await self.dispatch_table[method](processed)

        # Unknown method
        return JSONRPCError(
            id=getattr(processed, "id", None)
            if hasattr(processed, "id")
            else processed.get("id")
            if isinstance(processed, dict)
            else None,
            error={
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        )

        # If it's not a method request, just pass it through
        return processed

    async def _handle_notification(self, method: str, message: Any) -> None:
        """
        Handle notification messages.

        Args:
            method: The notification method
            message: The notification message
        """
        if method == "notifications/cancelled":
            logger.info(f"Request cancelled: {getattr(message, 'params', {})}")
        else:
            logger.debug(f"Received notification: {method}")

    async def _handle_ping(self, message: PingRequest) -> PingResponse:
        """
        Handle a ping request and return a pong response.

        Args:
            message: The ping request

        Returns:
            A properly formatted pong response
        """
        return PingResponse(id=message.id or 0)

    async def _handle_initialize(
        self, message: InitializeRequest, user_id: str | None = None
    ) -> InitializeResponse:
        """
        Handle an initialize request and return a proper initialize response.

        Args:
            message: The initialize request
            user_id: Optional user ID for the connection

        Returns:
            A properly formatted initialize response
        """
        # Extract client capabilities from the request
        client_capabilities = []
        if message.params and "capabilities" in message.params:
            client_caps = message.params["capabilities"]
            if isinstance(client_caps, dict) and "notifications" in client_caps:
                notifications = client_caps["notifications"]
                if isinstance(notifications, dict):
                    for method, enabled in notifications.items():
                        if enabled:
                            client_capabilities.append(NotificationCapability(method=method))

        # Register client capabilities with notification manager
        if self.notification_manager and user_id:
            # Update client with their notification capabilities
            async with self.notification_manager.clients_lock:
                if user_id in self.notification_manager.clients:
                    self.notification_manager.clients[user_id].capabilities = client_capabilities

        # Create the result data with notification support
        result = InitializeResult(
            protocolVersion=MCP_PROTOCOL_VERSION,
            capabilities=ServerCapabilities(
                tools={"listChanged": True},  # Server supports tool change notifications
                logging={},  # Server supports logging
                # Add notification capabilities
                notifications={
                    "progress": True,
                    "message": True,
                    "resources": {
                        "listChanged": True,
                        "updated": True,
                    },
                    "tools": {
                        "listChanged": True,
                    },
                },
            ),
            serverInfo=Implementation(
                name="Arcade MCP Worker",
                version="0.1.0",
                title="Arcade Model Context Protocol Worker",
            ),
            instructions="The Arcade MCP Worker provides access to tools defined in Arcade toolkits. Use 'tools/list' to see available tools and 'tools/call' to execute them. This server supports notifications for progress tracking, messages, and resource/tool updates.",
        )

        # Construct proper response with result field
        response = InitializeResponse(id=message.id or 0, result=result)

        logger.debug(f"Initialize response: {response.model_dump_json()}")
        return response

    async def _handle_list_tools(
        self, message: ListToolsRequest
    ) -> Union[ListToolsResponse, JSONRPCError]:
        """
        Handle a tools/list request and return a list of available tools.

        Args:
            message: The tools/list request

        Returns:
            A properly formatted tools/list response or error
        """
        try:
            # Get all tools from the catalog
            tools = []
            tool_conversion_errors = []

            for tool in self.tool_catalog:
                try:
                    mcp_tool = create_mcp_tool(tool)
                    if mcp_tool:
                        tools.append(mcp_tool)
                except Exception:
                    tool_name = getattr(tool, "name", str(tool))
                    logger.exception(f"Error converting tool: {tool_name}")
                    tool_conversion_errors.append(tool_name)

            # Log summary if we had errors
            if tool_conversion_errors:
                logger.warning(
                    f"Failed to convert {len(tool_conversion_errors)} tools: {tool_conversion_errors}"
                )

            # Create tool objects with exception handling for each one
            tool_objects = []
            for t in tools:
                try:
                    # Make input schema optional if missing
                    tool_dict = dict(t)
                    if "inputSchema" not in tool_dict:
                        tool_dict["inputSchema"] = {
                            "type": "object",
                            "properties": {},
                        }

                    tool_objects.append(Tool(**tool_dict))
                except Exception:
                    logger.exception(f"Error creating Tool object for {t.get('name', 'unknown')}")

            # For now, we don't implement pagination, so return all tools
            # and don't set nextCursor
            result = ListToolsResult(tools=tool_objects)
            response = ListToolsResponse(id=message.id or 0, result=result)

        except Exception:
            logger.exception("Error listing tools")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": "Internal error listing tools",
                },
            )
        return response

    async def _handle_call_tool(  # noqa: C901
        self, message: CallToolRequest, user_id: str | None = None
    ) -> CallToolResponse:
        """
        Handle a tools/call request to execute a tool.

        Args:
            message: The tools/call request
            user_id: Optional user ID for authentication

        Returns:
            A properly formatted tools/call response
        """
        tool_name: str = message.params["name"]
        # According to MCP spec, arguments come in params.arguments
        input_params: dict[str, Any] = message.params.get("arguments", {})

        # Extract progress token from request metadata if present
        progress_token = None
        if hasattr(message, "get_progress_token"):
            progress_token = message.get_progress_token()
        elif message.params and "_meta" in message.params:
            meta = message.params["_meta"]
            if isinstance(meta, dict) and "progressToken" in meta:
                progress_token = meta["progressToken"]

        logger.info(f"Handling tool call for {tool_name}")

        try:
            tool = self.tool_catalog.get_tool_by_name(tool_name, separator="_")

            # Create tool context
            tool_context = ToolContext()

            # Apply local context from worker.toml or environment
            self._apply_local_context(tool_context, user_id)

            # Set progress token if provided
            if progress_token:
                tool_context.progress_token = progress_token

            # Add notification support if available
            if self.notification_manager and user_id:
                # Get client's log level (default to info)
                min_log_level = self.client_log_levels.get(user_id, "info")

                backend = MCPNotificationBackend(
                    self.notification_manager, user_id, min_log_level=min_log_level
                )
                logger_instance = create_tool_logger(backend, tool_name)
                notifier_instance = create_tool_notifier(backend, progress_token)
                tool_context.set_notification_support(logger_instance, notifier_instance)
                tool_context.set_min_log_level(min_log_level)

            # Set up context with secrets
            if tool.definition.requirements and tool.definition.requirements.secrets:
                self._setup_tool_secrets(tool, tool_context)

            # Handle authorization if needed
            requirement = self._get_auth_requirement(tool)
            if requirement and not self.auth_disabled:
                # Use the arcade client (real or mock) for authorization
                auth_result = await self._check_authorization(
                    requirement, user_id=user_id or self.local_context.get("user_id")
                )
                if auth_result.status != "completed":
                    return CallToolResponse(
                        id=message.id or 0,
                        result=CallToolResult(content=[{"type": "text", "text": auth_result.url}]),
                    )
                else:
                    tool_context.authorization = ToolAuthorizationContext(
                        token=auth_result.context.token if auth_result.context else None,
                        user_info={"user_id": user_id} if user_id else {},
                    )

            # Execute the tool
            logger.debug(f"Executing tool {tool_name} with input: {input_params}")
            result = await ToolExecutor.run(
                func=tool.tool,
                definition=tool.definition,
                input_model=tool.input_model,
                output_model=tool.output_model,
                context=tool_context,
                **input_params,
            )
            logger.debug(f"Tool result: {result}")
            if result.value is not None or (result.value is not None and not result.error):
                # Handle structured content for dict/list values
                structured_content = None

                # Determine if the tool declared an output schema (clients expect structuredContent)
                require_structured = bool(
                    getattr(tool.definition, "output", None)
                    and getattr(tool.definition.output, "value_schema", None) is not None
                )

                # If the value is a dict, also provide it as structured content
                if isinstance(result.value, dict):
                    structured_content = result.value
                elif require_structured:
                    # Wrap non-dict results to satisfy clients expecting an object
                    structured_content = {"result": result.value}

                # Build unstructured content text. If we have structured content, ensure a
                # matching text block exists so validators can correlate both representations.
                if structured_content is not None:
                    try:
                        content = [{"type": "text", "text": json.dumps(structured_content)}]
                    except Exception:
                        content = convert_to_mcp_content(result.value)
                else:
                    content = convert_to_mcp_content(result.value)

                response = CallToolResponse(
                    id=message.id or 0,
                    result=CallToolResult(
                        content=content,
                        structuredContent=structured_content,
                        isError=False,
                    ),
                )

                # Include logs if any
                if result.logs:
                    for log in result.logs:
                        logger.log(
                            getattr(logging, log.level.upper(), logging.INFO),
                            f"Tool log: {log.message}",
                        )

                return response
            else:
                error = result.error or "Error calling tool"
                logger.error(f"Tool {tool_name} returned error: {error}")
                return CallToolResponse(
                    id=message.id or 0,
                    result=CallToolResult(
                        content=[{"type": "text", "text": str(error)}], isError=True
                    ),
                )
        except Exception as e:
            logger.exception(f"Error calling tool {tool_name}")
            error_msg = f"Error calling tool {tool_name}: {e!s}"
            return CallToolResponse(
                id=message.id or 0,
                result=CallToolResult(content=[{"type": "text", "text": error_msg}], isError=True),
            )

    def _setup_tool_secrets(self, tool: Any, tool_context: ToolContext) -> None:
        """
        Set up tool secrets in the tool context.

        Args:
            tool: The tool to set up secrets for
            tool_context: The tool context to update
        """
        for secret in tool.definition.requirements.secrets:
            value = os.environ.get(secret.key)
            if value is not None:
                tool_context.set_secret(secret.key, value)

    def _apply_local_context(self, tool_context: ToolContext, user_id: str | None = None) -> None:
        """
        Apply local context configuration to the tool context.

        This method sets up user IDs and metadata for local development.
        Priority order:
        1. Environment variables (ARCADE_USER_ID, ARCADE_USER_EMAIL, etc.)
        2. worker.toml local_context configuration
        3. Method parameters

        Args:
            tool_context: The tool context to update
            user_id: Optional user ID passed from the request
        """
        # Set user_id (priority: parameter > env > config)
        final_user_id = (
            user_id or os.environ.get("ARCADE_USER_ID") or self.local_context.get("user_id")
        )
        if final_user_id:
            tool_context.user_id = final_user_id

        # Additional metadata from environment
        if os.environ.get("ARCADE_USER_EMAIL"):
            if not tool_context.metadata:
                tool_context.metadata = []
            tool_context.metadata.append(
                ToolMetadataItem(key="user_email", value=os.environ.get("ARCADE_USER_EMAIL"))
            )

        # Apply any additional metadata from local_context
        local_metadata = self.local_context.get("metadata", {})
        for key, value in local_metadata.items():
            if not tool_context.metadata:
                tool_context.metadata = []
            # Check if metadata key already exists
            existing = next((m for m in tool_context.metadata if m.key == key), None)
            if not existing:
                tool_context.metadata.append(ToolMetadataItem(key=key, value=str(value)))

    async def _handle_cancel(self, message: CancelRequest) -> JSONRPCResponse:
        """
        Handle a cancel request.

        Args:
            message: The cancel request

        Returns:
            A response acknowledging the cancellation
        """
        return JSONRPCResponse(id=message.id or 0, result={"ok": True})

    async def _handle_shutdown(self, message: ShutdownRequest) -> ShutdownResponse:
        """
        Handle a shutdown request.

        Args:
            message: The shutdown request

        Returns:
            A response acknowledging the shutdown request
        """
        # Schedule a task to shutdown the server after sending the response
        proc = asyncio.create_task(self.shutdown())
        proc.add_done_callback(lambda _: logger.info("MCP server shutdown complete"))
        return ShutdownResponse(id=message.id or 0, result={"ok": True})

    async def _handle_list_resources(self, message: ListResourcesRequest) -> ListResourcesResponse:
        """
        Handle a resources/list request.

        Args:
            message: The resources/list request

        Returns:
            A properly formatted resources/list response
        """
        return ListResourcesResponse(id=message.id or 0, result=DictResult(data={"resources": []}))

    async def _handle_list_prompts(self, message: ListPromptsRequest) -> ListPromptsResponse:
        """
        Handle a prompts/list request.

        Args:
            message: The prompts/list request

        Returns:
            A properly formatted prompts/list response
        """
        return ListPromptsResponse(id=message.id or 0, result=DictResult(data={"prompts": []}))

    async def _handle_set_log_level(
        self, message: SetLevelRequest, user_id: str | None = None
    ) -> SetLevelResponse:
        """
        Handle a logging/setLevel request.

        Args:
            message: The logging/setLevel request
            user_id: Optional user ID for this connection

        Returns:
            A response acknowledging the log level change
        """
        level = message.params.get("level")
        if level is None:
            return SetLevelResponse(id=message.id or 0, result={})

        # Store the log level for this client
        if user_id:
            self.client_log_levels[user_id] = level.lower()

        # Map MCP log levels to Python log levels
        level_mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "notice": logging.INFO,  # Python doesn't have notice, map to info
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "alert": logging.CRITICAL,  # Python doesn't have alert, map to critical
            "emergency": logging.CRITICAL,  # Python doesn't have emergency, map to critical
        }

        numeric_level = level_mapping.get(level.lower())
        if numeric_level is None:
            # Invalid level, but we still return success per spec
            return SetLevelResponse(id=message.id or 0, result={})

        logger.setLevel(numeric_level)
        logger.info(f"Log level set to {level}")
        return SetLevelResponse(id=message.id or 0, result=DictResult(data={"ok": True}))

    async def _handle_subscribe(
        self, message: SubscribeRequest, user_id: str | None = None
    ) -> Union[SubscribeResponse, JSONRPCError]:
        """
        Handle a notification subscription request.

        Args:
            message: The subscribe request
            user_id: Optional user ID for the connection

        Returns:
            A subscribe response or error
        """
        if not self.notification_manager or not user_id:
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": "Notifications not supported or client not registered",
                },
            )

        try:
            # Extract notification types from params
            notification_types = []
            if message.params and "types" in message.params:
                types = message.params["types"]
                if isinstance(types, list):
                    notification_types = types

            # Subscribe the client
            subscriptions = await self.notification_manager.subscribe(
                user_id,
                notification_types,
                filters=message.params.get("filters") if message.params else None,
            )

            # Return response with subscriptions
            result: dict[str, Any] = {
                "subscriptions": [sub.model_dump(exclude_none=True) for sub in subscriptions]
            }
            return SubscribeResponse(id=message.id or 0, result=result)

        except ValueError as e:
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32602,
                    "message": str(e),
                },
            )
        except Exception as e:
            logger.exception("Error handling subscribe request")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": f"Failed to subscribe: {e!s}",
                },
            )

    async def _handle_unsubscribe(
        self, message: UnsubscribeRequest, user_id: str | None = None
    ) -> Union[UnsubscribeResponse, JSONRPCError]:
        """
        Handle a notification unsubscription request.

        Args:
            message: The unsubscribe request
            user_id: Optional user ID for the connection

        Returns:
            An unsubscribe response or error
        """
        if not self.notification_manager or not user_id:
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": "Notifications not supported or client not registered",
                },
            )

        try:
            # Extract subscription IDs from params
            subscription_ids = []
            if message.params and "subscription_ids" in message.params:
                ids = message.params["subscription_ids"]
                if isinstance(ids, list):
                    subscription_ids = ids

            # Unsubscribe the client
            success = await self.notification_manager.unsubscribe(
                user_id,
                subscription_ids,
            )

            # Return response
            result: dict[str, Any] = {"success": success}
            return UnsubscribeResponse(id=message.id or 0, result=result)

        except Exception as e:
            logger.exception("Error handling unsubscribe request")
            return JSONRPCError(
                id=message.id,
                error={
                    "code": -32603,
                    "message": f"Failed to unsubscribe: {e!s}",
                },
            )

    def _get_auth_requirement(self, tool: MaterializedTool) -> AuthRequirement | None:
        """
        Get the authentication requirement for a tool.

        Args:
            tool: The tool to get the requirement for

        Returns:
            An authentication requirement or None if not required
        """
        req = tool.definition.requirements.authorization
        if not req:
            return None
        if not req.provider_id and not req.provider_type:
            return None
        if hasattr(req, "oauth2") and req.oauth2:
            return AuthRequirement(
                provider_id=str(req.provider_id),
                provider_type=str(req.provider_type),
                oauth2=AuthRequirementOauth2(scopes=req.oauth2.scopes or []),
            )
        return AuthRequirement(
            provider_id=str(req.provider_id),
            provider_type=str(req.provider_type),
        )

    async def _check_authorization(
        self, auth_requirement: AuthRequirement, user_id: str | None = None
    ) -> AuthorizationResponse:
        """
        Check if a tool is authorized for a user.

        Args:
            tool: The tool to check authorization for
            user_id: The user ID to check authorization for

        Returns:
            An authorization response

        Raises:
            RuntimeError: If the tool has no authorization requirement
            Exception: If authorization fails
        """
        try:
            response = await self.arcade.auth.authorize(
                auth_requirement=auth_requirement,
                user_id=user_id or "anonymous",
            )
            logger.debug(f"Authorization response: {response}")

        except ArcadeError:
            logger.exception("Error authorizing tool")
            raise
        return response

    async def shutdown(self) -> None:
        """Shutdown the server."""
        self._shutdown = True

        # Stop notification manager
        if self.notification_manager and hasattr(self, "_notification_manager_started"):
            await self.notification_manager.stop()
            self._notification_manager_started = False

        logger.info("MCP server shutdown complete")
