import asyncio
import logging
import os
import threading
from typing import Any

from arcadepy import AsyncArcade
from arcadepy.types.auth_authorize_params import (
    AuthRequirement,
    AuthRequirementOauth2,
)
from arcadepy.types.shared import AuthorizationResponse
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from arcade.core.catalog import MaterializedTool
from arcade.core.config import config
from arcade.core.executor import ToolExecutor
from arcade.core.schema import ToolAuthorizationContext, ToolContext

try:
    from mcp.server.lowlevel.server import lifespan as default_lifespan
    from mcp.server.models import InitializationOptions
    from mcp.server.sse import SseServerTransport
    from mcp.types import (
        EmbeddedResource,
        ImageContent,
        ServerCapabilities,
        TextContent,
    )
    from mcp.types import (
        Tool as MCPTool,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


from arcade.core.schema import FullyQualifiedName
from arcade.worker.core.common import RequestData, Router, Worker, WorkerComponent
from arcade.worker.mcp.components import convert_to_mcp_content, create_mcp_tool
from arcade.worker.mcp.message_processor import create_message_processor
from arcade.worker.mcp.server import PatchedMCPServer

logger = logging.getLogger("arcade.mcp")


class MCPSSEComponent(WorkerComponent):
    """Component for serving tools over SSE using the Model Context Protocol."""

    def __init__(self, worker: Worker, fastapi_app: FastAPI, **config):
        """Initialize the SSE component.

        Args:
            worker: The worker instance that provides the tools
            fastapi_app: The FastAPI app to mount the SSE endpoints to
            **config: Additional configuration options
                sse_path: The path for SSE connections (default: "/sse")
                message_path: The path for message endpoints (default: "/messages/")
                server_name: Name of the MCP server (default: "Arcade MCP Server")
                server_version: Version of the MCP server (default: "1.0.0")
                instructions: Instructions for the MCP server
                middleware: list of middleware to apply to messages
                max_connections: Maximum number of simultaneous SSE connections (default: 100)
                max_worker_threads: Maximum number of worker threads (default: 10)
        """
        super().__init__(worker)

        if not MCP_AVAILABLE:
            raise ImportError(
                "The MCP package is required for SSE support. Install it with 'pip install mcp-sdk'"
            )

        self.fastapi_app = fastapi_app
        self.sse_path = config.get("sse_path", "/sse")
        self.message_path = config.get("message_path", "/messages/")
        self.server_name = config.get("server_name", "Arcade MCP Server")
        self.server_version = config.get("server_version", "1.0.0")
        self.instructions = config.get("instructions")
        self.middleware = config.get("middleware", [])
        self.max_connections = int(config.get("max_connections", 100))
        self.max_worker_threads = int(config.get("max_worker_threads", 10))

        # Track active connections
        self.active_connections: set[str] = set()
        self.connection_count = 0
        self.connection_lock = threading.RLock()

        self.initialized = False

    def register(self, router: Router) -> None:
        """Register with the router.

        Note: This component doesn't use the router directly but mounts
        endpoints to the FastAPI app.
        """
        self._initialize_if_needed()

    def _initialize_if_needed(self):
        """Initialize the MCP server if not already initialized."""
        if self.initialized:
            return
        # Create initialization options with server info and capabilities
        self.init_options = InitializationOptions(
            server_name=self.server_name,
            server_version=self.server_version,
            capabilities=ServerCapabilities(
                tools={"listChanged": True},
                resources=None,  # No resource capabilities for now
                prompts=None,  # No prompt capabilities for now
                logging={},  # Basic logging support
            ),
            instructions=self.instructions,
        )

        # Create MCP server with middleware support and thread pool configuration
        self.mcp_server = PatchedMCPServer(
            name=self.server_name,
            instructions=self.instructions,
            lifespan=default_lifespan,
            max_connections=self.max_connections,
            max_worker_threads=self.max_worker_threads,
        )

        # Set up middleware if provided
        if self.middleware:
            processor = create_message_processor(*self.middleware)
            self.mcp_server.set_message_processor(processor)
            logger.info(f"Initialized MCP message processor with {len(self.middleware)} middleware")

        # Set up MCP handlers
        self.mcp_server.list_tools()(self._list_tools)
        self.mcp_server.call_tool()(self._call_tool)
        self.executor = ToolExecutor()
        # Create SSE transport
        self.sse = SseServerTransport(self.message_path)

        # Make sure the message path ends with a slash for proper mounting
        message_mount_path = self.message_path
        if not message_mount_path.endswith("/"):
            message_mount_path = f"{message_mount_path}/"

        # Make sure the message path doesn't start with a slash for proper URL joining
        if message_mount_path.startswith("/"):
            message_mount_path = message_mount_path[1:]

        # Create Starlette app for SSE
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route(self.sse_path, endpoint=self._handle_sse),
                Mount(f"/{message_mount_path}", app=self.sse.handle_post_message),
            ],
        )

        # Mount Starlette app to FastAPI app
        self.fastapi_app.mount("/mcp", starlette_app)
        self.initialized = True
        logger.info(f"MCP SSE server initialized at /mcp{self.sse_path}")
        logger.info(f"MCP message endpoint available at /mcp/{message_mount_path}")
        logger.info(f"Configured for up to {self.max_connections} simultaneous connections")

    def _get_connection_id(self) -> str:
        """Generate a unique connection ID and track it."""
        with self.connection_lock:
            if len(self.active_connections) >= self.max_connections:
                # Too many connections
                logger.warning(
                    f"Maximum connections ({self.max_connections}) reached, rejecting new connection"
                )
                return ""

            self.connection_count += 1
            conn_id = f"sse_{self.connection_count}"
            self.active_connections.add(conn_id)
            logger.debug(
                f"New connection {conn_id} established. Active connections: {len(self.active_connections)}"
            )
            return conn_id

    def _release_connection_id(self, conn_id: str) -> None:
        """Remove a connection ID from tracking."""
        with self.connection_lock:
            if conn_id in self.active_connections:
                self.active_connections.remove(conn_id)
                logger.debug(
                    f"Connection {conn_id} released. Active connections: {len(self.active_connections)}"
                )

    async def _list_tools(self) -> list[MCPTool]:
        """Handler for the MCP list_tools operation."""
        tools = []
        for definition in self.worker.get_catalog():
            try:
                # Parse the fully qualified name (toolkit.name) into toolkit and name parts
                parts = definition.fully_qualified_name.split(".")
                if len(parts) == 2:
                    toolkit_name, tool_name = parts
                    # Create a new FullyQualifiedName object with the parsed parts
                    fqn = FullyQualifiedName(tool_name, toolkit_name)
                    tool = self.worker.catalog[fqn]
                    mcp_tool = create_mcp_tool(tool)
                    if mcp_tool:
                        tools.append(mcp_tool)
            except Exception as e:
                logger.warning(f"Error converting tool {definition.name} to MCP format: {e}")
        return tools

    async def _call_tool(  # noqa: C901
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handler for the MCP call_tool operation."""
        try:
            # Parse the fully qualified name (toolkit.name) into toolkit and name parts
            tool = self.worker.catalog.get_tool_by_name(name)

            # get secret keys from requirements
            keys = []
            if tool.definition.requirements and tool.definition.requirements.secrets:
                for secret in tool.definition.requirements.secrets:
                    keys.append(secret.key)

            # get secret values from environment
            secrets = {key: os.environ.get(key) for key in keys if os.environ.get(key) is not None}
            tool_context = ToolContext()
            for key, value in secrets.items():
                if value is not None:
                    tool_context.set_secret(key, value)

            # Check if the tool is authorized to be called
            if tool.definition.requirements and tool.definition.requirements.authorization:
                try:
                    authorization_response = await self._check_authorization(tool)
                    if authorization_response.status != "completed":
                        return [{"type": "text", "text": f"{authorization_response.url}"}]
                    else:
                        tool_context.authorization = ToolAuthorizationContext(
                            token=authorization_response.context.token,
                            user_info=authorization_response.context.user_info
                            if authorization_response.context.user_info
                            else {},
                        )
                except Exception as e:
                    logger.error(
                        f"Error authorizing tool {tool.definition.name}: {e}", exc_info=True
                    )
                    raise

            logger.debug(f"secrets: {secrets}")
            logger.debug(f"Calling tool {name} with arguments: {arguments}")
            logger.debug(f"Tool context: {tool_context.model_dump_json()}")

            # Execute the tool
            result = await self.executor.run(
                tool.tool,
                tool.definition,
                tool.input_model,
                tool.output_model,
                context=tool_context,
                **arguments,
            )

            # Convert the result to MCP content format
            if result.value is not None:
                return convert_to_mcp_content(result.value)
            elif result.error is not None:
                error_message = result.error.message
                developer_message = result.error.developer_message or ""
                traceback = result.error.traceback_info or ""
                logger.error(f"Error calling tool {name}: {error_message}")
                if developer_message or traceback:
                    logger.debug(f"Developer details: {developer_message}\n{traceback}")
                return [{"type": "text", "text": f"Error calling tool {name}: {error_message}"}]
            else:
                logger.error(f"Error calling tool {name}: Unexpected result format - {result}")
                return [
                    {"type": "text", "text": f"Error calling tool {name}: Unexpected result format"}
                ]
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=True)
            return [{"type": "text", "text": f"Error calling tool {name}: {e!s}"}]

    def _get_auth_requirement(self, tool: MaterializedTool) -> AuthRequirement:
        auth_requirement = None
        if tool.definition.requirements and tool.definition.requirements.authorization:
            requirement = tool.definition.requirements.authorization
            if requirement.oauth2:
                auth_requirement = AuthRequirement(
                    provider_id=requirement.provider_id,
                    provider_type=requirement.provider_type,
                    oauth2=AuthRequirementOauth2(
                        scopes=requirement.oauth2.scopes,
                    ),
                )
            else:
                auth_requirement = AuthRequirement(
                    provider_id=requirement.provider_id,
                    provider_type=requirement.provider_type,
                )
        return auth_requirement

    async def _check_authorization(self, tool: MaterializedTool) -> AuthorizationResponse:
        """Check if the tool is authorized to be called."""
        arcade_client = AsyncArcade(api_key=config.api.key)
        try:
            user_id = config.user.email if config.user.email else self._get_connection_id()
            authorization_response = await arcade_client.auth.authorize(
                auth_requirement=self._get_auth_requirement(tool),
                user_id=user_id,
            )
            logger.debug(f"Authorization response: {authorization_response}")

        except Exception as e:
            logger.exception(f"Error authorizing tool {tool.definition.name}: {e}")  # noqa: TRY401
            raise
        return authorization_response

    async def _handle_sse(self, request: Any) -> None:  # noqa: C901
        """Handle SSE connection."""
        # Generate a connection ID for tracking
        connection_id = self._get_connection_id()
        if not connection_id:
            # Too many connections, reject this one
            return

        try:
            # Create initialization options before starting the connection
            init_options = self.mcp_server.create_initialization_options()

            logger.debug(f"Connection {connection_id} attempting to establish SSE connection")

            # Connect to SSE and get the streams
            async with self.sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
            ) as streams:
                if not streams or len(streams) != 2:
                    logger.error(f"Invalid SSE stream connection: {streams}")
                    self._release_connection_id(connection_id)
                    return

                # Log stream types for debugging
                logger.debug(
                    f"Connection {connection_id} stream types: "
                    f"[0]={type(streams[0]).__name__}, [1]={type(streams[1]).__name__}"
                )

                # Run the MCP server with the streams
                try:
                    logger.debug(f"Starting MCP server for connection {connection_id}")

                    # We'll try up to 3 times if we get the initialization timing error
                    retry_count = 0
                    max_retries = 3
                    while retry_count < max_retries:
                        try:
                            await self.mcp_server.run(
                                streams[0],
                                streams[1],
                                init_options,
                            )
                            # If we get here, it completed successfully
                            logger.debug(
                                f"MCP server for connection {connection_id} completed normally"
                            )
                            break
                        except RuntimeError as e:
                            if (
                                "before initialization was complete" in str(e)
                                and retry_count < max_retries - 1
                            ):
                                # Wait a short time and retry
                                retry_count += 1
                                logger.warning(
                                    f"MCP initialization timing error for connection {connection_id} "
                                    f"(retry {retry_count}/{max_retries}): {e}"
                                )
                                await asyncio.sleep(0.5)  # Short delay before retry
                            else:
                                # Either not an initialization error or last retry
                                raise

                except RuntimeError as e:
                    if "initialization was complete" in str(e):
                        logger.error(
                            f"MCP initialization error for connection {connection_id}: {e}",
                            exc_info=True,
                        )
                    else:
                        logger.error(
                            f"MCP runtime error for connection {connection_id}: {e}", exc_info=True
                        )
                except TypeError as e:
                    logger.error(
                        f"Type error in SSE connection {connection_id}: {e}", exc_info=True
                    )
                except Exception as e:
                    logger.error(f"Error in SSE connection {connection_id}: {e}", exc_info=True)
        except TypeError as e:
            logger.error(f"Type error in SSE connection setup {connection_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error in SSE connection setup {connection_id}: {e}", exc_info=True)
        finally:
            # Always release the connection ID
            self._release_connection_id(connection_id)
            logger.debug(f"Connection {connection_id} cleaned up")

    async def __call__(self, request: RequestData) -> dict[str, Any]:
        """Handle a request (required by WorkerComponent)."""
        # This component doesn't handle regular HTTP requests
        with self.connection_lock:
            active_count = len(self.active_connections)

        return {
            "status": "mcp_active",
            "endpoint": f"/mcp{self.sse_path}",
            "server_name": self.server_name,
            "active_connections": active_count,
            "max_connections": self.max_connections,
        }


def create_mcp_sse_component(worker: Worker, app: FastAPI, **config) -> WorkerComponent | None:
    """Create an MCP SSE component.

    Args:
        worker: The worker to create the component for
        app: The FastAPI app to mount the SSE endpoints to
        **config: Additional configuration options
            max_connections: Maximum number of simultaneous SSE connections
            max_worker_threads: Maximum number of worker threads

    Returns:
        An MCP SSE component if MCP is available, otherwise None
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP is not available. MCP SSE component will not be created.")
        return None

    try:
        return MCPSSEComponent(worker, app, **config)
    except Exception as e:
        logger.exception(f"Error creating MCP SSE component: {e}")  # noqa: TRY401
        return None
