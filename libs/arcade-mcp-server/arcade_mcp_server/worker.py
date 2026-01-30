"""
Arcade MCP Server (Integrated Worker + MCP HTTP)

Creates a FastAPI application that exposes both Arcade Worker endpoints and
MCP Server endpoints over HTTP/SSE. MCP is always enabled in this integrated mode.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from types import FrameType
from typing import Any

import uvicorn
from arcade_core.catalog import ToolCatalog
from arcade_core.discovery import discover_tools
from arcade_core.toolkit import ToolkitLoadError
from arcade_serve.fastapi import FastAPIWorker, TaskTrackerMiddleware
from arcade_serve.fastapi.telemetry import OTELHandler
from fastapi import FastAPI
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp_server.__main__ import setup_logging
from arcade_mcp_server.fastapi.auth_routes import create_auth_router
from arcade_mcp_server.fastapi.middleware import AddTrailingSlashToPathMiddleware
from arcade_mcp_server.resource_server.base import ResourceServerValidator
from arcade_mcp_server.resource_server.middleware import ResourceServerMiddleware
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager


class CustomUvicornServer(uvicorn.Server):
    """Uvicorn server with force quit support on double SIGINT/SIGTERM."""

    def __init__(self, config: uvicorn.Config, task_tracker: TaskTrackerMiddleware):
        super().__init__(config)
        self.task_tracker = task_tracker
        self._signal_count = 0

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        """
        Handle termination signals with force quit on second signal.

        First signal (SIGINT/SIGTERM): Graceful shutdown
        Second signal: Force quit with os._exit(1)
        """
        self._signal_count += 1

        if self._signal_count == 1:
            logger.info("Shutting down gracefully. Press Ctrl+C again to force quit.")
            self.should_exit = True
        else:
            logger.warning("Force quit triggered - exiting immediately")
            os._exit(1)

    async def _wait_tasks_to_complete(self) -> None:
        try:
            # Let Uvicorn's normal wait process run
            await super()._wait_tasks_to_complete()
        except asyncio.CancelledError:
            # If we're cancelled (graceful shutdown time expired), then
            # we need to cancel the active HTTP request tasks that we are tracking
            logger.warning("Force quit triggered - cancelling all active requests")
            cancelled = self.task_tracker.cancel_all_tasks()
            logger.info(f"Cancelled {cancelled} active request(s)")
            self.force_exit = True
            os._exit(1)


@asynccontextmanager
async def create_lifespan(
    catalog: ToolCatalog,
    mcp_settings: MCPSettings | None = None,
    **kwargs: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Create lifespan context for the MCP server components.

    Yields a dict with `mcp_server`, and `session_manager`.
    """
    if mcp_settings is None:
        mcp_settings = MCPSettings.from_env()

    try:
        tool_env_keys = sorted(mcp_settings.tool_secrets().keys())
        logger.debug(
            f"Arcade settings: \n\
                ARCADE_ENVIRONMENT={mcp_settings.arcade.environment} \n\
                ARCADE_API_URL={mcp_settings.arcade.api_url}, \n\
                ARCADE_USER_ID={mcp_settings.arcade.user_id}, \n\
                api_key_present - {bool(mcp_settings.arcade.api_key)}"
        )
        logger.debug(f"Tool environment variable names available to tools: {tool_env_keys}")
    except Exception as e:
        logger.debug(f"Unable to log settings/tool env keys: {e}")

    mcp_server = MCPServer(
        catalog,
        settings=mcp_settings,
        **kwargs,
    )

    session_manager = HTTPSessionManager(
        server=mcp_server,
        json_response=True,
    )

    await mcp_server.start()
    async with session_manager.run():
        logger.info("MCP server started and ready for connections")
        yield {
            "mcp_server": mcp_server,
            "session_manager": session_manager,
        }
    await mcp_server.stop()


