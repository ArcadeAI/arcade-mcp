from arcade_mcp_server import resource


@resource(file="editor.html", title="Greeting editor")
def editor() -> None:
    """Edit a greeting and call tools through the connected MCP host."""


@resource(
    path="author-guide",
    scheme="https",
    mime_type="text/plain",
    meta={"webUrl": "https://modelcontextprotocol.io/extensions/apps/overview"},
)
def author_guide() -> str:
    """An HTTPS-scheme resource is read with resources/read, not a browser fetch."""
    return "MCP Apps guide: https://modelcontextprotocol.io/extensions/apps/overview"
