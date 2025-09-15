#!/usr/bin/env python
"""
02_building_apps.py - Build an MCP server using MCPApp

This example shows how to build and run an MCP server programmatically
using `MCPApp` instead of relying on the arcade_mcp CLI.

To run (HTTP transport by default):
    python 02_building_apps.py

To run with stdio transport (for Claude Desktop):
    python 02_building_apps.py stdio
"""

import sys
import warnings
from typing import Annotated

from arcade_mcp import MCPApp

# Suppress the deprecation warning since we're using the recommended import
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="arcade_tdk")
    from arcade_tdk import Context


# Create the MCP application
app = MCPApp(
    name="my_mcp_server",
    version="0.1.0",
    instructions="Example MCP server built with MCPApp"
)


@app.tool
def greet(name: Annotated[str, "Name of the person to greet"]) -> Annotated[str, "Greeting message"]:
    """Return a friendly greeting.

    Parameters:
        name: Person's name

    Returns:
        Greeting message.
    """
    return f"Hello, {name}!"


@app.tool
async def whoami(context: Context) -> Annotated[dict, "Basic server and user information"]:
    """Return basic information from the tool context.

    Returns:
        Dictionary with `user_id` and whether MCP features are available.
    """
    user_id = context.user_id or "anonymous"

    if context.mcp:
        await context.mcp.log("info", f"whoami called by: {user_id}")

    return {
        "user_id": user_id,
        "has_mcp": context.mcp is not None,
        "secret_keys": list(context.secrets.keys()),
    }


if __name__ == "__main__":
    # Check if stdio transport was requested
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        app.run(transport="stdio")
    else:
        # Default to HTTP transport
        app.run(host="127.0.0.1", port=8001)
