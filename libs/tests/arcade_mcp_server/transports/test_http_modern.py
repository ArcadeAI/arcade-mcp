"""Ordinary modern tools and discovery work without an initialization exchange."""

import httpx
import pytest
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

VERSION = "2026-07-28"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": VERSION,
}
META = {
    "io.modelcontextprotocol/protocolVersion": VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "modern-proof", "version": "1"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("configured_stateless", [False, True])
async def test_discovery_and_ordinary_call_without_initialization(
    mcp_server: MCPServer, configured_stateless: bool
) -> None:
    manager = HTTPSessionManager(
        server=mcp_server, json_response=True, stateless=configured_stateless
    )

    async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        await manager.handle_request(scope, receive, send)

    app = Starlette(routes=[Mount("/mcp", app=endpoint)])
    async with (
        manager.run(),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://server"
        ) as client,
    ):
        result = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "TestToolkit_test_tool",
                    "arguments": {"text": "modern"},
                    "_meta": META,
                },
            },
        )
        assert result.status_code == 200, "modern tool call was rejected: " + result.text
        assert result.json()["id"] == 3
        assert result.json()["result"]["content"] == [{"type": "text", "text": "Echo: modern"}]
        assert result.json()["result"]["resultType"] == "complete"
        assert "mcp-session-id" not in result.headers

        discovery = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "server/discover",
                "params": {"_meta": META},
            },
        )
        assert discovery.status_code == 200, "modern discovery was rejected: " + discovery.text
        assert discovery.json()["id"] == 1
        assert discovery.json()["result"]["supportedVersions"] == [
            VERSION,
            "2025-11-25",
            "2025-06-18",
        ]
        assert discovery.json()["result"]["capabilities"] == {"tools": {}}
        assert "mcp-session-id" not in discovery.headers

        listing = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": META}},
        )
        assert listing.status_code == 200, listing.text
        tools = listing.json()["result"]["tools"]
        ordinary = next(tool for tool in tools if tool["name"] == "TestToolkit_test_tool")
        assert ordinary["inputSchema"]["properties"]["text"]["type"] == "string"
        conflict = await client.post(
            "/mcp/",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/list",
                "params": {
                    "_meta": {**META, "io.modelcontextprotocol/protocolVersion": "2025-11-25"}
                },
            },
        )
        assert conflict.status_code == 400, conflict.text
        assert conflict.json()["id"] == 4
        assert conflict.json()["error"]["code"] == -32020
