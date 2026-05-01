"""Full ASGI / httpx integration tests for the HTTP Streamable transport.

These tests exercise the complete ASGI request/response cycle end-to-end using
httpx.ASGITransport + a minimal Starlette application that mounts
HTTPSessionManager. This complements the helper-function-level tests in
test_phase7_transport.py and the multi-version E2E tests in
integration/test_multi_version_e2e.py, which mock or bypass the ASGI layer.

Covers:
- CORS preflight (OPTIONS)
- Origin header validation
- Accept header validation (both application/json and text/event-stream required
  on POST except for initialize)
- MCP-Protocol-Version header validation (stateful + stateless)
- 400 on missing Mcp-Session-Id for non-initialize POSTs (stateful mode)
- Full initialize → initialized → tools/list round-trip
- Transport-level error shape (omits id)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _build_asgi_app(manager: HTTPSessionManager) -> Starlette:
    async def mcp_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        await manager.handle_request(scope, receive, send)

    return Starlette(routes=[Mount("/mcp", app=mcp_endpoint)])


@asynccontextmanager
async def _http_client(
    mcp_server: MCPServer,
    *,
    stateless: bool = False,
    allowed_origins: list[str] | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """Async context manager producing an httpx.AsyncClient against an ASGI-mounted manager.

    Keeps manager.run() and the httpx client inside the same task scope so
    anyio's cancel-scope bookkeeping stays consistent.
    """
    mcp_server.allowed_origins = allowed_origins if allowed_origins is not None else ["*"]
    manager = HTTPSessionManager(
        server=mcp_server,
        json_response=True,
        stateless=stateless,
    )
    app = _build_asgi_app(manager)

    async with manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def _initialize(
    client: httpx.AsyncClient, protocol_version: str = "2025-11-25"
) -> tuple[dict, str]:
    resp = await client.post(
        "/mcp/",
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
    )
    assert resp.status_code == 200, resp.text
    session_id = resp.headers.get("Mcp-Session-Id")
    assert session_id is not None
    return resp.json(), session_id


# -----------------------------------------------------------------------------
# CORS preflight
# -----------------------------------------------------------------------------


class TestCORSPreflight:
    @pytest.mark.asyncio
    async def test_options_preflight_returns_204(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            resp = await client.request(
                "OPTIONS",
                "/mcp/",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )
        assert resp.status_code == 204
        assert "Access-Control-Allow-Origin" in resp.headers
        allow_methods = resp.headers.get("Access-Control-Allow-Methods", "")
        for m in ("POST", "GET", "DELETE", "OPTIONS"):
            assert m in allow_methods
        allow_headers = resp.headers.get("Access-Control-Allow-Headers", "")
        assert "Mcp-Session-Id" in allow_headers
        assert "MCP-Protocol-Version" in allow_headers
        expose = resp.headers.get("Access-Control-Expose-Headers", "")
        assert "Mcp-Session-Id" in expose
        assert "MCP-Protocol-Version" in expose


# -----------------------------------------------------------------------------
# Origin validation
# -----------------------------------------------------------------------------


class TestOriginValidation:
    @pytest.mark.asyncio
    async def test_origin_not_in_allowlist_returns_403(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server, allowed_origins=["https://good.example.com"]) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Origin": "https://evil.example.com",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
        assert resp.status_code == 403
        body = json.loads(resp.content)
        # Transport errors omit id
        assert "id" not in body
        assert body["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_origin_in_allowlist_accepted(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server, allowed_origins=["https://good.example.com"]) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Origin": "https://good.example.com",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
        assert resp.status_code != 403
        assert resp.status_code < 500

    @pytest.mark.asyncio
    async def test_no_origin_header_accepted_as_non_browser(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server, allowed_origins=["https://good.example.com"]) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    # No Origin header
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
        assert resp.status_code != 403


# -----------------------------------------------------------------------------
# Accept header validation
# -----------------------------------------------------------------------------


class TestAcceptHeaderValidation:
    @pytest.mark.asyncio
    async def test_post_without_proper_accept_returns_406(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            _, session_id = await _initialize(client, protocol_version="2025-06-18")
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "text/plain",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            )
        assert resp.status_code == 406
        body = json.loads(resp.content)
        assert "id" not in body  # transport-level error omits id
        assert body["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_initialize_must_also_advertise_both_content_types(
        self, mcp_server: MCPServer
    ) -> None:
        """Per MCP 2025-11-25 transports.mdx section 2, every client POST MUST
        include both ``application/json`` and ``text/event-stream`` in the
        Accept header -- there is no carve-out for initialize. The server
        MAY respond to initialize with an SSE stream, so the client must
        advertise support for both content types up front. An initialize
        POST missing ``text/event-stream`` gets 406 just like any other POST.
        """
        async with _http_client(mcp_server) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    # Only application/json, missing text/event-stream.
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
        assert resp.status_code == 406
        body = json.loads(resp.content)
        assert "id" not in body  # transport-level error omits id
        assert body["error"]["code"] == -32600


# -----------------------------------------------------------------------------
# MCP-Protocol-Version header
# -----------------------------------------------------------------------------


class TestProtocolVersionHeader:
    @pytest.mark.asyncio
    async def test_unsupported_version_header_returns_400(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            _, session_id = await _initialize(client, protocol_version="2025-06-18")
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                    "MCP-Protocol-Version": "1999-01-01",
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            )
        assert resp.status_code == 400
        body = json.loads(resp.content)
        assert "id" not in body  # transport error omits id

    @pytest.mark.asyncio
    async def test_stateless_requires_version_header(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server, stateless=True) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    # no MCP-Protocol-Version
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_version_header_mismatch_with_negotiated_returns_400(
        self, mcp_server: MCPServer
    ) -> None:
        """Hardening: once a session has negotiated a version, the header (if
        sent) must match it."""
        async with _http_client(mcp_server) as client:
            _, session_id = await _initialize(client, protocol_version="2025-06-18")
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                    # Send a supported but mismatched version
                    "MCP-Protocol-Version": "2025-11-25",
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            )
        assert resp.status_code == 400


# -----------------------------------------------------------------------------
# Session ID flow
# -----------------------------------------------------------------------------


class TestSessionIdFlow:
    @pytest.mark.asyncio
    async def test_missing_session_on_non_init_returns_400(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_initialize_returns_session_id(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"},
                    },
                },
            )
        assert resp.status_code == 200
        assert resp.headers.get("Mcp-Session-Id") is not None


# -----------------------------------------------------------------------------
# Full round-trip
# -----------------------------------------------------------------------------


class TestFullRoundTrip:
    @pytest.mark.asyncio
    async def test_initialize_then_tools_list(self, mcp_server: MCPServer) -> None:
        async with _http_client(mcp_server) as client:
            init, session_id = await _initialize(client, protocol_version="2025-11-25")
            assert init["result"]["protocolVersion"] == "2025-11-25"

            # Send initialized notification
            await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                },
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            list_resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            )
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert "result" in body
        assert "tools" in body["result"]

    @pytest.mark.asyncio
    async def test_negotiates_down_to_client_version(self, mcp_server: MCPServer) -> None:
        """If client sends 2025-06-18, server must reply 2025-06-18 (not latest)."""
        async with _http_client(mcp_server) as client:
            init, _ = await _initialize(client, protocol_version="2025-06-18")
        assert init["result"]["protocolVersion"] == "2025-06-18"
