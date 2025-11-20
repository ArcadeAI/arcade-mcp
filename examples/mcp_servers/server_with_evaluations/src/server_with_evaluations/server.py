#!/usr/bin/env python3
"""server-with-evaluations MCP server"""

from arcade_mcp_server import MCPApp

import server_with_evaluations

app = MCPApp(name="ServerWithEvaluations", version="1.0.0", log_level="DEBUG")

app.add_tools_from_module(server_with_evaluations)

if __name__ == "__main__":
    app.run(transport="stdio")
