#!/usr/bin/env python3
"""
00_hello_world.py - The simplest possible MCP server

This example shows the absolute minimum code needed to create an MCP server
with a single tool using arcade-mcp-server with direct Python execution.

To run:
    uv run 00_hello_world.py           # HTTP transport (default)
    uv run 00_hello_world.py stdio     # stdio transport for Claude Desktop
"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp

# Create the MCP application
app = MCPApp(
    name="hello_world", version="1.0.0", instructions="A simple MCP server with a greeting tool"
)


@app.tool
def greet(name: Annotated[str, "Name of the person to greet"]) -> Annotated[str, "Welcome message"]:
    """Greet a person by name with a welcome message."""
    return f"Hello, {name}! Welcome to Arcade MCP."


if __name__ == "__main__":
    # Check if stdio transport was requested
    transport = "stdio" if len(sys.argv) > 1 and sys.argv[1] == "stdio" else "http"

    print(f"Starting {app.name} v{app.version}")
    print(f"Transport: {transport}")

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)
