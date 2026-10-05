from importlib.metadata import version

from arcade_mcp_server import MCPApp

import app_tools

app = MCPApp(name="AppTools", version=version("app_tools"))
app.add_tools_from_module(app_tools)


if __name__ == "__main__":
    app.run()
