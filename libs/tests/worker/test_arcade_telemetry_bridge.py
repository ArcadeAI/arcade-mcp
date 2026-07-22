"""Tests for the optional arcade-telemetry bridge in arcade-serve.

Covers both paths:
- arcade_telemetry NOT importable — OTELHandler runs its built-in OTLP setup.
- arcade_telemetry importable (simulated via sys.modules monkeypatch) —
  OTELHandler delegates provider setup and skips OTLP exporter init.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from arcade_serve.fastapi import _arcade_telemetry
from arcade_serve.fastapi.telemetry import OTELHandler
from fastapi import FastAPI


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def fake_arcade_telemetry(monkeypatch: pytest.MonkeyPatch):
    """Install a fake `arcade_telemetry` package into sys.modules.

    Yields a SimpleNamespace with the mocks the test can assert against.
    """
    telemetry_handle = MagicMock(name="Telemetry")
    new_telemetry = MagicMock(name="new_telemetry", return_value=telemetry_handle)

    fake_root = types.ModuleType("arcade_telemetry")
    fake_root.new_telemetry = new_telemetry  # type: ignore[attr-defined]

    class _FakeCorrelationMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    fake_starlette = types.ModuleType("arcade_telemetry.starlette")
    fake_starlette.CorrelationMiddleware = _FakeCorrelationMiddleware  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "arcade_telemetry", fake_root)
    monkeypatch.setitem(sys.modules, "arcade_telemetry.starlette", fake_starlette)

    return types.SimpleNamespace(
        new_telemetry=new_telemetry,
        telemetry_handle=telemetry_handle,
        correlation_middleware_cls=_FakeCorrelationMiddleware,
    )


def test_bridge_unavailable_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Make sure no stray import landed in sys.modules from a prior test.
    monkeypatch.delitem(sys.modules, "arcade_telemetry", raising=False)
    monkeypatch.delitem(sys.modules, "arcade_telemetry.starlette", raising=False)

    assert _arcade_telemetry.is_available() is False
    assert (
        _arcade_telemetry.init_providers(
            service_name="worker", environment="local", version="1.0.0", log_level=20
        )
        is None
    )
    assert _arcade_telemetry.correlation_middleware_cls() is None
    # Shutdown of None is a no-op.
    _arcade_telemetry.shutdown(None)


def test_bridge_available_when_installed(fake_arcade_telemetry) -> None:
    assert _arcade_telemetry.is_available() is True

    handle = _arcade_telemetry.init_providers(
        service_name="worker", environment="prod", version="2.3.4", log_level=10
    )
    assert handle is fake_arcade_telemetry.telemetry_handle
    fake_arcade_telemetry.new_telemetry.assert_called_once_with(
        service_name="worker", environment="prod", version="2.3.4", log_level=10
    )

    assert (
        _arcade_telemetry.correlation_middleware_cls()
        is fake_arcade_telemetry.correlation_middleware_cls
    )


def test_shutdown_calls_handle_shutdown(fake_arcade_telemetry) -> None:
    handle = _arcade_telemetry.init_providers(
        service_name="worker", environment="prod", version="1.0.0", log_level=20
    )
    _arcade_telemetry.shutdown(handle)
    fake_arcade_telemetry.telemetry_handle.shutdown.assert_called_once()


@patch("arcade_serve.fastapi.telemetry.RequestsInstrumentor")
@patch("arcade_serve.fastapi.telemetry.AioHttpClientInstrumentor")
@patch("arcade_serve.fastapi.telemetry.HTTPXClientInstrumentor")
@patch("arcade_serve.fastapi.telemetry.FastAPIInstrumentor")
@patch("arcade_serve.fastapi.telemetry.OTLPLogExporter")
@patch("arcade_serve.fastapi.telemetry.OTLPMetricExporter")
@patch("arcade_serve.fastapi.telemetry.OTLPSpanExporter")
def test_otel_handler_delegates_when_arcade_telemetry_present(
    mock_span_exporter,
    mock_metric_exporter,
    mock_log_exporter,
    mock_fastapi_instrumentor,
    mock_httpx,
    mock_aiohttp,
    mock_requests,
    fake_arcade_telemetry,
    app: FastAPI,
) -> None:
    handler = OTELHandler(enable=True, service_name="worker", service_version="9.9.9")
    handler.instrument_app(app)

    # arcade-telemetry handled provider setup — OTELHandler's OTLP exporters
    # must NOT have been constructed.
    mock_span_exporter.assert_not_called()
    mock_metric_exporter.assert_not_called()
    mock_log_exporter.assert_not_called()
    assert handler._tracer_provider is None
    assert handler._meter_provider is None
    assert handler._logger_provider is None

    # arcade-telemetry's new_telemetry() was called with the handler's values.
    fake_arcade_telemetry.new_telemetry.assert_called_once()
    kwargs = fake_arcade_telemetry.new_telemetry.call_args.kwargs
    assert kwargs["service_name"] == "worker"
    assert kwargs["version"] == "9.9.9"

    # FastAPI / HTTPX / aiohttp / Requests instrumentors still run, with
    # tracer_provider omitted so they pick up arcade-telemetry's global providers.
    mock_fastapi_instrumentor.return_value.instrument_app.assert_called_once_with(
        app, excluded_urls="/worker/health", exclude_spans=["send", "receive"]
    )
    mock_httpx.return_value._instrument.assert_called_once_with()
    mock_aiohttp.return_value._instrument.assert_called_once_with()
    mock_requests.return_value._instrument.assert_called_once_with()

    # Shutdown delegates to the arcade-telemetry handle and does NOT touch the
    # OTLP exporter shutdown path (which would crash since exporters were never
    # initialized).
    handler.shutdown()
    fake_arcade_telemetry.telemetry_handle.shutdown.assert_called_once()
    assert handler._arcade_telemetry_handle is None


def test_create_arcade_mcp_registers_correlation_middleware(
    fake_arcade_telemetry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With arcade-telemetry available AND otel_enable=True, create_arcade_mcp
    adds CorrelationMiddleware to the FastAPI app."""
    monkeypatch.setenv("MCP_SERVER_NAME", "test-mcp")
    monkeypatch.setenv("MCP_SERVER_VERSION", "0.1.0")

    from arcade_core import ToolCatalog
    from arcade_mcp_server.settings import MCPSettings
    from arcade_mcp_server.worker import create_arcade_mcp

    catalog = ToolCatalog()
    mcp_settings = MCPSettings.from_env()
    app = create_arcade_mcp(catalog, mcp_settings=mcp_settings, otel_enable=True)

    middleware_classes = [m.cls for m in app.user_middleware]
    assert fake_arcade_telemetry.correlation_middleware_cls in middleware_classes


