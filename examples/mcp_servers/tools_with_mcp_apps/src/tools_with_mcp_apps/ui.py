from arcade_mcp_server import resource


@resource(file="editor.html", title="Greeting editor")
def editor() -> None:
    """Edit a greeting and call tools through the connected MCP host."""


@resource(
    path="author-guide",
    scheme="resource",
    mime_type="text/plain",
    meta={"webUrl": "https://modelcontextprotocol.io/extensions/apps/overview"},
)
def author_guide() -> str:
    """Read the MCP Apps guide link with resources/read."""
    return "MCP Apps guide: https://modelcontextprotocol.io/extensions/apps/overview"
