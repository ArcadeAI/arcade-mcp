from fastapi import FastAPI

from arcade.actor.common.serializers import MsgSpecJSONResponse
from arcade.actor.core.conf import settings
from arcade.actor.core.generate import generate_endpoint
from arcade.actor.routes import v1
from arcade.tool.catalog import ToolCatalog


def register_app() -> FastAPI:
    # FastAPI
    app = FastAPI(
        title=settings.TITLE,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOCS_URL,
        openapi_url=settings.OPENAPI_URL,
        default_response_class=MsgSpecJSONResponse,
    )

    register_static_file(app)

    register_middleware(app)

    register_router(app)

    generate_tool_routes(app)

    return app


def register_static_file(app: FastAPI) -> None:
    """
    Register static files
    """

    if settings.STATIC_FILES:
        import os

        from fastapi.staticfiles import StaticFiles

        if not os.path.exists("./static"):
            os.mkdir("./static")
        app.mount("/static", StaticFiles(directory="static"), name="static")


def register_middleware(app: FastAPI) -> None:
    """
    Register middleware for the FastAPI app
    """
    # Gzip: Always at the top
    if settings.MIDDLEWARE_GZIP:
        from fastapi.middleware.gzip import GZipMiddleware

        app.add_middleware(GZipMiddleware)

    # CORS: Always at the end
    if settings.MIDDLEWARE_CORS:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def register_router(app: FastAPI) -> None:
    """
    Register routers for the FastAPI app
    """
    dependencies = None

    # API
    app.include_router(v1, dependencies=dependencies)


def generate_tool_routes(app: FastAPI) -> None:
    """
    Generate tool routes for each tool in the catalog
    Add the routes to the FastAPI app and the tool
    definitions to the catalog
    """
    catalog = ToolCatalog()
    router = generate_endpoint(list(catalog.tools.values()))
    app.include_router(router)
    app.state.catalog = catalog
