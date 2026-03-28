"""Integration tests for MCPApp.include_router() with TestClient."""

from arcade_core import ToolCatalog
from arcade_core.toolkit import Toolkit
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.worker import create_arcade_mcp
from fastapi import APIRouter
from fastapi.testclient import TestClient


def _make_catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    toolkit = Toolkit(name="test", package_name="test", version="0.1.0", description="Test toolkit")
    catalog.add_toolkit(toolkit)
    return catalog


def test_extra_router_endpoint_reachable(monkeypatch):
    """GET /healthz returns 200."""
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")

    router = APIRouter()

    @router.get("/healthz")
    def healthz():
        return {"status": "ok"}

    app = create_arcade_mcp(
        _make_catalog(),
        mcp_settings=MCPSettings.from_env(),
        extra_routers=[(router, {})],
    )
    client = TestClient(app)

    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_extra_router_with_prefix(monkeypatch):
    """Router with prefix="/custom", GET /custom/check returns 200, GET /check returns 404."""
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")

    router = APIRouter()

    @router.get("/check")
    def check():
        return {"ok": True}

    app = create_arcade_mcp(
        _make_catalog(),
        mcp_settings=MCPSettings.from_env(),
        extra_routers=[(router, {"prefix": "/custom"})],
    )
    client = TestClient(app)

    assert client.get("/custom/check").status_code == 200
    assert client.get("/check").status_code == 404


def test_multiple_extra_routers(monkeypatch):
    """Two routers both reachable."""
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")

    r1 = APIRouter()
    r2 = APIRouter()

    @r1.get("/ping")
    def ping():
        return "pong"

    @r2.get("/version")
    def version():
        return "1.0"

    app = create_arcade_mcp(
        _make_catalog(),
        mcp_settings=MCPSettings.from_env(),
        extra_routers=[(r1, {}), (r2, {})],
    )
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/version").status_code == 200


def test_no_extra_routers_backward_compatible(monkeypatch):
    """extra_routers=None, /mcp/ still accessible."""
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")

    app = create_arcade_mcp(
        _make_catalog(),
        mcp_settings=MCPSettings.from_env(),
        extra_routers=None,
    )
    client = TestClient(app)

    # /mcp/ mount should still exist
    mounts = [route for route in app.routes if hasattr(route, "app") and hasattr(route, "path")]
    mcp_mounts = [m for m in mounts if m.path == "/mcp"]
    assert len(mcp_mounts) == 1


def test_extra_router_in_openapi(monkeypatch):
    """Custom endpoint appears in OpenAPI schema."""
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")

    router = APIRouter(tags=["Custom"])

    @router.get("/healthz")
    def healthz():
        return {"status": "ok"}

    app = create_arcade_mcp(
        _make_catalog(),
        mcp_settings=MCPSettings.from_env(),
        extra_routers=[(router, {})],
    )
    client = TestClient(app)

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/healthz" in schema["paths"]
