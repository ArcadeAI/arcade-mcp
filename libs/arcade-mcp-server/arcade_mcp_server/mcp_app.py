"""
MCPApp - A FastAPI-like interface for MCP servers.

Provides a clean, minimal API for building MCP servers with lazy initialization.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Literal, ParamSpec, TypeVar

from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolDefinitionError
from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.error_adapters import ErrorAdapter
from arcade_tdk.tool import tool as tool_decorator
from dotenv import load_dotenv
from loguru import logger

from arcade_mcp_server.exceptions import ServerError
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.types import Prompt, PromptMessage, Resource
from arcade_mcp_server.worker import run_arcade_mcp

P = ParamSpec("P")
T = TypeVar("T")

TransportType = Literal["http", "stdio"]


class MCPApp:
    """
    A FastAPI-like interface for building MCP servers.

    The app collects tools and configuration, then lazily creates the server
    and transport when run() is called.

    Example:
        ```python
        from arcade_mcp_server import MCPApp

        app = MCPApp(name="my_server", version="1.0.0")

        @app.tool
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        # Runtime CRUD once you have a server bound to the app:
        # app.server = mcp_server
        # await app.tools.add(materialized_tool)
        # await app.prompts.add(prompt, handler)
        # await app.resources.add(resource)

        app.run(host="127.0.0.1", port=8000)
        ```
    """

    def __init__(
        self,
        name: str = "ArcadeMCP",
        version: str = "1.0.0dev",
        title: str | None = None,
        instructions: str | None = None,
        log_level: str = "INFO",
        transport: TransportType = "http",
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize the MCP app.

        Args:
            name: Server name
            version: Server version
            title: Server title for display
            instructions: Server instructions
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            transport: Transport type ("http")
            host: Host for transport
            port: Port for transport
            reload: Enable auto-reload for development
            **kwargs: Additional server configuration
        """
        self.name = name
        self.version = version
        self.title = title or name
        self.instructions = instructions
        self.log_level = log_level
        self.server_kwargs = kwargs
        self.transport = transport
        self.host = host
        self.port = port
        self.reload = reload

        # Tool collection (build-time)
        self._catalog = ToolCatalog()
        self._toolkit_name = name

        # Public handle to the MCPServer (set by caller for runtime ops)
        self.server: MCPServer | None = None

        self._load_env()
        self._setup_logging()

    # Properties (exposed below initializer)
    @property
    def tools(self) -> _ToolsAPI:
        """Runtime and build-time tools API: add/update/remove/list."""
        return _ToolsAPI(self)

    @property
    def prompts(self) -> _PromptsAPI:
        """Runtime prompts API: add/remove/list."""
        return _PromptsAPI(self)

    @property
    def resources(self) -> _ResourcesAPI:
        """Runtime resources API: add/remove/list."""
        return _ResourcesAPI(self)

    def _load_env(self) -> None:
        """Load .env file from the current directory."""
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logger.info(f"Loaded environment from {env_path}")

    def _setup_logging(self) -> None:
        logger.remove()
        if self.log_level == "DEBUG":
            format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{line}</cyan> | <level>{message}</level>"
        else:
            format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        logger.add(
            sys.stdout,
            format=format_str,
            level=self.log_level,
            colorize=True,
            diagnose=(self.log_level == "DEBUG"),
        )

    def add_tool(
        self,
        func: Callable[P, T],
        desc: str | None = None,
        name: str | None = None,
        requires_auth: ToolAuthorization | None = None,
        requires_secrets: list[str] | None = None,
        requires_metadata: list[str] | None = None,
        adapters: list[ErrorAdapter] | None = None,
    ) -> Callable[P, T]:
        """Add a tool for build-time materialization (pre-server)."""
        if not hasattr(func, "__tool_name__"):
            func = tool_decorator(
                func,
                desc=desc,
                name=name,
                requires_auth=requires_auth,
                requires_secrets=requires_secrets,
                requires_metadata=requires_metadata,
                adapters=adapters,
            )
        try:
            self._catalog.add_tool(func, self._toolkit_name)
        except ToolDefinitionError as e:
            raise e.with_context(func.__name__) from e
        logger.debug(f"Added tool: {func.__name__}")
        return func

    def tool(
        self,
        func: Callable[P, T] | None = None,
        desc: str | None = None,
        name: str | None = None,
        requires_auth: ToolAuthorization | None = None,
        requires_secrets: list[str] | None = None,
        requires_metadata: list[str] | None = None,
        adapters: list[ErrorAdapter] | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
        """Decorator for adding tools with optional parameters."""

        def decorator(f: Callable[P, T]) -> Callable[P, T]:
            return self.add_tool(
                f,
                desc=desc,
                name=name,
                requires_auth=requires_auth,
                requires_secrets=requires_secrets,
                requires_metadata=requires_metadata,
                adapters=adapters,
            )

        if func is not None:
            return decorator(func)
        return decorator

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
        transport: TransportType = "http",
        **kwargs: Any,
    ) -> None:
        if len(self._catalog) == 0:
            logger.error("No tools added to the server. Use @app.tool decorator or app.add_tool().")
            sys.exit(1)

        logger.info(f"Starting {self.name} v{self.version} with {len(self._catalog)} tools")

        if transport in ["http", "streamable-http", "streamable"]:
            run_arcade_mcp(
                catalog=self._catalog,
                host=host,
                port=port,
                reload=reload,
                **self.server_kwargs,
            )
        elif transport == "stdio":
            import asyncio

            from arcade_mcp_server.__main__ import run_stdio_server

            asyncio.run(
                run_stdio_server(
                    catalog=self._catalog,
                    port=port,
                    reload=reload,
                    **self.server_kwargs,
                )
            )
        else:
            raise ServerError(f"Invalid transport: {transport}")


