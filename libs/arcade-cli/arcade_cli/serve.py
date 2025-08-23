import asyncio
import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from importlib.metadata import version as get_pkg_version
from pathlib import Path
from typing import Any

import fastapi
import uvicorn

# Watchfiles is used under the hood by Uvicorn's reload feature.
# Importing watchfiles here is an explicit acknowledgement that it needs to be installed
import watchfiles  # noqa: F401
from arcade_core.catalog import ToolCatalog
from arcade_core.telemetry import OTELHandler
from arcade_core.toolkit import Toolkit, get_package_directory
from arcade_serve.core.components import (
    CallToolComponent,
    CatalogComponent,
    HealthCheckComponent,
    LocalContextCallToolComponent,
    WorkerComponent,
)
from arcade_serve.fastapi.sse import SSEComponent
from arcade_serve.fastapi.stream import StreamComponent
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_serve.mcp.stdio import StdioServer
from loguru import logger
from rich.console import Console

from arcade_cli.constants import ARCADE_CONFIG_PATH
from arcade_cli.deployment import Deployment
from arcade_cli.utils import (
    discover_toolkits,
    load_dotenv,
)

console = Console(width=70, color_system="auto")


# App factory for Uvicorn reload
def create_arcade_app() -> fastapi.FastAPI:
    # TODO: Find a better way to pass these configs to factory used for reload
    debug_mode = os.environ.get("ARCADE_DEBUG_MODE", "False").lower() == "true"
    otel_enabled = os.environ.get("ARCADE_OTEL_ENABLE", "False").lower() == "true"
    auth_for_reload = not debug_mode
    deployment_file = os.environ.get("ARCADE_DEPLOYMENT_FILE")

    # Call setup_logging here to ensure Uvicorn worker processes also get Loguru formatting
    # for all standard library loggers.
    # The log_level for Uvicorn itself is set via uvicorn.run(log_level=...),
    # this call primarily aims to capture third-party library logs into Loguru.
    setup_logging(log_level=logging.DEBUG if debug_mode else logging.INFO, mcp_mode=False)

    logger.info(f"Debug: {debug_mode}, OTEL: {otel_enabled}, Auth Disabled: {auth_for_reload}")
    version = get_pkg_version("arcade-ai")

    # Load toolkits and local context
    local_context = None
    if deployment_file:
        toolkits = load_toolkits_from_deployment(Path(deployment_file))
        # Load local context from deployment file
        try:
            deployment = Deployment.from_toml(Path(deployment_file))
            if deployment.worker:
                worker_config = deployment.worker[0].config
                local_context = worker_config.local_context or {}
                # Include auth providers in the context
                if worker_config.local_auth_providers:
                    local_context["local_auth_providers"] = [
                        provider.model_dump() for provider in worker_config.local_auth_providers
                    ]
        except Exception as e:
            logger.warning(f"Could not load local context from deployment: {e}")
    else:
        toolkits = discover_toolkits()

    logger.info("Registered toolkits:")
    for toolkit in toolkits:
        logger.info(
            f"  - {toolkit.name}: {sum(len(tools) for tools in toolkit.tools.values())} tools"
        )

    otel_handler = OTELHandler(
        enable=otel_enabled,
        log_level=logging.DEBUG if debug_mode else logging.INFO,
    )

    custom_lifespan = partial(lifespan, otel_handler=otel_handler, enable_otel=otel_enabled)

    app = fastapi.FastAPI(
        title="Arcade Worker",
        description="A worker for the Arcade platform.",
        version=version,
        docs_url="/docs" if debug_mode else None,
        redoc_url="/redoc" if debug_mode else None,
        openapi_url="/openapi.json" if debug_mode else None,
        lifespan=custom_lifespan,
    )

    disable_auth = not auth_for_reload
    secret = os.getenv("ARCADE_WORKER_SECRET", "dev")
    if secret == "dev" and not os.environ.get("ARCADE_WORKER_SECRET"):  # noqa: S105
        logger.warning("Using default 'dev' for ARCADE_WORKER_SECRET. Set this in production.")

    # Determine which components to use
    components: list[type[WorkerComponent]] = [CatalogComponent, HealthCheckComponent]

    # Use LocalContextCallToolComponent if we have local context, otherwise use standard
    if local_context:
        # We'll need to register this component with the local_context
        # But FastAPIWorker doesn't support passing kwargs to components yet
        # So we'll register it manually after creating the worker
        components.append(CallToolComponent)  # Will replace this below
    else:
        components.append(CallToolComponent)

    worker = FastAPIWorker(
        app=app,
        secret=secret,
        disable_auth=disable_auth,
        otel_meter=otel_handler.get_meter(),
        components=components,
    )

    # If we have local context, replace the CallToolComponent with LocalContextCallToolComponent
    if local_context:
        # Remove the default CallToolComponent
        worker.components = [c for c in worker.components if not isinstance(c, CallToolComponent)]
        # Add LocalContextCallToolComponent with local context
        worker.register_component(LocalContextCallToolComponent, local_context=local_context)

    for tk in toolkits:
        worker.register_toolkit(tk)

    return app


