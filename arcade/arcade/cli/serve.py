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

console = Console()


def serve_default_actor(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Get an instance of a FastAPI server with the Arcade Actor.
    """
    toolkits = Toolkit.find_all_arcade_toolkits()
    if not toolkits:
        console.print("No toolkits found in Python environment. Exiting...", style="bold red")
        return
    else:
        console.print("Serving the following toolkits:", style="bold blue")
        for toolkit in toolkits:
            console.print(f"  - {toolkit.name} ({toolkit.package_name})")

    app = fastapi.FastAPI(
        title="Arcade AI Actor",
        description="Arcade AI default Actor implementation using FastAPI.",
        version="0.1.0",
    )
    actor = FastAPIActor(app)
    for toolkit in toolkits:
        actor.register_toolkit(toolkit)

    console.print("Starting FastAPI server...", style="bold blue")

    uvicorn.run(
        app=app,
        host=host,
        port=port,
    )