class _ToolsAPI:
    """Unified tools API for MCPApp (build-time and runtime)."""

    def __init__(self, app: MCPApp) -> None:
        self._app = app

    async def add(self, tool: MaterializedTool) -> None:
        """Add or update a tool at runtime if server is bound; otherwise queue via app.add_tool decorator."""
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime tools API.")
        await self._app.server.tools.add_tool(tool)

    async def update(self, tool: MaterializedTool) -> None:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime tools API.")
        await self._app.server.tools.update_tool(tool)

    async def remove(self, name: str) -> MaterializedTool:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime tools API.")
        return await self._app.server.tools.remove_tool(name)

    async def list(self) -> list[Any]:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime tools API.")
        return await self._app.server.tools.list_tools()


class _PromptsAPI:
    """Unified prompts API for MCPApp (runtime)."""

    def __init__(self, app: MCPApp) -> None:
        self._app = app

    async def add(
        self, prompt: Prompt, handler: Callable[[dict[str, str]], list[PromptMessage]] | None = None
    ) -> None:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime prompts API.")
        await self._app.server.prompts.add_prompt(prompt, handler)

    async def remove(self, name: str) -> Prompt:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime prompts API.")
        return await self._app.server.prompts.remove_prompt(name)

    async def list(self) -> list[Prompt]:
        if self._app.server is None:
            raise ServerError("No server bound to app. Set app.server to use runtime prompts API.")
        return await self._app.server.prompts.list_prompts()


class _ResourcesAPI:
    """Unified resources API for MCPApp (runtime)."""

    def __init__(self, app: MCPApp) -> None:
        self._app = app

    async def add(self, resource: Resource, handler: Callable[[str], Any] | None = None) -> None:
        if self._app.server is None:
            raise ServerError(
                "No server bound to app. Set app.server to use runtime resources API."
            )
        await self._app.server.resources.add_resource(resource, handler)

    async def remove(self, uri: str) -> Resource:
        if self._app.server is None:
            raise ServerError(
                "No server bound to app. Set app.server to use runtime resources API."
            )
        return await self._app.server.resources.remove_resource(uri)

    async def list(self) -> list[Resource]:
        if self._app.server is None:
            raise ServerError(
                "No server bound to app. Set app.server to use runtime resources API."
            )
        return await self._app.server.resources.list_resources()