def create_arcade_mcp(
    catalog: ToolCatalog,
    mcp_settings: MCPSettings | None = None,
    debug: bool = False,
    otel_enable: bool = False,
    resource_server_validator: ResourceServerValidator | None = None,
    **kwargs: Any,
) -> FastAPI:
    """
    Create a FastAPI app exposing MCP HTTP endpoints
    and Arcade Worker endpoints if a secret is provided.

    MCP is always enabled in this integrated application.

    Args:
        catalog: Tool catalog for available tools
        mcp_settings: MCP configuration settings
        debug: Enable debug mode
        otel_enable: Enable OpenTelemetry
        resource_server_validator: Resource Server validator for front-door authentication
        **kwargs: Additional configuration options
    """
    if mcp_settings is None:
        mcp_settings = MCPSettings.from_env()
    secret = mcp_settings.arcade.server_secret

    otel_handler = OTELHandler(
        enable=otel_enable,
        log_level=logging.DEBUG if debug else logging.INFO,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            logger.debug(f"Server lifespan startup. OTEL enabled: {otel_enable}")
            async with create_lifespan(catalog, mcp_settings, **kwargs) as components:
                app.state.mcp_server = components["mcp_server"]
                app.state.session_manager = components["session_manager"]
                yield
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.debug("Server lifespan cancelled.")
            raise
        finally:
            logger.debug(f"Server lifespan shutdown. OTEL enabled: {otel_enable}")
            if otel_enable and otel_handler:
                otel_handler.shutdown()
            await logger.complete()
            logger.debug("Server lifespan shutdown complete.")

    # Use settings for FastAPI app metadata
    app = FastAPI(
        title=(mcp_settings.server.title or mcp_settings.server.name),
        description=(mcp_settings.server.instructions or ""),
        version=mcp_settings.server.version,
        docs_url="/docs" if not mcp_settings.arcade.auth_disabled else None,
        redoc_url="/redoc" if not mcp_settings.arcade.auth_disabled else None,
        lifespan=lifespan,
    )
    otel_handler.instrument_app(app)

    task_tracker = TaskTrackerMiddleware(app)
    app.state.task_tracker = task_tracker

    # Since this middleware tracks all HTTP requests, it must be added first
    @app.middleware("http")
    async def track_tasks_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        return await task_tracker.dispatch(request, call_next)

    app.add_middleware(AddTrailingSlashToPathMiddleware)

    # Add OAuth discovery endpoint if auth is enabled
    if resource_server_validator and resource_server_validator.supports_oauth_discovery():
        canonical_url = getattr(resource_server_validator, "canonical_url", None)
        if not canonical_url:
            raise ValueError(
                "canonical_url must be set via parameter or "
                "MCP_RESOURCE_SERVER_CANONICAL_URL environment variable"
            )

        auth_router = create_auth_router(resource_server_validator, canonical_url)
        app.include_router(auth_router)

    # Worker endpoints
    if secret is not None:
        worker = FastAPIWorker(
            app=app,
            secret=secret,
            disable_auth=mcp_settings.arcade.auth_disabled,
            otel_meter=otel_handler.get_meter(),
        )
        worker.catalog = catalog
        logger.info("Worker routes enabled at /worker/* (ARCADE_WORKER_SECRET is set)")

    class _MCPASGIProxy:
        def __init__(self, parent_app: FastAPI):
            self._app = parent_app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            session_manager = getattr(self._app.state, "session_manager", None)
            if session_manager is None:
                resp = Response("MCP server not initialized", status_code=503)
                await resp(scope, receive, send)
                return
            await session_manager.handle_request(scope, receive, send)

    # Create MCP proxy and wrap with auth middleware if enabled
    mcp_proxy: Any = _MCPASGIProxy(app)
    if resource_server_validator:
        # Get canonical_url from validator if it supports OAuth discovery
        canonical_url = None
        if resource_server_validator.supports_oauth_discovery():
            canonical_url = getattr(resource_server_validator, "canonical_url", None)
            if not canonical_url:
                raise ValueError(
                    "canonical_url must be set via parameter or "
                    "MCP_RESOURCE_SERVER_CANONICAL_URL environment variable"
                )

        mcp_proxy = ResourceServerMiddleware(mcp_proxy, resource_server_validator, canonical_url)

    # Mount the ASGI proxy to handle all /mcp requests
    app.mount("/mcp", mcp_proxy, name="mcp-proxy")

    # Customize OpenAPI to include MCP documentation
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        # Get the default OpenAPI schema
        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Add MCP routes to the schema
        from arcade_mcp_server.fastapi.routes import (
            MCPError,
            MCPRequest,
            MCPResponse,
            get_openapi_routes,
        )

        # Add MCP schemas
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}

        # Add schema definitions
        openapi_schema["components"]["schemas"]["MCPRequest"] = MCPRequest.model_json_schema()
        openapi_schema["components"]["schemas"]["MCPResponse"] = MCPResponse.model_json_schema()
        openapi_schema["components"]["schemas"]["MCPError"] = MCPError.model_json_schema()

        # Add MCP paths
        if "paths" not in openapi_schema:
            openapi_schema["paths"] = {}

        for route_def in get_openapi_routes():
            path = route_def["path"]
            openapi_schema["paths"][path] = {k: v for k, v in route_def.items() if k != "path"}

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


