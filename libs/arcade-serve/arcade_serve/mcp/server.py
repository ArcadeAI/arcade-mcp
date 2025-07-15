import asyncio
import logging
import os
import uuid
from enum import Enum
from typing import Any, Callable, Union

from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolAuthorizationContext, ToolContext
from arcadepy import ArcadeError, AsyncArcade
from arcadepy.types.auth_authorize_params import AuthRequirement, AuthRequirementOauth2
from arcadepy.types.shared import AuthorizationResponse

from arcade_serve.mcp.convert import convert_to_mcp_content, create_mcp_tool
from arcade_serve.mcp.logging import create_mcp_logging_middleware
from arcade_serve.mcp.message_processor import MCPMessageProcessor, create_message_processor
from arcade_serve.mcp.types import (
    CallToolRequest,
    CallToolResponse,
    CallToolResult,
    CancelRequest,
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
    ProgressNotification,
    ServerCapabilities,
    ShutdownRequest,
    ShutdownResponse,
    Tool,
)

logger = logging.getLogger("arcade.mcp")

MCP_PROTOCOL_VERSION = "2024-11-05"


class MessageMethod(str, Enum):
    """Enumeration of supported MCP message methods"""

    PING = "ping"
    INITIALIZE = "initialize"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    PROGRESS = "progress"
    CANCEL = "$/cancelRequest"
    SHUTDOWN = "shutdown"
    LIST_RESOURCES = "resources/list"
    LIST_PROMPTS = "prompts/list"