def _run_mcp_stdio(
    toolkits: list[Toolkit],
    *,
    logging_enabled: bool,
    env_file: str | None = None,
    deployment_file: Path | None = None,
) -> None:
    """Launch an MCP stdio server; blocks until it exits."""
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        # Load arcade.env from standard locations
        for candidate in [
            Path(ARCADE_CONFIG_PATH) / "arcade.env",
            Path.cwd() / "arcade.env",
        ]:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break

    # Get local context from deployment file if available
    local_context = None
    if deployment_file:
        try:
            deployment = Deployment.from_toml(deployment_file)
            if deployment.worker:
                worker_config = deployment.worker[0].config
                local_context = worker_config.local_context or {}
                # Include auth providers in the context
                if worker_config.local_auth_providers:
                    local_context["local_auth_providers"] = [
                        provider.model_dump() for provider in worker_config.local_auth_providers
                    ]
        except Exception as e:
            logger.warning(f"Could not load local context from deployment: {e}")

    catalog = ToolCatalog()
    for tk in toolkits:
        catalog.add_toolkit(tk)

    # Create and run the server
    server = StdioServer(catalog, auth_disabled=True, local_context=local_context)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user.")
    except Exception as exc:
        logger.exception("Error while running MCP server: %s", exc)
        raise
    finally:
        logger.info("Shutting down Server")
        logger.complete()
        logger.remove()


def _run_mcp_sse(
    toolkits: list[Toolkit],
    host: str,
    port: int,
    *,
    logging_enabled: bool,
    env_file: str | None = None,
    disable_auth: bool,
    deployment_file: Path | None = None,
) -> None:
    """Launch an MCP SSE server; blocks until it exits."""
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        for candidate in [
            Path(ARCADE_CONFIG_PATH) / "arcade.env",
            Path.cwd() / "arcade.env",
        ]:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break

    # Get local context from deployment file if available
    local_context = None
    if deployment_file:
        try:
            deployment = Deployment.from_toml(deployment_file)
            if deployment.worker and deployment.worker[0].config.local_context:
                local_context = deployment.worker[0].config.local_context
        except Exception as e:
            logger.warning(f"Could not load local context from deployment: {e}")

    app = fastapi.FastAPI(
        title="Arcade Worker (MCP SSE)",
        description="A worker for the Arcade platform running in MCP SSE mode.",
        version=get_pkg_version("arcade-ai"),
    )

    worker = FastAPIWorker(
        app=app,
        disable_auth=disable_auth,
    )

    # Register component with local context
    worker.register_component(SSEComponent, local_context=local_context)

    for tk in toolkits:
        worker.register_toolkit(tk)

    log_level = "debug" if logging_enabled else "info"

    @asynccontextmanager
    async def sse_lifespan(app: fastapi.FastAPI):
        # Components already registered, just manage lifecycle
        for component in worker.components:
            if hasattr(component, "startup"):
                component.startup()
        yield
        for component in worker.components:
            if hasattr(component, "shutdown"):
                await component.shutdown()

    app.router.lifespan_context = sse_lifespan
    uvicorn.run(app, host=host, port=port, log_level=log_level)


