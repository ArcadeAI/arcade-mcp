"""Run the POC server over HTTP with permissive CORS, so a browser-based MCP Apps
host (e.g. the ext-apps basic-host on :8080) can connect cross-origin.

Why this is needed: arcade-mcp's HTTP transport only emits a proper CORS *preflight*
(OPTIONS) handler when the OAuth resource-server middleware is enabled. A no-auth
server answers OPTIONS with 405, which browsers treat as a failed preflight and
refuse to connect (curl/non-browser clients are unaffected — they don't preflight).

This wraps the FastAPI app with Starlette's CORSMiddleware (which short-circuits
the preflight with a 200 and adds the headers) without modifying the library.

Run:  uv run --directory <arcade-mcp> python examples/mcp_servers/google_sheets_app/run_cors.py [port]
"""

import sys

import arcade_mcp_server.mcp_app as mcp_app
from fastapi.middleware.cors import CORSMiddleware

_orig_create_arcade_mcp = mcp_app.create_arcade_mcp


def _create_arcade_mcp_with_cors(*args, **kwargs):
    app = _orig_create_arcade_mcp(*args, **kwargs)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "Mcp-Protocol-Version"],
    )
    return app


mcp_app.create_arcade_mcp = _create_arcade_mcp_with_cors

import server  # noqa: E402  — module-level code registers the tools + resources

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server.app.run(transport="http", host="127.0.0.1", port=port)
