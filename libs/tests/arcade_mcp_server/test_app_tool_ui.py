"""A tool added to an app carries its interface with it, the same as in a toolkit."""

from arcade_mcp_server import MCPApp, resource


def test_a_tool_added_to_an_app_registers_its_interface():
    @resource(path="dashboard.html")
    def dashboard() -> str:
        return "<!DOCTYPE html><p>dashboard</p>"

    app = MCPApp(name="widgets", version="1.0.0")

    @app.tool(ui=dashboard)
    def show() -> str:
        """Show a dashboard."""
        return ""

    registered = app._catalog.resources.get("ui://Widgets/1.0.0/dashboard.html")

    assert registered.resource.mimeType == "text/html;profile=mcp-app"
    assert show.__tool_ui__ is dashboard
