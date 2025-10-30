#!/usr/bin/env python3
"""progress_reporting MCP server"""

import asyncio
import sys

from arcade_mcp_server import Context, MCPApp

app = MCPApp(name="progress_reporting", version="1.0.0", log_level="DEBUG")


@app.tool
async def report_progress(context: Context) -> str:
    """Report progress back to the client"""
    total = 5

    for i in range(total):
        await context.progress.report(i + 1, total=total, message=f"Step {i + 1} of {total}")
        await asyncio.sleep(1)

    return "All progress reported successfully"


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    app.run(transport=transport, host="127.0.0.1", port=8000)
