import asyncio
import time
from typing import Annotated

from arcade_mcp_server import Context, tool


@tool
async def slow_async_tool(
    context: Context, delay_seconds: Annotated[float, "Delay in seconds"]
) -> str:
    """A tool that takes time to execute (async)."""
    await asyncio.sleep(delay_seconds)
    return f"Completed async task after {delay_seconds}s"


@tool
def slow_sync_tool(context: Context, delay_seconds: Annotated[float, "Delay in seconds"]) -> str:
    """A tool that takes time to execute (sync)."""
    time.sleep(delay_seconds)
    return f"Completed sync task after {delay_seconds}s"
