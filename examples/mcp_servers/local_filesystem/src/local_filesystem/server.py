#!/usr/bin/env python3
"""local_filesystem MCP server"""

import sys

from arcade_mcp_server import MCPApp

import local_filesystem

# import local_filesystem.tools as tools


app = MCPApp(name="local_filesystem", version="1.0.0", log_level="DEBUG")
app.add_tools_from_module(local_filesystem)

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8074)
