import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger

try:
    import fastapi
except ImportError:
    raise ImportError(
        "FastAPI is not installed. Please install it using `pip install arcade-ai[fastapi]`."
    )

try:
    import uvicorn
except ImportError:
    raise ImportError("Uvicorn is not installed. Please install it using `pip install uvicorn`.")

from arcade.actor.fastapi.actor import FastAPIActor
from arcade.core.toolkit import Toolkit


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
                "format": "{time:MM-DD HH:mm:ss} | {level: <8} | {message}"
                + (" {name}:{function}:{line}" if log_level <= logging.DEBUG else "")
                + ("{exception}\n" if "{exception}" in "{message}" else ""),
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


def serve_default_actor(
    host: str = "127.0.0.1",
    port: int = 8002,
    disable_auth: bool = False,
    workers: int = 1,
    timeout_keep_alive: int = 5,
    **kwargs: Any,
) -> None:
    """
    Get an instance of a FastAPI server with the Arcade Actor.
    """
    # Setup unified logging
    setup_logging()

    toolkits = Toolkit.find_all_arcade_toolkits()
    if not toolkits:
        logger.error("No toolkits found in Python environment. Exiting...")
        return
    else:
        logger.info("Serving the following toolkits:")
        for toolkit in toolkits:
            logger.info(f"  - {toolkit.name} ({toolkit.package_name}): {len(toolkit.tools)} tools")

    actor_secret = os.environ.get("ARCADE_ACTOR_SECRET")
    if not disable_auth and not actor_secret:
        logger.warning(
            "Warning: ARCADE_ACTOR_SECRET environment variable is not set. Using 'dev' as the actor secret.",
        )
        actor_secret = actor_secret or "dev"

    app = fastapi.FastAPI(
        title="Arcade AI Actor",
        description="Arcade AI default Actor implementation using FastAPI.",
        version="0.1.0",
        lifespan=lifespan,  # Use custom lifespan to catch errors, notably KeyboardInterrupt (Ctrl+C)
    )
    actor = FastAPIActor(app, secret=actor_secret, disable_auth=disable_auth)
    for toolkit in toolkits:
        actor.register_toolkit(toolkit)

    logger.info("Starting FastAPI server...")

    class CustomUvicornServer(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass  # Disable Uvicorn's default signal handlers

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

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        logger.debug("Server shutdown complete.")
