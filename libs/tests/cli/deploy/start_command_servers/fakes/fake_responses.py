"""MCP answers shared by the stand-in servers in this directory.

They answer just enough of streamable HTTP for the CLI's handshake and tool listing.
"""

import json
from typing import Any

SESSION_ID = "fake-session"


def answer(body: bytes, *, sse: bool = False) -> tuple[int, dict[str, str], bytes]:
    """Return (status, headers, body) for one JSON-RPC message posted to the endpoint."""
    message = json.loads(body)
    if "id" not in message:
        return 202, {}, b""

    result: dict[str, Any]
    if message["method"] == "initialize":
        result = {
            "protocolVersion": message["params"]["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake-mcp", "version": "1.0.0"},
        }
    elif message["method"] == "tools/list":
        result = {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]}
    else:
        result = {}

    payload = json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result})
    headers = {"Mcp-Session-Id": SESSION_ID}
    if sse:
        headers["Content-Type"] = "text/event-stream"
        return 200, headers, f"event: message\ndata: {payload}\n\n".encode()
    headers["Content-Type"] = "application/json"
    return 200, headers, payload.encode()
