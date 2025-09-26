"""
00_hello_world.py - The simplest possible MCP server

This example shows the absolute minimum code needed to create an MCP server
with a single tool using arcade-mcp-server.

To run (auto-discovery):
1. Keep this file in the current directory
2. Run: python -m arcade_mcp_server

For Claude Desktop (stdio transport):
   python -m arcade_mcp_server stdio
"""

from typing import Annotated

from arcade_mcp_server import tool


@tool
def greet(name: Annotated[str, "Name of the person to greet"]) -> Annotated[str, "Welcome message"]:
    """Greet a person by name with a welcome message."""

    return f"Hello, {name}! Welcome to Arcade MCP."


# That's it! The arcade_mcp_server CLI will handle everything else:
# - Creating the MCP server
# - Setting up the transport (stdio or HTTP)
# - Registering your tool
# - Handling all the protocol communication

# When you run `python -m arcade_mcp_server`, it will:
# 1. Discover this file (if in current directory)
# 2. Find the @tool decorated function
# 3. Create an MCP server with this tool
# 4. Start listening for requests