def create_arcade_mcp_factory() -> FastAPI:
    """
    App factory for uvicorn reload support.

    This function is called by uvicorn when using reload mode with an import string.
    It rediscovers the catalog and reads configuration from environment variables.
    """
    # Configure logging first, before any other imports that might trigger logging.
    # This is critical for worker subprocesses (workers > 1) where main() is not called.
    debug = os.environ.get("ARCADE_MCP_DEBUG", "false").lower() == "true"
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level, stdio_mode=False)
    # Read configuration from the remaining env vars that were set before running the server
    otel_enable = os.environ.get("ARCADE_MCP_OTEL_ENABLE", "false").lower() == "true"
    tool_package = os.environ.get("ARCADE_MCP_TOOL_PACKAGE")
    discover_installed = os.environ.get("ARCADE_MCP_DISCOVER_INSTALLED", "false").lower() == "true"
    show_packages = os.environ.get("ARCADE_MCP_SHOW_PACKAGES", "false").lower() == "true"
    server_name = os.environ.get("ARCADE_MCP_SERVER_NAME")
    server_version = os.environ.get("ARCADE_MCP_SERVER_VERSION")
    server_title = os.environ.get("ARCADE_MCP_SERVER_TITLE")
    server_instructions = os.environ.get("ARCADE_MCP_SERVER_INSTRUCTIONS")

    # Rediscover tools since there have been changes
    try:
        catalog = discover_tools(
            tool_package=tool_package,
            show_packages=show_packages,
            discover_installed=discover_installed,
            server_name=server_name,
            server_version=server_version,
        )
    except ToolkitLoadError as exc:
        logger.error(str(exc))
        raise RuntimeError(f"Failed to discover tools: {exc}") from exc

    total_tools = len(catalog)
    if total_tools == 0:
        logger.error("No tools found. Create Python files with @tool decorated functions.")
        raise RuntimeError("No tools found")

    logger.info(f"Total tools loaded: {total_tools}")
    if otel_enable:
        logger.info("OpenTelemetry is enabled")

    # Build settings with server metadata from env vars
    from arcade_mcp_server.settings import ServerSettings

    mcp_settings = MCPSettings.from_env()
    if server_name or server_version or server_title or server_instructions:
        # Override server settings if any were provided via env vars
        mcp_settings.server = ServerSettings(
            name=server_name or mcp_settings.server.name,
            version=server_version or mcp_settings.server.version,
            title=server_title or mcp_settings.server.title,
            instructions=server_instructions or mcp_settings.server.instructions,
        )

    return create_arcade_mcp(
        catalog=catalog,
        mcp_settings=mcp_settings,
        debug=debug,
        otel_enable=otel_enable,
    )


