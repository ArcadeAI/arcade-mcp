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
from arcade_core.telemetry import OTELHandler
from arcade_core.toolkit import Toolkit, get_package_directory
from arcade_serve.fastapi.worker import FastAPIWorker
from loguru import logger
from rich.console import Console

from arcade_cli.constants import ARCADE_CONFIG_PATH
from arcade_cli.utils import (
    build_tool_catalog,
    discover_toolkits,
    load_dotenv,
)

console = Console(width=70, color_system="auto")


# App factory for Uvicorn reload
def create_arcade_app() -> fastapi.FastAPI:
    # TODO: Find a better way to pass these configs to factory used for reload
    debug_mode = os.environ.get("ARCADE_WORKER_SECRET", "dev") == "dev"
    otel_enabled = os.environ.get("ARCADE_OTEL_ENABLE", "False").lower() == "true"
    auth_for_reload = not debug_mode

    # Call setup_logging here to ensure Uvicorn worker processes also get Loguru formatting
    # for all standard library loggers.
    # The log_level for Uvicorn itself is set via uvicorn.run(log_level=...),
    # this call primarily aims to capture third-party library logs into Loguru.
    setup_logging(log_level=logging.DEBUG if debug_mode else logging.INFO, mcp_mode=False)

    logger.info(f"Debug: {debug_mode}, OTEL: {otel_enabled}, Auth Disabled: {auth_for_reload}")
    version = get_pkg_version("arcade-ai")
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
    otel_handler.instrument_app(app)

    secret = os.getenv("ARCADE_WORKER_SECRET", "dev")
    if secret == "dev" and not os.environ.get("ARCADE_WORKER_SECRET"):  # noqa: S105
        logger.warning("Using default 'dev' for ARCADE_WORKER_SECRET. Set this in production.")

    worker = FastAPIWorker(
        app=app,
        secret=secret,
        disable_auth=not debug_mode,  # TODO (Sam): possible unexpected behavior on reload here?
        otel_meter=otel_handler.get_meter(),
    )
    for tk in toolkits:
        worker.register_toolkit(tk)

    return app


def _run_mcp_stdio(
    toolkits: list[Toolkit], *, logging_enabled: bool, env_file: str | None = None
) -> None:
    """Launch an MCP stdio server; blocks until it exits."""

    from arcade_serve.mcp.stdio import StdioServer

    # Load env vars before launching server (explicit path, config path, cwd)
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        for candidate in [Path(ARCADE_CONFIG_PATH) / "arcade.env", Path.cwd() / "arcade.env"]:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break

    # Set up middleware configuration for stdio mode
    middleware_config = {
        "stdio_mode": True,  # Ensure logs go to stderr
    }

    catalog = build_tool_catalog(toolkits)
    server = StdioServer(
        catalog,
        enable_logging=logging_enabled,
        middleware_config=middleware_config,
    )

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
    app: fastapi.FastAPI, otel_handler: OTELHandler | None = None, enable_otel: bool = False
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
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    enable_otel: bool = False,
    debug: bool = False,
    mcp: bool = False,
    reload: bool = False,
    **kwargs: Any,
) -> None:
    # Initial logging setup for the main `arcade serve` process itself.
    # The Uvicorn worker processes will call setup_logging() again via create_arcade_app().
    setup_logging(log_level=logging.DEBUG if debug else logging.INFO, mcp_mode=mcp)

    if mcp:
        logger.info("MCP mode selected.")
        toolkits_for_mcp = discover_toolkits()
        _run_mcp_stdio(
            toolkits_for_mcp, logging_enabled=not debug, env_file=kwargs.pop("env_file", None)
        )
        return

    logger.info("FastAPI mode selected. Configuring for Uvicorn with app factory.")
    os.environ["ARCADE_DEBUG_MODE"] = str(debug)
    os.environ["ARCADE_OTEL_ENABLE"] = str(enable_otel)
    os.environ["ARCADE_DISABLE_AUTH"] = str(disable_auth)

    toolkits_for_reload_dirs: list[Toolkit] | None = None
    if reload:
        # This discovery is only to tell the main Uvicorn reloader process which project dirs to watch.
        # The actual app running in the worker will do its own discovery via create_arcade_app.
        toolkits_for_reload_dirs = discover_toolkits()
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
