import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any

import fastapi
import psutil
import uvicorn
from loguru import logger
from rich.console import Console

from arcade.core.telemetry import OTELHandler
from arcade.sdk import Toolkit
from arcade.worker.fastapi.worker import FastAPIWorker

console = Console(width=70, color_system="auto")


class RichInterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Let Loguru handle caller info; don't do stack inspection here
        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: int = logging.INFO) -> None:
    # Intercept everything at the root logger
    logging.root.handlers = [RichInterceptHandler()]
    logging.root.setLevel(log_level)

    # Remove every other logger's handlers and propagate to root logger
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Remove default handlers
    logger.remove()

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
                "sink": sys.stdout,
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


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore[no-untyped-def]
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        # This is necessary to prevent an unhandled error
        # when the user presses Ctrl+C
        logger.debug("Lifespan cancelled.")
        app.lifespan_context.cancel()
        raise


def serve_default_worker(  # noqa: C901
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    enable_otel: bool = False,
    debug: bool = False,
    **kwargs: Any,
) -> None:
    """
    Get an instance of a FastAPI server with the Arcade Worker.
    """
    # Setup unified logging
    setup_logging(log_level=logging.DEBUG if debug else logging.INFO)

    toolkits = Toolkit.find_all_arcade_toolkits()
    if not toolkits:
        raise RuntimeError("No toolkits found in Python environment.")

    worker_secret = os.environ.get("ARCADE_WORKER_SECRET")
    if not disable_auth and not worker_secret:
        logger.warning(
            "Warning: ARCADE_WORKER_SECRET environment variable is not set. Using 'dev' as the worker secret.",
        )
        worker_secret = worker_secret or "dev"

    app = fastapi.FastAPI(
        title="Arcade Worker",
        description="Arcade default Worker implementation using FastAPI.",
        version="0.1.0",
        lifespan=lifespan,  # Use custom lifespan to catch errors, notably KeyboardInterrupt (Ctrl+C)
    )

    otel_handler = OTELHandler(app, enable=enable_otel)

    worker = FastAPIWorker(
        app,
        secret=worker_secret,
        disable_auth=disable_auth,
        otel_meter=otel_handler.get_meter(),
    )

    toolkit_tool_counts = {}
    for toolkit in toolkits:
        prev_tool_count = worker.catalog.get_tool_count()
        worker.register_toolkit(toolkit)
        new_tool_count = worker.catalog.get_tool_count()
        toolkit_tool_counts[f"{toolkit.name} ({toolkit.package_name})"] = (
            new_tool_count - prev_tool_count
        )

    logger.info("Serving the following toolkits:")
    for name, tool_count in toolkit_tool_counts.items():
        logger.info(f"  - {name}: {tool_count} tools")

    logger.info(f"Starting FastAPI server with PID: {psutil.Process().pid}")

    class CustomUvicornServer(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass  # Disable Uvicorn's default signal handlers

        async def shutdown(self, sockets: Any = None) -> None:
            """
            Custom shutdown that properly cleans up resources.
            """
            logger.info("Initiating graceful shutdown...")

            # Now do the standard server shutdown
            await super().shutdown(sockets=sockets)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        workers=workers,
        timeout_keep_alive=timeout_keep_alive,
        log_config=None,
        **kwargs,
    )
    server = CustomUvicornServer(config=config)

    async def serve() -> None:
        await server.serve()

    async def shutdown() -> None:
        # Custom clean shutdown
        try:
            logger.info("Shutting down")
            await server.shutdown()

            # Give a brief period for connections to close properly
            logger.info("Waiting for connections to close. (CTRL+C to force quit)")
            try:
                # Wait a short time for connections to finalize
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                logger.info("Forced immediate shutdown")

        except Exception as e:
            logger.exception(f"Error during server shutdown: {e}")

        if enable_otel:
            otel_handler.shutdown()
        logger.debug("Server shutdown complete.")

    try:
        loop = asyncio.get_event_loop()

        # Signals we want to forward from wrapper process to the child
        sig_names = ["SIGINT", "SIGTERM", "SIGHUP", "SIGUSR1", "SIGUSR2", "SIGWINCH", "SIGBREAK"]

        # Setup graceful shutdown handlers
        for signal_name in sig_names:
            if hasattr(signal, signal_name):
                loop.add_signal_handler(
                    getattr(signal, signal_name), lambda: asyncio.create_task(shutdown())
                )

        # Run the server
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except asyncio.CancelledError:
        logger.info("Server tasks cancelled.")
    except Exception as e:
        logger.error(f"Error running server: {e}")
    finally:
        # Ensure cleanup runs even if there's an exception
        try:
            if enable_otel:
                otel_handler.shutdown()
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")

        logger.debug("Server shutdown complete.")