def test_create_arcade_mcp_skips_middleware_when_otel_disabled(
    fake_arcade_telemetry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even with arcade-telemetry available, otel_enable=False must NOT add
    CorrelationMiddleware. Matches the documented behavior table — when OTel
    is off, the middleware stack must not change."""
    monkeypatch.setenv("MCP_SERVER_NAME", "test-mcp")
    monkeypatch.setenv("MCP_SERVER_VERSION", "0.1.0")

    from arcade_core import ToolCatalog
    from arcade_mcp_server.settings import MCPSettings
    from arcade_mcp_server.worker import create_arcade_mcp

    catalog = ToolCatalog()
    mcp_settings = MCPSettings.from_env()
    app = create_arcade_mcp(catalog, mcp_settings=mcp_settings, otel_enable=False)

    middleware_classes = [m.cls for m in app.user_middleware]
    assert fake_arcade_telemetry.correlation_middleware_cls not in middleware_classes


def test_create_arcade_mcp_skips_middleware_without_arcade_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without arcade-telemetry installed, no CorrelationMiddleware is added
    regardless of the otel_enable flag."""
    monkeypatch.delitem(sys.modules, "arcade_telemetry", raising=False)
    monkeypatch.delitem(sys.modules, "arcade_telemetry.starlette", raising=False)
    monkeypatch.setenv("MCP_SERVER_NAME", "test-mcp")
    monkeypatch.setenv("MCP_SERVER_VERSION", "0.1.0")

    from arcade_core import ToolCatalog
    from arcade_mcp_server.settings import MCPSettings
    from arcade_mcp_server.worker import create_arcade_mcp

    catalog = ToolCatalog()
    mcp_settings = MCPSettings.from_env()
    app = create_arcade_mcp(catalog, mcp_settings=mcp_settings)

    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CorrelationMiddleware" not in middleware_classes


@patch("arcade_serve.fastapi.telemetry.RequestsInstrumentor")
@patch("arcade_serve.fastapi.telemetry.AioHttpClientInstrumentor")
@patch("arcade_serve.fastapi.telemetry.HTTPXClientInstrumentor")
@patch("arcade_serve.fastapi.telemetry.FastAPIInstrumentor")
@patch("arcade_serve.fastapi.telemetry.OTLPLogExporter")
@patch("arcade_serve.fastapi.telemetry.OTLPMetricExporter")
@patch("arcade_serve.fastapi.telemetry.OTLPSpanExporter")
def test_otel_handler_uses_builtin_when_arcade_telemetry_absent(
    mock_span_exporter,
    mock_metric_exporter,
    mock_log_exporter,
    mock_fastapi_instrumentor,
    mock_httpx,
    mock_aiohttp,
    mock_requests,
    monkeypatch: pytest.MonkeyPatch,
    app: FastAPI,
) -> None:
    monkeypatch.delitem(sys.modules, "arcade_telemetry", raising=False)
    monkeypatch.delitem(sys.modules, "arcade_telemetry.starlette", raising=False)

    mock_span_exporter.return_value.shutdown = MagicMock()
    mock_metric_exporter.return_value.shutdown = MagicMock()
    mock_log_exporter.return_value.shutdown = MagicMock()

    handler = OTELHandler(enable=True)
    handler.instrument_app(app)

    # Built-in path constructed its own providers.
    mock_span_exporter.assert_called()
    mock_metric_exporter.assert_called()
    mock_log_exporter.assert_called()
    assert handler._tracer_provider is not None
    assert handler._meter_provider is not None
    assert handler._logger_provider is not None
    assert handler._arcade_telemetry_handle is None
