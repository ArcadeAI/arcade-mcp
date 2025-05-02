import asyncio
import logging
import os
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version as get_pkg_version
from pathlib import Path
from typing import Any

import fastapi
import uvicorn
from loguru import logger
from rich.console import Console

from arcade.cli.constants import ARCADE_CONFIG_PATH
from arcade.cli.utils import (
    build_tool_catalog,
    discover_toolkits,
    load_dotenv,
    validate_and_get_config,
)
from arcade.core.telemetry import OTELHandler
from arcade.sdk import Toolkit
from arcade.worker.fastapi.worker import FastAPIWorker

console = Console(width=70, color_system="auto")


def _run_mcp_stdio(
    toolkits: list[Toolkit], *, logging_enabled: bool, env_file: str | None = None
) -> None:
    """Launch an MCP stdio server; blocks until it exits."""

    from arcade.worker.mcp.stdio import StdioServer

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


def _run_fastapi_server(
    app: fastapi.FastAPI,
    *,
    host: str,
    port: int,
    workers: int,
    timeout_keep_alive: int,
    enable_otel: bool,
    otel_handler: OTELHandler,
    **uvicorn_kwargs: Any,
) -> None:
    """Run a FastAPI application via Uvicorn with graceful shutdown."""

    class CustomUvicornServer(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            # Disable Uvicorn's default signal handling; we manage it manually
            pass

        async def shutdown(self, sockets: Any = None) -> None:
            logger.info("Initiating graceful shutdown...")
            await super().shutdown(sockets=sockets)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        workers=workers,
        timeout_keep_alive=timeout_keep_alive,
        log_config=None,
        **uvicorn_kwargs,
    )

    server = CustomUvicornServer(config=config)

    async def _serve() -> None:
        await server.serve()

    async def _graceful_shutdown() -> None:
        try:
            logger.info("Shutting down server ...")
            await server.shutdown()

            # brief pause for connections to close gracefully
            await asyncio.sleep(0.5)
        finally:
            if enable_otel:
                otel_handler.shutdown()
            logger.debug("Server shutdown complete.")

    # Map signals to our graceful shutdown
    loop = asyncio.get_event_loop()
    for sig_name in (
        "SIGINT",
        "SIGTERM",
        "SIGHUP",
        "SIGUSR1",
        "SIGUSR2",
        "SIGWINCH",
        "SIGBREAK",
    ):
        if hasattr(signal, sig_name):
            loop.add_signal_handler(
                getattr(signal, sig_name), lambda: asyncio.create_task(_graceful_shutdown())
            )

    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        if enable_otel:
            otel_handler.shutdown()


class RichInterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Let Loguru handle caller info; don't do stack inspection here
        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: int = logging.INFO, mcp_mode: bool = False) -> None:
    # Intercept everything at the root logger
    logging.root.handlers = [RichInterceptHandler()]
    logging.root.setLevel(log_level)

    # Remove every other logger's handlers and propagate to root logger
    for name in logging.root.manager.loggerDict:
        # Keep handlers for MCP logger if middleware handles it separately
        if mcp_mode and name == "arcade.mcp":
            continue
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Remove default handlers from Loguru
    logger.remove()

    # Configure main Loguru sink
    # In MCP mode, all general console logs go to stderr to keep stdout clean
    sink_destination = sys.stderr if mcp_mode else sys.stdout

    # Configure loguru with a cleaner format and colors
    if log_level == logging.DEBUG:
        format_string = "<level>{level}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{file}:{line: <4}</cyan> | <level>{message}</level>"
    else:
        format_string = (
            "<level>{level}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        )
    logger.configure(
        handlers=[
            {
                "sink": sink_destination,  # Redirect sink based on mcp_mode
                "colorize": True,
                "level": log_level,
                # Format that ensures timestamp on every line and better alignment
                "format": format_string,
                # Make sure multiline messages are handled properly
                "enqueue": True,
                "diagnose": True,  # Disable traceback framing which adds noise
            }
        ]
    )
    if mcp_mode:
        logger.debug("Loguru sink configured for stderr in MCP mode.")


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        # This is necessary to prevent an unhandled error
        # when the user presses Ctrl+C
        logger.debug("Lifespan cancelled.")
        raise


def serve_default_worker(  # noqa: C901
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    enable_otel: bool = False,
    debug: bool = False,
    mcp: bool = False,
    **kwargs: Any,
) -> None:
    """
    Get a default instance of a FastAPI server with the Arcade Worker
    serving tools installed in the current Python environment.

    Args:
        host: The host to run the server on.
        port: The port to run the server on.
        disable_auth: Whether to disable authentication.
        workers: The number of workers to run.
        timeout_keep_alive: The timeout for keep-alive connections.
        enable_otel: Whether to enable OpenTelemetry.
        debug: Whether to enable debug logging.
        mcp: Whether to run worker as MCP server over stdio.
    """

    # Setup unified logging first
    version = get_pkg_version("arcade-ai")
    if mcp:
        validate_and_get_config()
    setup_logging(log_level=logging.DEBUG if debug else logging.INFO, mcp_mode=mcp)

    toolkits = discover_toolkits()
    logger.info("Serving the following toolkits:")
    toolkit_tool_counts: dict[str, int] = {}
    for toolkit in toolkits:
        for _, tools in toolkit.tools.items():
            toolkit_tool_counts[toolkit.name] = toolkit_tool_counts.get(toolkit.name, 0) + len(
                tools
            )
    for toolkit in toolkits:
        if debug:
            logger.info(f"{toolkit.name}: ({toolkit_tool_counts.get(toolkit.name, 0)} tools)")
            for filename, tools in toolkit.tools.items():
                for tool in tools:
                    logger.info(f"  - {filename}: {tool}")
        else:
            logger.info(f"  - {toolkit.name}: {toolkit_tool_counts.get(toolkit.name, 0)} tools")

    # --- MCP stdio --------------------------------------------------
    if mcp:
        env_file = kwargs.pop("env_file", None)
        _run_mcp_stdio(toolkits, logging_enabled=not debug, env_file=env_file)
        return

    # --- FastAPI HTTP --------------------------------------------------
    app = fastapi.FastAPI(
        title="Arcade Worker",
        description="A worker for the Arcade platform",
        version=version,
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
        openapi_url="/openapi.json" if debug else None,
        lifespan=lifespan,
    )

    secret = os.getenv("ARCADE_WORKER_SECRET", None)
    if secret is None:
        logger.warning("No secret found for Arcade Worker")
        logger.info(
            "Setting ARCADE_WORKER_SECRET environment variable to 'dev'. Set this in production"
        )
        secret = "dev"  # noqa: S105

    otel_handler = OTELHandler(
        app, enable=enable_otel, log_level=logging.DEBUG if debug else logging.INFO
    )
    worker = FastAPIWorker(
        app=app,
        secret=secret,
        disable_auth=disable_auth,
        otel_meter=otel_handler.get_meter(),
    )
    for toolkit in toolkits:
        worker.register_toolkit(toolkit)

    _run_fastapi_server(
        app,
        host=host,
        port=port,
        workers=workers,
        timeout_keep_alive=timeout_keep_alive,
        enable_otel=enable_otel,
        otel_handler=otel_handler,
        **kwargs,
    )
