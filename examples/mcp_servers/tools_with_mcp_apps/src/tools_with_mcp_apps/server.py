import sys
from importlib.metadata import version

from arcade_mcp_server import MCPApp

import tools_with_mcp_apps

app = MCPApp(name="tools_with_mcp_apps", version=version("tools_with_mcp_apps"))
app.add_tools_from_module(tools_with_mcp_apps)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