class MCPServer:
    """
    Unified async MCP server that manages connections, middleware, and tool invocation.
    Handles protocol-level messages (ping, initialize, list_tools, call_tool, etc.).
    """

    def __init__(
        self,
        tool_catalog: Any,
        enable_logging: bool = True,
        **client_kwargs: dict[str, Any],
    ) -> None:
        """
        Initialize the MCP server.

        Args:
            tool_catalog: Catalog of available tools
            **client_kwargs: Additional arguments to pass to the AsyncArcade client
        """
        self.tool_catalog: ToolCatalog = tool_catalog
        self.message_processor: MCPMessageProcessor = create_message_processor()

        # Pop middleware_config from client_kwargs regardless of logging state,
        # as it's internal config not meant for AsyncArcade.
        middleware_config = client_kwargs.pop("middleware_config", {})

        if enable_logging:
            # Create and add the logging middleware if logging is enabled.
            # Note: enable_logging must be True for this middleware (and its stdio_mode behavior)
            # to be activated.
            self.message_processor.add_middleware(
                create_mcp_logging_middleware(**middleware_config)
            )

        self._shutdown: bool = False
        # Initialize AsyncArcade with the *remaining* client_kwargs
        self.arcade = AsyncArcade(**client_kwargs)  # type: ignore[arg-type]

        # Initialize handler dispatch table
        self._method_handlers: dict[str, Callable] = {
            MessageMethod.PING: self._handle_ping,
            MessageMethod.INITIALIZE: self._handle_initialize,
            MessageMethod.LIST_TOOLS: self._handle_list_tools,
            MessageMethod.CALL_TOOL: self._handle_call_tool,
            MessageMethod.PROGRESS: self._handle_progress,
            MessageMethod.CANCEL: self._handle_cancel,
            MessageMethod.SHUTDOWN: self._handle_shutdown,
            MessageMethod.LIST_RESOURCES: self._handle_list_resources,
            MessageMethod.LIST_PROMPTS: self._handle_list_prompts,
        }

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

        try:
            logger.info(f"Starting MCP connection for user {user_id}")

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

    async def handle_message(self, message: Any, user_id: str | None = None) -> Any:
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
                    init_response = await self._handle_initialize(InitializeRequest(**parsed))
                    return init_response
            except Exception:
                logger.exception("Error processing JSON string")
                # Not parseable JSON, continue with normal processing
                pass

        # Check if it's a notification
        if hasattr(processed, "method"):
            method = getattr(processed, "method", None)

            # Handle notifications (methods starting with "notifications/")
            if method and method.startswith("notifications/"):
                await self._handle_notification(method, processed)
                return None

            # Handle regular methods using the dispatch table
            if method in self._method_handlers:
                # If it's a call_tool request, we need to pass the user_id
                if method == MessageMethod.CALL_TOOL:
                    return await self._method_handlers[method](processed, user_id=user_id)
                # For other methods, just pass the processed message
                return await self._method_handlers[method](processed)

            # Unknown method
            return JSONRPCError(
                id=getattr(processed, "id", None),
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
        return PingResponse(id=message.id)

    async def _handle_initialize(self, message: InitializeRequest) -> InitializeResponse:
        """
        Handle an initialize request and return a proper initialize response.

        Args:
            message: The initialize request

        Returns:
            A properly formatted initialize response
        """
        # Create the result data
        result = InitializeResult(
            protocolVersion=MCP_PROTOCOL_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=Implementation(name="Arcade MCP Worker", version="0.1.0"),
            instructions="Arcade MCP Worker initialized.",
        )

        # Construct proper response with result field
        response = InitializeResponse(id=message.id, result=result)

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
                        tool_dict["inputSchema"] = {"type": "object", "properties": {}}

                    tool_objects.append(Tool(**tool_dict))
                except Exception:
                    logger.exception(f"Error creating Tool object for {t.get('name', 'unknown')}")

            # Return successful response with the tools we were able to convert
            result = ListToolsResult(tools=tool_objects)
            response = ListToolsResponse(id=message.id, result=result)

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

    async def _handle_call_tool(
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
        # Extract input from the correct field
        input_params: dict[str, Any] = message.params.get("input", {})
        if not input_params:
            input_params = message.params.get("arguments", {})

        logger.info(f"Handling tool call for {tool_name}")

        try:
            tool = self.tool_catalog.get_tool_by_name(tool_name, separator="_")
            tool_context = ToolContext()

            # Set up context with secrets
            if tool.definition.requirements and tool.definition.requirements.secrets:
                self._setup_tool_secrets(tool, tool_context)

            # Handle authorization if needed
            requirement = self._get_auth_requirement(tool)
            if requirement:
                auth_result = await self._check_authorization(requirement, user_id=user_id)
                if auth_result.status != "completed":
                    return CallToolResponse(
                        id=message.id,
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
            if result.value:
                return CallToolResponse(
                    id=message.id,
                    result=CallToolResult(content=convert_to_mcp_content(result.value)),
                )
            else:
                error = result.error or "Error calling tool"
                logger.error(f"Tool {tool_name} returned error: {error}")
                return CallToolResponse(
                    id=message.id,
                    result=CallToolResult(
                        content=[{"type": "text", "text": convert_to_mcp_content(error)}]
                    ),
                )
        except Exception as e:
            logger.exception(f"Error calling tool {tool_name}")
            error = f"Error calling tool {tool_name}: {e!s}"
            return CallToolResponse(
                id=message.id,
                result=CallToolResult(
                    content=[{"type": "text", "text": convert_to_mcp_content(error)}]
                ),
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

    async def _handle_progress(self, message: ProgressNotification) -> JSONRPCResponse:
        """
        Handle a progress notification.

        Args:
            message: The progress notification

        Returns:
            A response acknowledging the notification
        """
        return JSONRPCResponse(id=getattr(message, "id", None), result={"ok": True})

    async def _handle_cancel(self, message: CancelRequest) -> JSONRPCResponse:
        """
        Handle a cancel request.

        Args:
            message: The cancel request

        Returns:
            A response acknowledging the cancellation
        """
        return JSONRPCResponse(id=getattr(message, "id", None), result={"ok": True})

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
        return ShutdownResponse(id=message.id, result={"ok": True})

    async def _handle_list_resources(self, message: ListResourcesRequest) -> ListResourcesResponse:
        """
        Handle a resources/list request.

        Args:
            message: The resources/list request

        Returns:
            A properly formatted resources/list response
        """
        return ListResourcesResponse(id=message.id, result={"resources": []})

    async def _handle_list_prompts(self, message: ListPromptsRequest) -> ListPromptsResponse:
        """
        Handle a prompts/list request.

        Args:
            message: The prompts/list request

        Returns:
            A properly formatted prompts/list response
        """
        return ListPromptsResponse(id=message.id, result={"prompts": []})

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
        logger.info("MCP server shutdown complete")
