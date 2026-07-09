#!/usr/bin/env python3
"""ServiceNow MCP server"""

import sys

from arcade_mcp_server import MCPApp

import servicenow

app = MCPApp(name="servicenow", version="1.0.0", log_level="DEBUG")

app.add_tools_from_module(servicenow)

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    #   Supports tools that require_auth or require_secrets out-of-the-box
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    #   Does not support tools that require_auth or require_secrets unless the server is deployed
    #   using 'arcade deploy' or added in the Arcade Developer Dashboard with 'Arcade' server type
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)