async def serve_with_force_quit(
    app: FastAPI,
    host: str,
    port: int,
    log_level: str,
) -> None:
    """Serve the FastAPI app with force quit capability."""
    timeout_graceful_shutdown = int(
        os.environ.get("ARCADE_UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN", "15")
    )

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level,
        lifespan="on",
        timeout_graceful_shutdown=timeout_graceful_shutdown,
    )

    task_tracker = app.state.task_tracker
    server = CustomUvicornServer(config, task_tracker)

    await server.serve()


def run_arcade_mcp(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int = 1,
    debug: bool = False,
    otel_enable: bool = False,
    tool_package: str | None = None,
    discover_installed: bool = False,
    show_packages: bool = False,
    mcp_settings: MCPSettings | None = None,
    **kwargs: Any,
) -> None:
    """
    Run the integrated Arcade MCP server with uvicorn.

    This is used for module execution (`arcade mcp` and `python -m arcade_mcp_server`) only.
    MCPApp has its own reload mechanism.

    Args:
        workers: Number of uvicorn worker processes. When workers > 1, force-quit
            capability is disabled (standard uvicorn signal handling is used).
            Cannot be combined with reload=True.

    Raises:
        ValueError: If both reload=True and workers > 1 are specified, as uvicorn
            does not support multiple workers in reload mode.
    """
    if reload and workers > 1:
        raise ValueError(
            "Cannot use reload=True with workers > 1. "
            "Uvicorn does not support multiple workers in reload mode."
        )

    log_level = "debug" if debug else "info"

    # Set env vars for the app factory to read
    os.environ["ARCADE_MCP_DEBUG"] = str(debug)
    os.environ["ARCADE_MCP_OTEL_ENABLE"] = str(otel_enable)
    if tool_package:
        os.environ["ARCADE_MCP_TOOL_PACKAGE"] = tool_package
    os.environ["ARCADE_MCP_DISCOVER_INSTALLED"] = str(discover_installed)
    os.environ["ARCADE_MCP_SHOW_PACKAGES"] = str(show_packages)

    # Handle server name/version from mcp_settings or kwargs
    server_name = kwargs.get("name")
    server_version = kwargs.get("version")
    if mcp_settings:
        os.environ["ARCADE_MCP_SERVER_NAME"] = mcp_settings.server.name
        os.environ["ARCADE_MCP_SERVER_VERSION"] = mcp_settings.server.version
        if mcp_settings.server.title:
            os.environ["ARCADE_MCP_SERVER_TITLE"] = mcp_settings.server.title
        if mcp_settings.server.instructions:
            os.environ["ARCADE_MCP_SERVER_INSTRUCTIONS"] = mcp_settings.server.instructions
    else:
        if server_name:
            os.environ["ARCADE_MCP_SERVER_NAME"] = server_name
        if server_version:
            os.environ["ARCADE_MCP_SERVER_VERSION"] = server_version

    app_import_string = "arcade_mcp_server.worker:create_arcade_mcp_factory"

    if reload or workers > 1:
        # Reload mode and multi-worker mode (mutually exclusive, validated above)
        # use uvicorn.run() which bypasses serve_with_force_quit(). This means the
        # server will not be able to force quit when there are active tool executions
        # or active connections with MCP clients. For reload mode, prefer MCPApp.run().
        uvicorn.run(
            app_import_string,
            factory=True,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            lifespan="on",
            workers=workers,
        )
    else:
        # Single-worker production mode uses serve_with_force_quit() for graceful
        # shutdown with force-quit capability on second SIGINT/SIGTERM
        app = create_arcade_mcp_factory()
        asyncio.run(
            serve_with_force_quit(
                app=app,
                host=host,
                port=port,
                log_level=log_level,
            )
        )
