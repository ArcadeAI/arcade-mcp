import logging
import os

from rich.console import Console

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

DEVELOPMENT_SECRET = "dev"  # noqa: S105

logger = logging.getLogger(__name__)
console = Console()


def serve_default_actor(
    host: str = "127.0.0.1", port: int = 8000, disable_auth: bool = False
) -> None:
    """
    Get an instance of a FastAPI server with the Arcade Actor.
    """
    # Use Uvicorn's default log config for Arcade logging,
    # to ensure a nice consistent style for all logs.
    logging_config = uvicorn.config.LOGGING_CONFIG
    logging_config["loggers"]["arcade"] = {
        "handlers": ["default"],
        "level": "INFO",
        "propagate": False,
    }

    # TODO: Pass in a logging config from the CLI, to set the log level.
    logging.config.dictConfig(logging_config)

    toolkits = Toolkit.find_all_arcade_toolkits()
    if not toolkits:
        logger.error("No toolkits found in Python environment. Exiting...")
        return
    else:
        logger.info("Serving the following toolkits:")
        for toolkit in toolkits:
            logger.info(f"  - {toolkit.name} ({toolkit.package_name})")

    actor_secret = os.environ.get("ARCADE_ACTOR_SECRET")
    if not actor_secret:
        logger.warning(
            "Warning: ARCADE_ACTOR_SECRET environment variable is not set. Using 'dev' as the actor secret.",
        )
        actor_secret = DEVELOPMENT_SECRET

    app = fastapi.FastAPI(
        title="Arcade AI Actor",
        description="Arcade AI default Actor implementation using FastAPI.",
        version="0.1.0",
    )
    actor = FastAPIActor(app, secret=actor_secret, disable_auth=disable_auth)
    for toolkit in toolkits:
        actor.register_toolkit(toolkit)

    logger.info("Starting FastAPI server...")

    uvicorn.run(
        app=app,
        host=host,
        port=port,
        log_config=logging_config,
    )
