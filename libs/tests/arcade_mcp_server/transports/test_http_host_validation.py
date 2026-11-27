"""Host header validation when the HTTP transport is bound to a loopback address.

A page on attacker.example can make the browser send requests to 127.0.0.1 by
re-resolving its own hostname (DNS rebinding). Those requests carry
``Host: attacker.example``, so a server bound to loopback rejects any Host that is
not a loopback name or explicitly allowed. Also covers the MCP_TRANSPORT_ALLOWED_ORIGINS
and MCP_TRANSPORT_ALLOWED_HOSTS settings reaching the transport, and the startup logs.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings, TransportSettings
from arcade_mcp_server.transports.http_session_manager import (
    HTTPSessionManager,
    is_loopback_host,
)
from arcade_mcp_server.worker import create_arcade_mcp
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Mount

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "0"},
    },
}
TOOLS_CALL = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "TestToolkit_sample_tool", "arguments": {}},
}


@asynccontextmanager
async def _client(
    mcp_server: MCPServer,
    *,
    bind_host: str | None,
    allowed_hosts: list[str] | None = None,
    trusted_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    mcp_server.allowed_origins = allowed_origins
    mcp_server.allowed_hosts = allowed_hosts
    manager = HTTPSessionManager(
        server=mcp_server,
        json_response=True,
        bind_host=bind_host,
        trusted_hosts=trusted_hosts,
    )
    app = Starlette(routes=[Mount("/mcp", app=manager.handle_request)])
    async with manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            yield client


async def _post(
    client: httpx.AsyncClient, host: str, *, origin: str | None = None, body: dict = INITIALIZE
) -> httpx.Response:
    headers = {**HEADERS, "Host": host}
    if origin is not None:
        headers["Origin"] = origin
    return await client.post("/mcp/", headers=headers, json=body)


def _assert_host_rejected(resp: httpx.Response) -> None:
    assert resp.status_code == 403, resp.text
    body = json.loads(resp.content)
    # Same shape as the Origin rejection: a transport error with no id.
    assert "id" not in body
    assert body["jsonrpc"] == "2.0"
    assert body["error"]["code"] == -32600
    assert body["error"]["message"].startswith("Forbidden: Host not allowed")
    # Tells the operator which setting accepts a tunnel or proxy hostname.
    assert "MCP_TRANSPORT_ALLOWED_HOSTS" in body["error"]["message"]


class TestLoopbackBind:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("bind_host", ["127.0.0.1", "localhost", "::1"])
    async def test_spoofed_host_without_origin_is_rejected(
        self, mcp_server: MCPServer, bind_host: str
    ) -> None:
        async with _client(mcp_server, bind_host=bind_host) as client:
            resp = await _post(client, "attacker.example:8000")
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    async def test_spoofed_host_cannot_call_tools(self, mcp_server: MCPServer) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            resp = await _post(
                client,
                "attacker.example",
                body=TOOLS_CALL,
            )
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    async def test_spoofed_host_is_rejected_before_the_origin_check(
        self, mcp_server: MCPServer
    ) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", allowed_origins=["http://attacker.example"]
        ) as client:
            resp = await _post(client, "attacker.example", origin="http://attacker.example")
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    async def test_spoofed_host_preflight_is_rejected(self, mcp_server: MCPServer) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            resp = await client.request(
                "OPTIONS",
                "/mcp/",
                headers={"Host": "attacker.example", "Origin": "http://attacker.example"},
            )
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "host",
        [
            "localhost",
            "localhost:8000",
            "LOCALHOST:8000",
            "127.0.0.1",
            "127.0.0.1:8000",
            "[::1]",
            "[::1]:8000",
        ],
    )
    async def test_loopback_hosts_are_accepted(self, mcp_server: MCPServer, host: str) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            resp = await _post(client, host)
        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["serverInfo"]["name"] == "Test Server"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "host",
        [
            "localhost.attacker.example",
            "127.0.0.1.attacker.example",
            "attacker.example:127",
            "0.0.0.0:8000",
        ],
    )
    async def test_lookalike_hosts_are_rejected(self, mcp_server: MCPServer, host: str) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            resp = await _post(client, host)
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    async def test_rejection_is_logged_with_the_setting_to_use(
        self, mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
    ) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            with caplog.at_level(logging.WARNING):
                await _post(client, "tunnel.example.com")
        messages = [r.getMessage() for r in caplog.records]
        assert any(
            "'tunnel.example.com'" in m and "MCP_TRANSPORT_ALLOWED_HOSTS" in m for m in messages
        ), messages


class TestNonLoopbackBind:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("bind_host", ["0.0.0.0", "::", "192.168.1.10", None])  # noqa: S104
    async def test_any_host_is_accepted(self, mcp_server: MCPServer, bind_host: str | None) -> None:
        async with _client(mcp_server, bind_host=bind_host) as client:
            resp = await _post(client, "mcp.example.com")
        assert resp.status_code == 200, resp.text


class TestAllowedHosts:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("host", ["abc.ngrok.app", "abc.ngrok.app:443", "ABC.ngrok.app"])
    async def test_entry_without_port_matches_any_port(
        self, mcp_server: MCPServer, host: str
    ) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", allowed_hosts=["abc.ngrok.app"]
        ) as client:
            resp = await _post(client, host)
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_entry_with_port_matches_only_that_port(self, mcp_server: MCPServer) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", allowed_hosts=["proxy.internal:8443"]
        ) as client:
            accepted = await _post(client, "proxy.internal:8443")
            rejected = await _post(client, "proxy.internal:9000")
        assert accepted.status_code == 200, accepted.text
        _assert_host_rejected(rejected)

    @pytest.mark.asyncio
    async def test_other_hosts_are_still_rejected(self, mcp_server: MCPServer) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", allowed_hosts=["abc.ngrok.app"]
        ) as client:
            resp = await _post(client, "attacker.example")
        _assert_host_rejected(resp)

    @pytest.mark.asyncio
    async def test_wildcard_turns_the_check_off(self, mcp_server: MCPServer) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1", allowed_hosts=["*"]) as client:
            resp = await _post(client, "attacker.example")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_trusted_hosts_are_accepted(self, mcp_server: MCPServer) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", trusted_hosts=["mcp.example.com"]
        ) as client:
            resp = await _post(client, "mcp.example.com")
        assert resp.status_code == 200, resp.text


class TestOriginBehaviorUnchanged:
    """Host validation runs first; the Origin rules behave as before."""

    @pytest.mark.asyncio
    async def test_origin_rejected_by_default_on_a_loopback_host(
        self, mcp_server: MCPServer
    ) -> None:
        async with _client(mcp_server, bind_host="127.0.0.1") as client:
            resp = await _post(client, "127.0.0.1:8000", origin="http://localhost:3000")
        assert resp.status_code == 403
        assert resp.json()["error"]["message"] == "Forbidden: Origin not allowed"

    @pytest.mark.asyncio
    async def test_listed_origin_accepted_on_a_loopback_host(self, mcp_server: MCPServer) -> None:
        async with _client(
            mcp_server, bind_host="127.0.0.1", allowed_origins=["http://localhost:3000"]
        ) as client:
            resp = await _post(client, "127.0.0.1:8000", origin="http://localhost:3000")
        assert resp.status_code == 200, resp.text
        assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


class TestStartupLogs:
    @pytest.mark.asyncio
    async def test_wildcard_origin_logs_a_warning(
        self, mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            async with _client(mcp_server, bind_host=None, allowed_origins=["*"]):
                pass
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("allowed_origins contains '*'" in m for m in warnings), warnings

    @pytest.mark.asyncio
    async def test_no_wildcard_warning_for_listed_origins(
        self, mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            async with _client(
                mcp_server, bind_host=None, allowed_origins=["http://localhost:3000"]
            ):
                pass
        assert not any("contains '*'" in r.getMessage() for r in caplog.records)

    @pytest.mark.asyncio
    async def test_loopback_bind_logs_the_accepted_hosts_and_setting(
        self, mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            async with _client(mcp_server, bind_host="127.0.0.1", allowed_hosts=["a.example"]):
                pass
        messages = [r.getMessage() for r in caplog.records]
        assert any(
            "127.0.0.1" in m and "a.example" in m and "MCP_TRANSPORT_ALLOWED_HOSTS" in m
            for m in messages
        ), messages

    @pytest.mark.asyncio
    async def test_wildcard_host_logs_a_warning(
        self, mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            async with _client(mcp_server, bind_host="127.0.0.1", allowed_hosts=["*"]):
                pass
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Host header validation is off" in m for m in warnings), warnings


class TestIsLoopbackHost:
    @pytest.mark.parametrize(
        "host", ["localhost", "LocalHost", "127.0.0.1", "127.1.2.3", "::1", "[::1]"]
    )
    def test_loopback(self, host: str) -> None:
        assert is_loopback_host(host)

    @pytest.mark.parametrize(
        "host",
        ["0.0.0.0", "::", "", "192.168.1.10", "example.com", "localhost.example"],  # noqa: S104
    )
    def test_not_loopback(self, host: str) -> None:
        assert not is_loopback_host(host)


class TestSettingsReachTheTransport:
    def test_allowed_hosts_env_var_is_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_HOSTS", "abc.ngrok.app, proxy.internal:8443")
        assert TransportSettings().allowed_hosts == ["abc.ngrok.app", "proxy.internal:8443"]

    def test_env_vars_reach_the_server(self, tool_catalog, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_ORIGINS", "http://localhost:3000")
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_HOSTS", "abc.ngrok.app")
        server = MCPServer(catalog=tool_catalog, settings=MCPSettings())
        assert server.allowed_origins == ["http://localhost:3000"]
        assert server.allowed_hosts == ["abc.ngrok.app"]

    def test_arguments_override_env_vars(
        self, tool_catalog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_ORIGINS", "http://localhost:3000")
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_HOSTS", "abc.ngrok.app")
        server = MCPServer(
            catalog=tool_catalog,
            settings=MCPSettings(),
            allowed_origins=["https://app.example.com"],
            allowed_hosts=["proxy.internal"],
        )
        assert server.allowed_origins == ["https://app.example.com"]
        assert server.allowed_hosts == ["proxy.internal"]

    @pytest.mark.asyncio
    async def test_allowed_origins_env_var_takes_effect(
        self, tool_catalog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCP_TRANSPORT_ALLOWED_ORIGINS", "http://localhost:3000")
        server = MCPServer(catalog=tool_catalog, name="Env Server", settings=MCPSettings())
        await server.start()
        try:
            manager = HTTPSessionManager(server=server, json_response=True)
            app = Starlette(routes=[Mount("/mcp", app=manager.handle_request)])
            async with manager.run():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://127.0.0.1"
                ) as client:
                    resp = await client.post(
                        "/mcp/",
                        headers={**HEADERS, "Origin": "http://localhost:3000"},
                        json=INITIALIZE,
                    )
        finally:
            await server.stop()
        assert resp.status_code == 200, resp.text


class TestCreateArcadeMcp:
    """The integrated app: /mcp is checked, the worker routes are not."""

    @staticmethod
    def _settings() -> MCPSettings:
        settings = MCPSettings()
        settings.arcade.server_secret = "test-worker-secret"  # noqa: S105
        return settings

    def test_spoofed_host_is_rejected_on_mcp_only(self, tool_catalog) -> None:
        app = create_arcade_mcp(tool_catalog, mcp_settings=self._settings(), bind_host="127.0.0.1")
        with TestClient(app, base_url="http://127.0.0.1:8000") as client:
            spoofed = client.post(
                "/mcp/", headers={**HEADERS, "Host": "attacker.example"}, json=INITIALIZE
            )
            loopback = client.post("/mcp/", headers=HEADERS, json=INITIALIZE)
            # The Arcade Engine reaches /worker/* under its own hostname; those routes
            # are JWT-protected and keep accepting any Host.
            worker = client.get("/worker/health", headers={"Host": "worker.example.com"})
        _assert_host_rejected(spoofed)
        assert loopback.status_code == 200, loopback.text
        assert worker.status_code == 200, worker.text

    def test_without_bind_host_no_host_check(self, tool_catalog) -> None:
        app = create_arcade_mcp(tool_catalog, mcp_settings=self._settings())
        with TestClient(app) as client:
            resp = client.post(
                "/mcp/", headers={**HEADERS, "Host": "mcp.example.com"}, json=INITIALIZE
            )
        assert resp.status_code == 200, resp.text

    def test_canonical_url_host_is_accepted(
        self, tool_catalog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A server that declared its public URL (e.g. a tunnel) accepts that hostname."""
        import arcade_mcp_server.worker as worker_module

        class _Validator:
            canonical_url = "https://abc.ngrok.app/mcp"

            def supports_oauth_discovery(self) -> bool:
                return False

        # Token checks are not the subject here; let requests through to the transport.
        monkeypatch.setattr(worker_module, "ResourceServerMiddleware", lambda app, *a, **k: app)
        app = create_arcade_mcp(
            tool_catalog,
            mcp_settings=self._settings(),
            bind_host="127.0.0.1",
            resource_server_validator=_Validator(),  # type: ignore[arg-type]
        )
        with TestClient(app, base_url="http://127.0.0.1:8000") as client:
            canonical = client.post(
                "/mcp/", headers={**HEADERS, "Host": "abc.ngrok.app"}, json=INITIALIZE
            )
            other = client.post(
                "/mcp/", headers={**HEADERS, "Host": "attacker.example"}, json=INITIALIZE
            )
        assert canonical.status_code == 200, canonical.text
        _assert_host_rejected(other)


class TestBindHostPlumbing:
    def test_run_arcade_mcp_passes_the_bind_host_to_the_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``arcade mcp http`` / ``python -m arcade_mcp_server`` builds the app in a factory."""
        import arcade_mcp_server.worker as worker_module

        calls: dict = {}

        def _fake_create(**kwargs):
            calls.update(kwargs)
            return object()

        async def _fake_serve(**kwargs):
            return None

        class _Catalog(list):
            """One stand-in tool, so the factory gets past its zero-tools guard."""

            resources = ()

        monkeypatch.setattr(worker_module, "discover_tools", lambda **kw: _Catalog([object()]))
        monkeypatch.setattr(worker_module, "setup_logging", lambda **kw: None)
        monkeypatch.setattr(worker_module, "create_arcade_mcp", _fake_create)
        monkeypatch.setattr(worker_module, "serve_with_force_quit", _fake_serve)

        worker_module.run_arcade_mcp(host="127.0.0.1", port=8123)
        assert calls["bind_host"] == "127.0.0.1"
