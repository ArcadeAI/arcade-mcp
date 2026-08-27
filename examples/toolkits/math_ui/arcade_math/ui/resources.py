from pathlib import Path

from arcade_tdk import resource

# The MCP Apps extension pins this exact string, and the reference host compares
# it with equality before it will render. Spacing and casing are part of it.
MCP_APP_HTML = "text/html;profile=mcp-app"

_HERE = Path(__file__).parent


@resource(
    path="sum-list.html",
    name="sum_list_ui",
    title="Sum a list of numbers",
    description="Interface for the SumList tool: enter numbers, see the running total.",
    mime_type=MCP_APP_HTML,
)
def sum_list_ui() -> str:
    """The document a host renders for SumList.

    Returned as text rather than a path, because the framework resolves a
    resource once at registration and serves the bytes from memory afterwards.
    """
    return (_HERE / "sum_list.html").read_text(encoding="utf-8")
