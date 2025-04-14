import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any

import fastapi
import uvicorn
from loguru import logger

from arcade.core.telemetry import OTELHandler
from arcade.sdk import Toolkit
from arcade.worker.fastapi.worker import FastAPIWorker


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: int = logging.INFO) -> None:
    # Intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)

    # Remove every other logger's handlers
    # and propagate to root logger
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Configure loguru with custom format, no colors
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "serialize": False,
                "level": log_level,
                "format": "{level}  [{time:HH:mm:ss.SSS}] {message}"
                + (" {name}:{function}:{line}" if log_level <= logging.DEBUG else "")
                + ("\n{exception}" if "{exception}" in "{message}" else ""),
            }
        ]
    )


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore[no-untyped-def]
    try:
        yield
    except asyncio.CancelledError:
        # This is necessary to prevent an unhandled error
        # when the user presses Ctrl+C
        logger.debug("Lifespan cancelled.")


def serve_default_worker(  # noqa: C901
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    enable_otel: bool = False,
    debug: bool = False,
    enable_mcp: bool = False,
    mcp_type: str = "sse",
    mcp_config: dict[str, str | int | bool] | None = None,
    enable_mcp_logging: bool = False,
    mcp_logging_config: dict[str, str | int | bool] | None = None,
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

    # Default MCP configuration if not provided
    if mcp_config is None:
        mcp_config = {
            "server_name": "Arcade Worker",
            "server_version": "0.1.0",
            "instructions": "Arcade Worker with MCP enabled",
            "sse_path": "/sse",
            "message_path": "messages/",
        }

    # Default MCP logging configuration if not provided
    if mcp_logging_config is None:
        mcp_logging_config = {
            "log_level": "INFO",
            "log_request_body": True,
            "log_response_body": True,
            "log_errors": True,
            "min_duration_to_log_ms": 0,
        }

    worker = FastAPIWorker(
        app,
        secret=worker_secret,
        disable_auth=disable_auth,
        otel_meter=otel_handler.get_meter(),
        enable_mcp=enable_mcp,
        mcp_type=mcp_type,
        mcp_config=mcp_config,
        enable_mcp_logging=enable_mcp_logging,
        mcp_logging_config=mcp_logging_config,
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

    if enable_mcp:
        logger.info(f"MCP enabled with type: {mcp_type}")
        if mcp_type == "sse" or mcp_type == "both":
            logger.info(f"MCP SSE endpoint: http://{host}:{port}/mcp{mcp_config['sse_path']}")
            logger.info(
                f"MCP message endpoint: http://{host}:{port}/mcp/{mcp_config['message_path']}"
            )

    logger.info("Starting FastAPI server...")

    class CustomUvicornServer(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass  # Disable Uvicorn's default signal handlers

        async def shutdown(self, sockets=None) -> None:
            """
            Custom shutdown that properly cleans up resources.
            """
            logger.info("Initiating graceful shutdown...")

            # If MCP is enabled, properly shutdown MCP servers
            if enable_mcp and hasattr(worker, "mcp_components"):
                for component in worker.mcp_components:
                    if hasattr(component, "mcp_server") and hasattr(
                        component.mcp_server, "shutdown"
                    ):
                        try:
                            logger.debug("Shutting down MCP server...")
                            await component.mcp_server.shutdown()
                        except Exception as e:
                            logger.exception(f"Error shutting down MCP server: {e}")

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

        # Setup graceful shutdown handlers
        for signal_name in ("SIGINT", "SIGTERM"):
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
