#!/usr/bin/env python3
"""E2E integration test MCP server"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp

import server

app = MCPApp(name="server", version="1.0.0", log_level="DEBUG")
app.add_tools_from_module(server)


@app.tool
def hello_world(name: Annotated[str, "The name to say hello to"]) -> str:
    """Say hello to the given name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport, host="127.0.0.1", port=8000)
