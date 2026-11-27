"""Host validation through the public ways of starting an HTTP server.

Each test builds the real FastAPI app the way ``MCPApp.run(transport="http")``,
``run_arcade_mcp`` (``arcade mcp http``) or ``create_arcade_mcp`` under the caller's own
uvicorn would, captures it instead of serving it, and sends ``initialize`` under a foreign
Host. Only names that already existed before Host validation are imported, so this file
also runs against the old code, where the spoofed request succeeds.
"""

from typing import Annotated, Any

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server import MCPApp
from arcade_mcp_server import mcp_app as mcp_app_module
from arcade_mcp_server import worker as worker_module
from arcade_mcp_server.worker import create_arcade_mcp
from arcade_tdk import tool
from fastapi.testclient import TestClient

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


@tool
def echo(text: Annotated[str, "Text to echo"]) -> str:
    """Echo text."""
    return text


def _catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    catalog.add_tool(echo, "EntryKit")
    return catalog


def _initialize(app: Any, host: str) -> int:
    # The base URL is the connection's local address; the server listens on loopback.
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        resp = client.post("/mcp/", headers={**HEADERS, "Host": host}, json=INITIALIZE)
    return resp.status_code


@pytest.fixture(autouse=True)
def _clean_server_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ARCADE_SERVER_HOST",
        "ARCADE_SERVER_PORT",
        "ARCADE_SERVER_TRANSPORT",
        "ARCADE_SERVER_RELOAD",
        "ARCADE_MCP_CHILD_PROCESS",
        "MCP_TRANSPORT_ALLOWED_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)


def _app_from_mcpapp_run(monkeypatch: pytest.MonkeyPatch, host: str, **app_kwargs: Any) -> Any:
    captured: dict[str, Any] = {}

    async def _capture(*, app: Any, **_: Any) -> None:
        captured["app"] = app

    monkeypatch.setattr(mcp_app_module, "serve_with_force_quit", _capture)
    monkeypatch.setattr(MCPApp, "_setup_logging", lambda *a, **k: None)
    app = MCPApp(name="EntryApp", version="1.0.0", **app_kwargs)
    app.add_tool(echo)
    app.run(transport="http", host=host, port=8000)
    return captured["app"]


class TestMCPAppRun:
    def test_spoofed_host_is_refused_on_a_loopback_bind(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = _app_from_mcpapp_run(monkeypatch, "127.0.0.1")
        assert _initialize(app, "attacker.example") == 403
        assert _initialize(app, "localhost:8000") == 200

    def test_non_loopback_bind_is_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app = _app_from_mcpapp_run(monkeypatch, "0.0.0.0")  # noqa: S104
        assert _initialize(app, "attacker.example") == 200

    def test_allowed_hosts_lets_a_tunnel_host_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = _app_from_mcpapp_run(monkeypatch, "127.0.0.1", allowed_hosts=["abc.ngrok.app"])
        assert _initialize(app, "abc.ngrok.app") == 200
        assert _initialize(app, "attacker.example") == 403


class TestRunArcadeMcp:
    """``arcade mcp http`` / ``python -m arcade_mcp_server http``."""

    def test_spoofed_host_is_refused_on_a_loopback_bind(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        async def _capture(*, app: Any, **_: Any) -> None:
            captured["app"] = app

        monkeypatch.setattr(worker_module, "discover_tools", lambda **_: _catalog())
        monkeypatch.setattr(worker_module, "setup_logging", lambda **_: None)
        monkeypatch.setattr(worker_module, "serve_with_force_quit", _capture)
        worker_module.run_arcade_mcp(host="127.0.0.1", port=8000)

        assert _initialize(captured["app"], "attacker.example") == 403
        assert _initialize(captured["app"], "127.0.0.1:8000") == 200


class TestCreateArcadeMcpUnderOwnUvicorn:
    """``create_arcade_mcp(...)`` then ``uvicorn.run(app, host="127.0.0.1")``."""

    def test_spoofed_host_is_refused_on_a_loopback_connection(self) -> None:
        app = create_arcade_mcp(_catalog())
        assert _initialize(app, "attacker.example") == 403
        assert _initialize(app, "[::1]:8000") == 200
