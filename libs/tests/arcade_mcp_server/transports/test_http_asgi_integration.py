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
    json_response: bool = True,
    resource_owner_factory: object | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """Async context manager producing an httpx.AsyncClient against an ASGI-mounted manager.

    Keeps manager.run() and the httpx client inside the same task scope so
    anyio's cancel-scope bookkeeping stays consistent.

    ``json_response=False`` opts into SSE response mode.
    ``resource_owner_factory`` (when supplied) is invoked per request and the
    return value is stored on the ASGI scope under ``"resource_owner"``,
    matching what the resource-server middleware would do in production.
    """
    mcp_server.allowed_origins = allowed_origins if allowed_origins is not None else ["*"]
    manager = HTTPSessionManager(
        server=mcp_server,
        json_response=json_response,
        stateless=stateless,
    )

    async def mcp_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        if resource_owner_factory is not None:
            scope["resource_owner"] = resource_owner_factory()  # type: ignore[operator]
        await manager.handle_request(scope, receive, send)

    app = Starlette(routes=[Mount("/mcp", app=mcp_endpoint)])

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
    async def test_stateless_non_initialize_missing_header_uses_backcompat(
        self, mcp_server: MCPServer
    ) -> None:
        """Spec backcompat: a stateless non-initialize POST without the
        MCP-Protocol-Version header must NOT 400. The server assumes
        2025-03-26 and dispatches the request.

        Per MCP 2025-11-25 transports.mdx:276-279.
        """
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
        # Spec requires the request to be processed, not rejected at transport.
        assert resp.status_code != 400

    @pytest.mark.asyncio
    async def test_stateless_initialize_without_header_is_accepted(
        self, mcp_server: MCPServer
    ) -> None:
        """Stateless initialize MUST be exempt from the header check.

        Initialize carries params.protocolVersion so the header is
        redundant; blocking it would prevent negotiation.
        """
        async with _http_client(mcp_server, stateless=True) as client:
            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    # no MCP-Protocol-Version
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "0"},
                    },
                },
            )
        assert resp.status_code != 400

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


# -----------------------------------------------------------------------------
# SSE 403 / WWW-Authenticate short-circuit for INSUFFICIENT_SCOPE
# -----------------------------------------------------------------------------


class TestSSEInsufficientScopeShortCircuit:
    """SSE response mode must redirect insufficient_scope errors through the
    JSON path so the client receives HTTP 403 + WWW-Authenticate (RFC 9728
    PRM scope step-up).

    The SSE channel commits to 200 text/event-stream as soon as it opens; the
    HTTP status and WWW-Authenticate header cannot be changed after that.
    Detecting the error before opening the stream is the only conformant
    path."""

    @staticmethod
    def _low_priv_owner_factory():
        from arcade_mcp_server.resource_server.base import ResourceOwner

        return ResourceOwner(
            user_id="alice",
            granted_scopes=frozenset({"files:read"}),
            claims={
                "scope": "files:read",
                "iss": "https://auth.example.com",
                "sub": "alice",
            },
        )

    @staticmethod
    async def _sse_initialize(client: httpx.AsyncClient) -> str:
        """Initialize handshake when the server is in SSE mode.

        Returns the negotiated session id. The initialize response itself
        arrives as a single SSE event, not raw JSON.
        """
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
        assert resp.status_code == 200, resp.text
        session_id = resp.headers.get("Mcp-Session-Id")
        assert session_id is not None
        return session_id

    @pytest.mark.asyncio
    async def test_sse_path_insufficient_scope_returns_json_403_with_www_authenticate(
        self, mcp_server: MCPServer
    ) -> None:
        """SSE mode + insufficient scope must reply HTTP 403 with WWW-Authenticate,
        not a 200 SSE stream."""
        async with _http_client(
            mcp_server,
            json_response=False,
            resource_owner_factory=self._low_priv_owner_factory,
        ) as client:
            session_id = await self._sse_initialize(client)
            await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                },
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            resp = await client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": session_id,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "TestToolkit.scoped_tool",
                        "arguments": {"text": "x"},
                    },
                },
            )

        assert resp.status_code == 403
        assert "WWW-Authenticate" in resp.headers
        assert 'error="insufficient_scope"' in resp.headers["WWW-Authenticate"]
        # The response body must NOT be SSE event-stream framing.
        assert "text/event-stream" not in resp.headers.get("Content-Type", "")
        body = resp.json()
        # _transport metadata must be stripped from the client-facing body.
        assert "_transport" not in body.get("error", {}).get("data", {})

    @pytest.mark.asyncio
    async def test_sse_path_succeeds_for_normally_authorized_call(
        self, mcp_server: MCPServer
    ) -> None:
        """Regression guard: the SSE peek-and-route must not short-circuit
        responses that are NOT INSUFFICIENT_SCOPE_ERROR_CODE. A normal SSE
        response continues to stream as text/event-stream."""

        def full_priv_owner_factory():
            from arcade_mcp_server.resource_server.base import ResourceOwner

            return ResourceOwner(
                user_id="alice",
                granted_scopes=frozenset({"files:read", "files:write"}),
                claims={
                    "scope": "files:read files:write",
                    "iss": "https://auth.example.com",
                    "sub": "alice",
                },
            )

        async with _http_client(
            mcp_server,
            json_response=False,
            resource_owner_factory=full_priv_owner_factory,
        ) as client:
            session_id = await self._sse_initialize(client)
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

        # In SSE mode a successful response is delivered as an event stream.
        assert list_resp.status_code == 200
        assert "text/event-stream" in list_resp.headers.get("Content-Type", "")
