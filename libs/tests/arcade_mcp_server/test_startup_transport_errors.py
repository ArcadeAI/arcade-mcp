"""Startup transport errors must tell the developer how to fix them (#703)."""

import socket
from collections.abc import Iterator
from typing import Annotated
from unittest.mock import patch

import pytest
from arcade_mcp_server.exceptions import ServerError
from arcade_mcp_server.mcp_app import MCPApp
from arcade_mcp_server.worker import ensure_port_available, run_arcade_mcp
from loguru import logger as loguru_logger


@pytest.fixture
def occupied_port() -> Iterator[int]:
    """A port on 127.0.0.1 that another socket is listening on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        yield sock.getsockname()[1]


@pytest.fixture
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
    return port


@pytest.fixture
def mcp_app() -> MCPApp:
    app = MCPApp(name="TestApp", version="1.0.0")

    @app.tool
    def echo(message: Annotated[str, "A message"]) -> str:
        """Echo a message."""
        return message

    return app


@pytest.fixture
def captured_errors() -> Iterator[list[str]]:
    messages: list[str] = []
    sink_id = loguru_logger.add(lambda m: messages.append(m.record["message"]), level="ERROR")
    yield messages
    loguru_logger.remove(sink_id)


class TestEnsurePortAvailable:
    def test_free_port_passes(self, free_port: int) -> None:
        ensure_port_available("127.0.0.1", free_port, "Use another port: --port {port}")

    def test_occupied_port_explains_how_to_fix(self, occupied_port: int) -> None:
        with pytest.raises(ServerError) as exc_info:
            ensure_port_available("127.0.0.1", occupied_port, "Use another port: --port {port}")

        message = str(exc_info.value)
        assert f"Port {occupied_port} is already in use" in message
        assert f"127.0.0.1:{occupied_port}" in message
        assert f"Stop the other process using port {occupied_port}" in message
        assert f"Use another port: --port {occupied_port + 1}" in message
        assert "Then restart the server." in message
        # Logged to stderr at startup; a cp1252 console on Windows cannot encode non-ASCII
        assert message.isascii()

    def test_other_bind_errors_are_left_to_uvicorn(self) -> None:
        # An address that cannot be bound for a reason other than "in use"
        ensure_port_available("256.256.256.256", 8000, "Use another port: --port {port}")


class TestMCPAppPortInUse:
    def test_run_exits_with_fix_steps_when_port_in_use(
        self, mcp_app: MCPApp, occupied_port: int, captured_errors: list[str]
    ) -> None:
        with (
            patch.object(mcp_app, "_setup_logging"),
            patch.object(mcp_app, "_create_and_run_server") as mock_direct,
            patch.object(mcp_app, "_run_with_reload") as mock_reload,
            pytest.raises(SystemExit) as exc_info,
        ):
            mcp_app.run(transport="http", host="127.0.0.1", port=occupied_port)

        assert exc_info.value.code == 1
        mock_direct.assert_not_called()
        mock_reload.assert_not_called()
        message = "\n".join(captured_errors)
        assert f"Port {occupied_port} is already in use" in message
        assert f'app.run(transport="http", port={occupied_port + 1})' in message
        assert f"ARCADE_SERVER_PORT={occupied_port + 1}" in message

    def test_run_checks_port_before_starting_reload_watcher(
        self, mcp_app: MCPApp, occupied_port: int
    ) -> None:
        with (
            patch.object(mcp_app, "_setup_logging"),
            patch.object(mcp_app, "_run_with_reload") as mock_reload,
            pytest.raises(SystemExit),
        ):
            mcp_app.run(transport="http", host="127.0.0.1", port=occupied_port, reload=True)

        mock_reload.assert_not_called()

    def test_run_starts_server_when_port_free(self, mcp_app: MCPApp, free_port: int) -> None:
        with (
            patch.object(mcp_app, "_setup_logging"),
            patch.object(mcp_app, "_create_and_run_server") as mock_direct,
        ):
            mcp_app.run(transport="http", host="127.0.0.1", port=free_port)

        mock_direct.assert_called_once_with("127.0.0.1", free_port)

    def test_stdio_does_not_check_port(self, mcp_app: MCPApp) -> None:
        with (
            patch("arcade_mcp_server.mcp_app.ensure_port_available") as mock_check,
            patch("arcade_mcp_server.stdio_runner.run_stdio_server"),
            patch("arcade_mcp_server.mcp_app.asyncio.run"),
        ):
            mcp_app.run(transport="stdio")

        mock_check.assert_not_called()


class TestRunArcadeMcpPortInUse:
    def test_raises_with_cli_fix_steps_when_port_in_use(self, occupied_port: int) -> None:
        with (
            patch("arcade_mcp_server.worker.serve_with_force_quit") as mock_serve,
            patch("arcade_mcp_server.worker.uvicorn.run") as mock_uvicorn,
            pytest.raises(ServerError) as exc_info,
        ):
            run_arcade_mcp(host="127.0.0.1", port=occupied_port)

        mock_serve.assert_not_called()
        mock_uvicorn.assert_not_called()
        message = str(exc_info.value)
        assert f"Port {occupied_port} is already in use" in message
        assert f"--port {occupied_port + 1}" in message


class TestInvalidTransport:
    def test_lists_supported_transports(self, mcp_app: MCPApp, monkeypatch) -> None:
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT", raising=False)
        with patch.object(mcp_app, "_setup_logging"), pytest.raises(ServerError) as exc_info:
            mcp_app.run(transport="sse")  # type: ignore[arg-type]

        message = str(exc_info.value)
        assert "Invalid transport: 'sse'" in message
        assert "stdio" in message
        assert "http" in message
        assert 'app.run(transport="stdio")' in message
        assert "ARCADE_SERVER_TRANSPORT" not in message
        assert message.isascii()

    def test_points_at_env_var_when_transport_came_from_it(
        self, mcp_app: MCPApp, monkeypatch
    ) -> None:
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "sse")
        with patch.object(mcp_app, "_setup_logging"), pytest.raises(ServerError) as exc_info:
            mcp_app.run(transport="stdio")

        message = str(exc_info.value)
        assert "Invalid transport: 'sse'" in message
        assert "ARCADE_SERVER_TRANSPORT" in message
        assert "ARCADE_SERVER_TRANSPORT=stdio" in message
