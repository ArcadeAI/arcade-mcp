#!/usr/bin/env python3
"""server_branding MCP server.

Demonstrates the server-level branding fields added to ``Implementation``
(``InitializeResult.serverInfo``) in MCP 2025-11-25:

- ``icons: list[Icon]``       — SEP-973. Clients render these next to the server name.
- ``description: str``        — Free-form prose that a client can surface.
- ``websiteUrl: str``         — Link to docs / marketing page.

The ``Icon`` type supports ``src`` (URL or ``data:`` URI), ``mimeType``,
``sizes`` (WHATWG icon-size syntax: ``"48x48"``, ``"any"``), and
``theme`` (``"light"`` / ``"dark"``). A single server can register multiple
icons for different themes and DPIs — the client picks the best one.

This example also demonstrates the **tool name format guidance** from
SEP-986 (enforced via ``validation.is_valid_tool_name``): tool names MUST
match ``[A-Za-z0-9_.-]{1,128}``, and Arcade canonicalises snake_case
function names to PascalCase at register time.
"""

import base64
import sys
from typing import Annotated

from arcade_mcp_server import Context, Icon, MCPApp

# -----------------------------------------------------------------------------
# Server branding — the point of this example
# -----------------------------------------------------------------------------

# A tiny inline SVG icon for light themes. In production you'd typically
# host your icons at a public URL and reference them by https URL.
_LIGHT_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' fill='#4c6ef5'/>"
    "<text x='32' y='40' text-anchor='middle' font-family='monospace' "
    "font-size='28' fill='white'>AC</text></svg>"
)
_DARK_SVG = _LIGHT_SVG.replace("#4c6ef5", "#fa5252")

# Encode them as base64 data URIs so the example is fully self-contained.


def _svg_data_uri(svg: str) -> str:
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


app = MCPApp(
    name="server_branding",
    version="1.0.0",
    title="Server Branding Demo",
    description=(
        "Example MCP server showing off the 2025-11-25 server-level branding fields: "
        "icons, description, and websiteUrl. Inspect the initialize response to see them."
    ),
    website_url="https://arcade.dev",
    icons=[
        # Light-theme icon at two sizes.
        Icon(
            src=_svg_data_uri(_LIGHT_SVG),
            mimeType="image/svg+xml",
            sizes=["64x64", "any"],
            theme="light",
        ),
        # Dark-theme icon.
        Icon(
            src=_svg_data_uri(_DARK_SVG),
            mimeType="image/svg+xml",
            sizes=["64x64", "any"],
            theme="dark",
        ),
        # External URL for a larger hero image — clients that want a big icon
        # can fetch this directly.
        Icon(
            src="https://docs.arcade.dev/images/arcade-logo-512.png",
            mimeType="image/png",
            sizes=["512x512"],
        ),
    ],
    instructions=(
        "This server exists to demonstrate server branding. The `echo` tool below is a "
        "placeholder — the feature is in the serverInfo you see at initialize time."
    ),
    log_level="DEBUG",
)


# -----------------------------------------------------------------------------
# One trivial tool so the catalog isn't empty.
# -----------------------------------------------------------------------------


@app.tool
def echo(msg: Annotated[str, "A message to echo back"]) -> str:
    """Echo the message. The real point of this server is its ``initialize``
    response — this tool exists so the catalog isn't empty.
    """
    return msg


# -----------------------------------------------------------------------------
# Tool name format (SEP-986)
# -----------------------------------------------------------------------------
#
# MCP 2025-11-25 SHOULD: tool names match ``[A-Za-z0-9_.-]{1,128}``. Arcade's
# convention is PascalCase (``snake_to_pascal_case`` is applied at register
# time), which is a strict subset of the SHOULD pattern. Examples:
#
#   def generate_report(...)    -> "GenerateReport"       ✔ valid
#   def search_by_tag(...)      -> "SearchByTag"          ✔ valid
#   name="data.fetch-utility"                             ✔ valid (passes the SHOULD pattern)
#   name="my tool"                                        ✘ space is not allowed
#   name="🚀launch"                                        ✘ emoji not allowed
#
# If you override ``name=`` on ``@app.tool`` or ``@tool``, the library does
# NOT silently mangle it; you get a SHOULD-violating name on the wire.
# ``is_valid_tool_name`` in ``arcade_mcp_server.validation`` lets you check.


@app.tool(name="data.fetch-utility")
def fetch_something() -> str:
    """Demonstrate a custom dotted-with-dash name — valid under SEP-986."""
    return "fetched"


@app.tool
def ready_to_ship(context: Context) -> str:
    """Name will be canonicalised to ``ReadyToShip`` at register time."""
    return "👍"


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # HTTP makes it easier to curl the initialize response.
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    app.run(transport=transport, host="127.0.0.1", port=8000)
