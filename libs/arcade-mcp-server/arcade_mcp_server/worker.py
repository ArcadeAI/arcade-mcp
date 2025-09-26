"""
Arcade MCP Server (Integrated Worker + MCP HTTP)

Creates a FastAPI application that exposes both Arcade Worker endpoints and
MCP Server endpoints over HTTP/SSE. MCP is always enabled in this integrated mode.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from arcade_core.catalog import ToolCatalog
from arcade_serve.fastapi.telemetry import OTELHandler
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI
from loguru import logger
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp_server.fastapi.middleware import AddTrailingSlashToPathMiddleware
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager


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
    **kwargs: Any,
) -> FastAPI:
    """
    Create a FastAPI app exposing Arcade Worker and MCP HTTP endpoints.

    MCP is always enabled in this integrated application.
    """
    if mcp_settings is None:
        mcp_settings = MCPSettings.from_env()
    secret = mcp_settings.arcade.server_secret
    if secret is None:
        secret = "dev"  # noqa: S105

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

    app = FastAPI(
        title=(mcp_settings.server.title or mcp_settings.server.name),
        description=(mcp_settings.server.instructions or ""),
        version=mcp_settings.server.version,
        docs_url="/docs" if not mcp_settings.arcade.auth_disabled else None,
        redoc_url="/redoc" if not mcp_settings.arcade.auth_disabled else None,
        lifespan=lifespan,
        **kwargs,
    )
    otel_handler.instrument_app(app)
    app.add_middleware(AddTrailingSlashToPathMiddleware)

    # Worker endpoints
    worker = FastAPIWorker(
        app=app,
        secret=secret,
        disable_auth=mcp_settings.arcade.auth_disabled,
        otel_meter=otel_handler.get_meter(),
    )
    worker.catalog = catalog

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

    # Mount the actual ASGI proxy to handle all /mcp requests
    app.mount("/mcp", _MCPASGIProxy(app), name="mcp-proxy")

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
    import os

    from arcade_core.discovery import discover_tools
    from arcade_core.toolkit import ToolkitLoadError

    # Read configuration from env vars that were set before running the server
    debug = os.environ.get("ARCADE_MCP_DEBUG", "false").lower() == "true"
    otel_enable = os.environ.get("ARCADE_MCP_OTEL_ENABLE", "false").lower() == "true"
    tool_package = os.environ.get("ARCADE_MCP_TOOL_PACKAGE")
    discover_installed = os.environ.get("ARCADE_MCP_DISCOVER_INSTALLED", "false").lower() == "true"
    show_packages = os.environ.get("ARCADE_MCP_SHOW_PACKAGES", "false").lower() == "true"
    server_name = os.environ.get("ARCADE_MCP_SERVER_NAME")
    server_version = os.environ.get("ARCADE_MCP_SERVER_VERSION")

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

    # Build kwargs for server creation
    kwargs = {}
    if server_name:
        kwargs["name"] = server_name
    if server_version:
        kwargs["version"] = server_version

    return create_arcade_mcp(
        catalog=catalog,
        mcp_settings=None,
        debug=debug,
        otel_enable=otel_enable,
        **kwargs,
    )


def run_arcade_mcp(
    catalog: ToolCatalog,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    debug: bool = False,
    otel_enable: bool = False,
    tool_package: str | None = None,
    discover_installed: bool = False,
    show_packages: bool = False,
    **kwargs: Any,
) -> None:
    """
    Run the integrated Arcade MCP server with uvicorn.
    """
    import os

    log_level = "debug" if debug else "info"

    if reload:
        # Set env vars for the app factory to read later
        os.environ["ARCADE_MCP_DEBUG"] = str(debug)
        os.environ["ARCADE_MCP_OTEL_ENABLE"] = str(otel_enable)
        if tool_package:
            os.environ["ARCADE_MCP_TOOL_PACKAGE"] = tool_package
        os.environ["ARCADE_MCP_DISCOVER_INSTALLED"] = str(discover_installed)
        os.environ["ARCADE_MCP_SHOW_PACKAGES"] = str(show_packages)
        if kwargs.get("name"):
            os.environ["ARCADE_MCP_SERVER_NAME"] = kwargs["name"]
        if kwargs.get("version"):
            os.environ["ARCADE_MCP_SERVER_VERSION"] = kwargs["version"]

        # import string is required for reload mode
        app_import_string = "arcade_mcp_server.worker:create_arcade_mcp_factory"

        uvicorn.run(
            app_import_string,
            factory=True,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            lifespan="on",
        )
    else:
        app = create_arcade_mcp(
            catalog=catalog,
            debug=debug,
            otel_enable=otel_enable,
            **kwargs,
        )

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            lifespan="on",
        )
