"""
MCPApp - A FastAPI-like interface for MCP servers.

Provides a clean, minimal API for building MCP servers with lazy initialization.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Literal, ParamSpec, TypeVar

import uvicorn
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolDefinitionError
from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.error_adapters import ErrorAdapter
from arcade_tdk.tool import tool as tool_decorator
from dotenv import load_dotenv
from loguru import logger
from watchfiles import watch

from arcade_mcp_server.exceptions import ServerError
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings, ServerSettings
from arcade_mcp_server.types import Prompt, PromptMessage, Resource
from arcade_mcp_server.worker import create_arcade_mcp

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
        version: str = "0.1.0",
        title: str | None = None,
        instructions: str | None = None,
        log_level: str = "INFO",
        transport: TransportType = "stdio",
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
            transport: Transport type ("stdio")
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

        self._mcp_settings = MCPSettings(
            server=ServerSettings(
                name=self.name,
                version=self.version,
                title=self.title,
                instructions=self.instructions,
            )
        )

        self._load_env()
        if not logger._core.handlers:  # type: ignore[attr-defined]
            self._setup_logging(transport == "stdio")

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

    def _setup_logging(self, stdio_mode: bool = False) -> None:
        logger.remove()

        # In stdio mode, use stderr (stdout is reserved for JSON-RPC)
        sink = sys.stderr if stdio_mode else sys.stdout

        if self.log_level == "DEBUG":
            format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{line}</cyan> | <level>{message}</level>"
        else:
            format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        logger.add(
            sink,
            format=format_str,
            level=self.log_level,
            colorize=(not stdio_mode),
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
        transport: TransportType = "stdio",
        **kwargs: Any,
    ) -> None:
        if len(self._catalog) == 0:
            logger.error("No tools added to the server. Use @app.tool decorator or app.add_tool().")
            sys.exit(1)

        host, port, transport, reload = MCPApp._get_configuration_overrides(
            host, port, transport, reload
        )

        # Since the transport could have changed since __init__, we need to setup logging again
        self._setup_logging(transport == "stdio")

        if os.getenv("ARCADE_MCP_CHILD_PROCESS") == "1":
            # parent watcher has already been setup
            reload = False

        logger.info(f"Starting {self.name} v{self.version} with {len(self._catalog)} tools")

        if transport in ["http", "streamable-http", "streamable"]:
            if reload:
                self._run_with_reload(host, port)
            else:
                self._create_and_run_server(host, port)
        elif transport == "stdio":
            from arcade_mcp_server.__main__ import run_stdio_server

            asyncio.run(
                run_stdio_server(
                    catalog=self._catalog,
                    settings=self._mcp_settings,
                    **self.server_kwargs,
                )
            )
        else:
            raise ServerError(f"Invalid transport: {transport}")

    def _run_with_reload(self, host: str, port: int) -> None:
        """
        Run with file watching for auto-reload.

        This method runs as the parent process that watches for file changes
        and spawns/restarts child processes to run the actual server.
        """
        env_file_path = Path.cwd() / ".env"

        def start_server_process() -> subprocess.Popen:
            """Start a child process running the server."""
            env = os.environ.copy()
            env["ARCADE_MCP_CHILD_PROCESS"] = "1"

            return subprocess.Popen(
                [sys.executable, *sys.argv],
                env=env,
            )

        def shutdown_server_process(process: subprocess.Popen, reason: str = "reload") -> None:
            """Shutdown server process gracefully with fallback to force kill."""
            logger.info(f"Shutting down server for {reason}...")
            process.terminate()

            try:
                process.wait(timeout=5)
                logger.info("Server shut down gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Server did not shut down within 5 seconds (likely due to active client connections). "
                    "Force killing server process..."
                )
                process.kill()
                process.wait()
                logger.info("Server force killed")

        logger.info("Starting file watcher for auto-reload")
        process = start_server_process()

        try:

            def watch_filter(change: Any, path: str) -> bool:
                return path.endswith(".py") or (Path(path) == env_file_path)

            for changes in watch(".", watch_filter=watch_filter):
                logger.info(f"Detected changes in {len(changes)} file(s), restarting server...")
                shutdown_server_process(process, reason="reload")
                process = start_server_process()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            shutdown_server_process(process, reason="shutdown")
            logger.info("File watcher stopped")

    def _create_and_run_server(self, host: str, port: int) -> None:
        """
        Create and run the server directly without reload.

        This is used when reload=False or when running as a child process.
        """
        debug = self.log_level == "DEBUG"
        log_level = "debug" if debug else "info"

        app = create_arcade_mcp(
            catalog=self._catalog,
            mcp_settings=self._mcp_settings,
            debug=debug,
            **self.server_kwargs,
        )

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            reload=False,  # MCPApp handles its own reload via parent/child process pattern
            lifespan="on",
        )

    @staticmethod
    def _get_configuration_overrides(
        host: str, port: int, transport: TransportType, reload: bool
    ) -> tuple[str, int, TransportType, bool]:
        """Get configuration overrides from environment variables."""
        if envvar_transport := os.getenv("ARCADE_SERVER_TRANSPORT"):
            transport = envvar_transport
            logger.debug(
                f"Using '{transport}' as transport from ARCADE_SERVER_TRANSPORT environment variable"
            )

        # host and port are only relevant for HTTP Streamable transport
        if transport in ["http", "streamable-http", "streamable"]:
            if envvar_host := os.getenv("ARCADE_SERVER_HOST"):
                host = envvar_host
                logger.debug(f"Using '{host}' as host from ARCADE_SERVER_HOST environment variable")

            if envvar_port := os.getenv("ARCADE_SERVER_PORT"):
                try:
                    port = int(envvar_port)
                except ValueError:
                    logger.warning(
                        f"Invalid port: '{envvar_port}' from ARCADE_SERVER_PORT environment variable. Using default port {port}"
                    )
                else:
                    logger.debug(
                        f"Using '{port}' as port from ARCADE_SERVER_PORT environment variable"
                    )

            if envvar_reload := os.getenv("ARCADE_SERVER_RELOAD"):
                if envvar_reload.lower() not in ["0", "1"]:
                    logger.warning(
                        f"Invalid reload: '{envvar_reload}' from ARCADE_SERVER_RELOAD environment variable. Using default reload {reload}"
                    )
                else:
                    reload = bool(int(envvar_reload))
                    logger.debug(
                        f"Using '{reload}' as reload from ARCADE_SERVER_RELOAD environment variable"
                    )

        return host, port, transport, reload


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
