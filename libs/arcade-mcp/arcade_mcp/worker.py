"""
Arcade MCP Server (Integrated Worker + MCP HTTP)

Creates a FastAPI application that exposes both Arcade Worker endpoints and
MCP Server endpoints over HTTP/SSE. MCP is always enabled in this integrated mode.
"""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from arcade_core.catalog import ToolCatalog
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI
from loguru import logger
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp.server import MCPServer
from arcade_mcp.settings import MCPSettings
from arcade_mcp.transports.http_session_manager import HTTPSessionManager


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

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with create_lifespan(catalog, mcp_settings, **kwargs) as components:
            app.state.mcp_server = components["mcp_server"]
            app.state.session_manager = components["session_manager"]
            yield

    app = FastAPI(
        title=(mcp_settings.server.title or mcp_settings.server.name),
        description=(mcp_settings.server.instructions or ""),
        version=mcp_settings.server.version,
        docs_url="/docs" if not mcp_settings.arcade.auth_disabled else None,
        redoc_url="/redoc" if not mcp_settings.arcade.auth_disabled else None,
        lifespan=lifespan,
        **kwargs,
    )

    # Worker endpoints
    worker = FastAPIWorker(
        app=app,
        secret=secret,
        disable_auth=mcp_settings.arcade.auth_disabled,
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
    def custom_openapi():
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
        from arcade_mcp.fastapi.routes import MCPError, MCPRequest, MCPResponse, get_openapi_routes

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

    app.openapi = custom_openapi

    return app


def run_arcade_mcp(
    catalog: ToolCatalog,
    host: str = "127.0.0.1",
    port: int = 7777,
    reload: bool = False,
    debug: bool = False,
    **kwargs: Any,
) -> None:
    """
    Run the integrated Arcade MCP server with uvicorn.
    """

    app = create_arcade_mcp(
        catalog=catalog,
        debug=debug,
        **kwargs,
    )

    log_level = "debug" if debug else "info"

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
        lifespan="on",
    )