def _run_mcp_stream(
    toolkits: list[Toolkit],
    host: str,
    port: int,
    *,
    logging_enabled: bool,
    env_file: str | None = None,
    disable_auth: bool,
    deployment_file: Path | None = None,
) -> None:
    """Launch an MCP HTTPS stream server; blocks until it exits."""
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        for candidate in [
            Path(ARCADE_CONFIG_PATH) / "arcade.env",
            Path.cwd() / "arcade.env",
        ]:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break

    # Get local context from deployment file if available
    local_context = None
    if deployment_file:
        try:
            deployment = Deployment.from_toml(deployment_file)
            if deployment.worker:
                worker_config = deployment.worker[0].config
                local_context = worker_config.local_context or {}
                # Include auth providers in the context
                if worker_config.local_auth_providers:
                    local_context["local_auth_providers"] = [
                        provider.model_dump() for provider in worker_config.local_auth_providers
                    ]
        except Exception as e:
            logger.warning(f"Could not load local context from deployment: {e}")

    app = fastapi.FastAPI(
        title="Arcade Worker (MCP Stream)",
        description="A worker for the Arcade platform running in MCP Stream mode.",
        version=get_pkg_version("arcade-ai"),
    )

    worker = FastAPIWorker(
        app=app,
        disable_auth=disable_auth,
    )

    # Register component with local context
    worker.register_component(StreamComponent, local_context=local_context)

    for tk in toolkits:
        worker.register_toolkit(tk)

    log_level = "debug" if logging_enabled else "info"

    @asynccontextmanager
    async def stream_lifespan(app: fastapi.FastAPI):
        # Components already registered, just manage lifecycle
        for component in worker.components:
            if hasattr(component, "startup"):
                component.startup()
        yield
        for component in worker.components:
            if hasattr(component, "shutdown"):
                await component.shutdown()

    app.router.lifespan_context = stream_lifespan
    uvicorn.run(app, host=host, port=port, log_level=log_level)


def load_toolkits_from_deployment(file: Path) -> list[Toolkit]:
    """Load toolkits from a deployment file."""
    deployment = Deployment.from_toml(file)
    toolkits = []
    for worker in deployment.worker:
        if worker.local_source and worker.local_source.packages:
            for package_path_str in worker.local_source.packages:
                package_path = file.parent / package_path_str
                toolkit = Toolkit.from_directory(package_path)
                toolkits.append(toolkit)
        else:
            # Auto-detect a local toolkit in the same directory as the deployment file
            # when packages are not explicitly specified.
            try:
                candidate_dir = file.parent
                if (candidate_dir / "pyproject.toml").is_file():
                    toolkit = Toolkit.from_directory(candidate_dir)
                    toolkits.append(toolkit)
            except Exception:
                # Best-effort: fall back silently if no local toolkit is present
                pass
    return toolkits


def _run_fastapi_server(
    host: str,
    port: int,
    workers_param: int,
    timeout_keep_alive: int,
    reload: bool,
    toolkits_for_reload_dirs: list[Toolkit] | None,
    debug_flag: bool,
) -> None:
    app_import_string = "arcade_cli.serve:create_arcade_app"
    reload_dirs_str_list: list[str] | None = None

    if reload:
        current_reload_dirs_paths = []
        if toolkits_for_reload_dirs:
            for tk in toolkits_for_reload_dirs:
                try:
                    package_dir_str = get_package_directory(tk.package_name)
                    current_reload_dirs_paths.append(Path(package_dir_str))
                except Exception as e:
                    logger.warning(f"Error getting reload path for toolkit {tk.name}: {e}")

        serve_py_dir_path = Path(__file__).resolve().parent
        current_reload_dirs_paths.append(serve_py_dir_path)

        if current_reload_dirs_paths:
            reload_dirs_str_list = [str(p) for p in current_reload_dirs_paths]
            logger.debug(f"Uvicorn reload_dirs: {reload_dirs_str_list}")

    effective_workers = 1 if reload else workers_param
    log_level_str = logging.getLevelName(logging.DEBUG if debug_flag else logging.INFO).lower()

    logger.debug(
        f"Calling uvicorn.run with app='{app_import_string}', factory=True, host='{host}', port={port}, "
        f"workers={effective_workers}, reload={reload}, log_level='{log_level_str}'"
    )

    uvicorn.run(
        app_import_string,
        factory=True,
        host=host,
        port=port,
        workers=effective_workers,
        log_config=None,
        log_level=log_level_str,
        reload=reload,
        reload_dirs=reload_dirs_str_list,
        lifespan="on",
        timeout_keep_alive=timeout_keep_alive,
    )


class RichInterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: int = logging.INFO, mcp_mode: bool = False) -> None:
    """Loguru and intercepts standard logging."""
    # Set our handler on root
    logging.root.handlers = [RichInterceptHandler()]
    logging.root.setLevel(log_level)

    # For all existing loggers, remove their handlers and make them propagate to root.
    for name in list(logging.root.manager.loggerDict.keys()):
        existing_logger = logging.getLogger(name)
        existing_logger.handlers = []
        existing_logger.propagate = True

    # clear existing loguru handlers to keep worker logging behavior clean
    # and consistent despite toolkit logging changes
    logger.remove()

    # set sink destination based on mode
    # MCP stdio needs to write to stderr to avoid interfering with capture
    sink_destination = sys.stderr if mcp_mode else sys.stdout

    if log_level == logging.DEBUG:
        format_string = "<level>{level}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{file}:{line: <4}</cyan> | <level>{message}</level>"
    else:
        format_string = (
            "<level>{level}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        )

    logger.configure(
        handlers=[
            {
                "sink": sink_destination,
                "colorize": True,
                "level": log_level,
                "format": format_string,
                "enqueue": True,  # non-blocking logging
                "diagnose": False,  # disable detailed logging TODO: make this configurable
            }
        ]
    )


@asynccontextmanager
async def lifespan(
    app: fastapi.FastAPI,
    otel_handler: OTELHandler | None = None,
    enable_otel: bool = False,
) -> AsyncGenerator[None, None]:
    try:
        logger.debug(f"Server lifespan startup. OTEL enabled: {enable_otel}")
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.debug("Server lifespan cancelled.")
        raise
    finally:
        logger.debug(f"Server lifespan shutdown. OTEL enabled: {enable_otel}")
        if enable_otel and otel_handler:
            otel_handler.shutdown()
        await logger.complete()
        logger.remove()
        logger.debug("Server lifespan shutdown complete.")


def serve_default_worker(
    file: Path,
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    enable_otel: bool = False,
    debug: bool = False,
    local: bool = False,
    reload: bool = False,
    sse: bool = False,
    stream: bool = False,
    **kwargs: Any,
) -> None:
    # Initial logging setup for the main `arcade serve` process itself.
    # The Uvicorn worker processes will call setup_logging() again via create_arcade_app().
    setup_logging(log_level=logging.DEBUG if debug else logging.INFO, mcp_mode=local)

    toolkits = load_toolkits_from_deployment(file)

    if local:
        logger.info("MCP mode selected.")
        _run_mcp_stdio(
            toolkits,
            logging_enabled=not debug,
            env_file=kwargs.pop("env_file", None),
            deployment_file=file,
        )
        return

    if sse:
        logger.info("MCP SSE mode selected.")
        _run_mcp_sse(
            toolkits,
            host=host,
            port=port,
            logging_enabled=not debug,
            env_file=kwargs.pop("env_file", None),
            disable_auth=disable_auth,
            deployment_file=file,
        )
        return

    if stream:
        logger.info("MCP Stream mode selected.")
        _run_mcp_stream(
            toolkits,
            host=host,
            port=port,
            logging_enabled=not debug,
            env_file=kwargs.pop("env_file", None),
            disable_auth=disable_auth,
            deployment_file=file,
        )
        return

    logger.info("FastAPI mode selected. Configuring for Uvicorn with app factory.")
    os.environ["ARCADE_DEBUG_MODE"] = str(debug)
    os.environ["ARCADE_OTEL_ENABLE"] = str(enable_otel)
    os.environ["ARCADE_DISABLE_AUTH"] = str(disable_auth)
    os.environ["ARCADE_DEPLOYMENT_FILE"] = str(file)

    toolkits_for_reload_dirs: list[Toolkit] | None = None
    if reload:
        # This discovery is only to tell the main Uvicorn reloader process which project dirs to watch.
        # The actual app running in the worker will do its own discovery via create_arcade_app.
        toolkits_for_reload_dirs = toolkits
        logger.debug(
            f"Reload mode: Uvicorn to watch {len(toolkits_for_reload_dirs) if toolkits_for_reload_dirs else 0} directories."
        )

    _run_fastapi_server(
        host=host,
        port=port,
        workers_param=workers,
        timeout_keep_alive=timeout_keep_alive,
        reload=reload,
        toolkits_for_reload_dirs=toolkits_for_reload_dirs,
        debug_flag=debug,
    )
    logger.info("Arcade serve process finished.")
