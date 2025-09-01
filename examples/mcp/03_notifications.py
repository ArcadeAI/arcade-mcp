#!/usr/bin/env python3
"""03: Notifications via ToolContext (log + progress).

Run:
  python 03_notifications.py [stream|sse|stdio]

Clients that support notifications (e.g., Cursor/Claude Desktop) will
render progress and log messages. If unsupported, calls silently no-op.
"""

# standard library
import asyncio
import sys
from typing import Annotated

from arcade_core.schema import ToolContext

# third-party
from arcade_mcp import Server
from arcade_tdk import tool


@tool(desc="Demonstrate progress and log notifications")
async def demo_progress(
    context: ToolContext,
    count: Annotated[int, "The number of steps to complete"] = 3,
) -> str:
    """Emit a few progress updates and log lines, then return a message.

    If the client didn't provide a progress token, progress updates no-op.
    """
    await context.log.info("Starting demo")

    async with context.notify.progress(message="Working...", total=count) as tracker:
        for i in range(count):
            await asyncio.sleep(0.5)
            await tracker.update(i + 1, message=f"Step {i + 1} of {count}")
            if (i + 1) % 2 == 0:
                await context.log.debug(f"Reached step {i + 1}")

    await context.log.info("Done")
    return "Completed demo"


server = Server(name="notifications_example", version="0.1.0")
server.add_tool(demo_progress)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stream"
    server.run(transport=transport, host="0.0.0.0", port=8000)
