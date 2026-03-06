"""Tests for Windows-specific subprocess flags and signal handling.

Verifies that:
- Background subprocess calls set CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP on Windows.
- graceful_terminate_process sends CTRL_BREAK_EVENT on Windows, falls back to terminate().
- MCPApp._run_with_reload shutdown uses CTRL_BREAK_EVENT on Windows.
- stdio transport registers a stdlib signal.signal fallback on Windows.

Tests that verify Windows-specific *logic* (flag construction, signal dispatch)
keep ``sys.platform`` mocking because Popen/process objects are also fully mocked.
Tests for the non-Windows path use ``pytest.mark.skipif`` instead.
"""

from __future__ import annotations

import asyncio
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Shared constants/helpers keep Windows behavior tests DRY and focused.
WIN_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
WIN_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
WIN_CTRL_BREAK_EVENT = getattr(signal, "CTRL_BREAK_EVENT", 1)


def _running_process() -> MagicMock:
    proc = MagicMock()
    proc.poll.return_value = None  # Process is running
    return proc


@contextmanager
def _patch_win32_subprocess_flags() -> Iterator[None]:
    with (
        patch.object(sys, "platform", "win32"),
        patch.object(subprocess, "CREATE_NO_WINDOW", WIN_CREATE_NO_WINDOW, create=True),
        patch.object(
            subprocess,
            "CREATE_NEW_PROCESS_GROUP",
            WIN_CREATE_NEW_PROCESS_GROUP,
            create=True,
        ),
    ):
        yield


@contextmanager
def _patch_win32_ctrl_break() -> Iterator[None]:
    with (
        patch.object(sys, "platform", "win32"),
        patch.object(signal, "CTRL_BREAK_EVENT", WIN_CTRL_BREAK_EVENT, create=True),
    ):
        yield


# ---------------------------------------------------------------------------
# deploy.py — start_server_process()
# ---------------------------------------------------------------------------


class TestDeployCreateNoWindow:
    """Verify start_server_process sets CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP on Windows."""

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_sets_flags_on_win32(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        mock_python.return_value = Path("python.exe")
        mock_popen.return_value = _running_process()

        # sys.platform mock: verifies flag-construction logic with fully-mocked Popen.
        with _patch_win32_subprocess_flags():
            from arcade_cli.deploy import start_server_process
            start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        flags = kwargs.get("creationflags", 0)
        # Both flags must be present
        assert flags & WIN_CREATE_NO_WINDOW, "CREATE_NO_WINDOW must be set"
        assert flags & WIN_CREATE_NEW_PROCESS_GROUP, "CREATE_NEW_PROCESS_GROUP must be set"

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows path: creationflags must be 0")
    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_no_creationflags_on_non_windows(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        mock_python.return_value = Path("python3")
        mock_popen.return_value = _running_process()

        from arcade_cli.deploy import start_server_process
        start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        assert kwargs.get("creationflags") == 0

    @pytest.mark.parametrize(
        ("debug", "expects_devnull"),
        [
            (False, True),
            (True, False),
        ],
        ids=["non-debug-devnull", "debug-inherits-streams"],
    )
    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_stream_configuration_by_debug_mode(
        self,
        mock_popen: MagicMock,
        mock_python: MagicMock,
        debug: bool,
        expects_devnull: bool,
    ) -> None:
        """Stream handling should switch between DEVNULL and inherited streams."""
        mock_python.return_value = Path("python.exe")
        mock_popen.return_value = _running_process()

        # sys.platform mock: verifies stream-mode logic with fully-mocked Popen.
        with _patch_win32_subprocess_flags():
            from arcade_cli.deploy import start_server_process
            start_server_process("server.py", debug=debug)

        _, kwargs = mock_popen.call_args
        if expects_devnull:
            assert kwargs.get("stdout") == subprocess.DEVNULL
            assert kwargs.get("stderr") == subprocess.DEVNULL
        else:
            assert kwargs.get("stdout") is None
            assert kwargs.get("stderr") is None


# ---------------------------------------------------------------------------
# subprocess_utils.py — graceful_terminate_process()
# ---------------------------------------------------------------------------


class TestGracefulTerminate:
    """Verify graceful_terminate_process uses CTRL_BREAK_EVENT on Windows."""

    def test_sends_ctrl_break_on_win32(self) -> None:
        """On Windows, graceful_terminate_process should send CTRL_BREAK_EVENT."""
        from arcade_core.subprocess_utils import graceful_terminate_process

        mock_proc = MagicMock()

        # sys.platform mock: verifies CTRL_BREAK_EVENT dispatch with mocked process.
        with _patch_win32_ctrl_break():
            graceful_terminate_process(mock_proc)

        # Should try send_signal with CTRL_BREAK_EVENT (not terminate)
        mock_proc.send_signal.assert_called_once_with(WIN_CTRL_BREAK_EVENT)
        mock_proc.terminate.assert_not_called()

    def test_falls_back_to_terminate_on_win32_oserror(self) -> None:
        """If send_signal fails on Windows, fall back to terminate."""
        from arcade_core.subprocess_utils import graceful_terminate_process

        mock_proc = MagicMock()
        mock_proc.send_signal.side_effect = OSError("Process exited")

        # sys.platform mock: exercises OSError fallback with mocked process.
        with _patch_win32_ctrl_break():
            graceful_terminate_process(mock_proc)

        mock_proc.terminate.assert_called_once()

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows terminate() path")
    def test_calls_terminate_on_linux(self) -> None:
        """On Linux/macOS, graceful_terminate_process should call terminate() directly."""
        from arcade_core.subprocess_utils import graceful_terminate_process

        mock_proc = MagicMock()

        graceful_terminate_process(mock_proc)

        mock_proc.terminate.assert_called_once()
        mock_proc.send_signal.assert_not_called()


# ---------------------------------------------------------------------------
# mcp_app.py — runtime behavior checks
# ---------------------------------------------------------------------------


class TestMcpAppSubprocess:
    """Verify MCPApp._run_with_reload subprocess behavior at runtime."""

    def test_shutdown_sends_ctrl_break_on_win32(self) -> None:
        """On Windows, _run_with_reload sends CTRL_BREAK_EVENT for graceful child shutdown."""
        from arcade_mcp_server.mcp_app import MCPApp

        mock_proc = MagicMock()
        mock_proc.wait.return_value = None

        # sys.platform mock: exercises Windows graceful shutdown path with mocked Popen/signal.
        with (
            _patch_win32_subprocess_flags(),
            patch.object(signal, "CTRL_BREAK_EVENT", WIN_CTRL_BREAK_EVENT, create=True),
            patch.object(subprocess, "Popen", return_value=mock_proc),
            patch("arcade_mcp_server.mcp_app.watch", side_effect=KeyboardInterrupt),
        ):
            app = MCPApp()
            app._run_with_reload("127.0.0.1", 8000)

        mock_proc.send_signal.assert_called_once_with(WIN_CTRL_BREAK_EVENT)
        mock_proc.terminate.assert_not_called()

    def test_shutdown_falls_back_to_terminate_on_win32_oserror(self) -> None:
        """On Windows, shutdown falls back to terminate() if send_signal raises OSError."""
        from arcade_mcp_server.mcp_app import MCPApp

        mock_proc = MagicMock()
        mock_proc.send_signal.side_effect = OSError("process already exited")
        mock_proc.wait.return_value = None

        # sys.platform mock: exercises OSError fallback path with mocked Popen/signal.
        with (
            _patch_win32_subprocess_flags(),
            patch.object(signal, "CTRL_BREAK_EVENT", WIN_CTRL_BREAK_EVENT, create=True),
            patch.object(subprocess, "Popen", return_value=mock_proc),
            patch("arcade_mcp_server.mcp_app.watch", side_effect=KeyboardInterrupt),
        ):
            app = MCPApp()
            app._run_with_reload("127.0.0.1", 8000)

        mock_proc.terminate.assert_called_once()

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows terminate() path")
    def test_shutdown_calls_terminate_on_non_windows(self) -> None:
        """On Linux/macOS, _run_with_reload uses terminate() for graceful child shutdown."""
        from arcade_mcp_server.mcp_app import MCPApp

        mock_proc = MagicMock()
        mock_proc.wait.return_value = None

        with (
            patch.object(subprocess, "Popen", return_value=mock_proc),
            patch("arcade_mcp_server.mcp_app.watch", side_effect=KeyboardInterrupt),
        ):
            app = MCPApp()
            app._run_with_reload("127.0.0.1", 8000)

        mock_proc.terminate.assert_called_once()
        mock_proc.send_signal.assert_not_called()


# ---------------------------------------------------------------------------
# stdio.py — signal handler fallback
# ---------------------------------------------------------------------------


class TestStdioSignalFallback:
    """Verify stdio transport registers a stdlib signal.signal fallback on Windows."""

    @pytest.mark.asyncio
    async def test_registers_stdlib_signal_handler_on_windows(self) -> None:
        """On Windows, StdioTransport.start() calls signal.signal(SIGINT, ...) as fallback."""
        import arcade_mcp_server.transports.stdio as stdio_mod
        from arcade_mcp_server.transports.stdio import StdioTransport

        transport = StdioTransport(name="test-win32-sigint")
        registered_signals: list[int] = []

        def capture_signal(signum: int, handler: object) -> None:
            registered_signals.append(signum)

        # sys.platform mock: exercises NotImplementedError fallback path that
        # only occurs on Windows when asyncio signal handlers are unavailable.
        with patch.object(sys, "platform", "win32"):
            loop = asyncio.get_running_loop()
            original_add = loop.add_signal_handler

            def raise_not_impl(*args: object, **kwargs: object) -> None:
                raise NotImplementedError

            loop.add_signal_handler = raise_not_impl  # type: ignore[assignment]
            with patch.object(stdio_mod.signal, "signal", side_effect=capture_signal):
                try:
                    await transport.start()
                finally:
                    loop.add_signal_handler = original_add  # type: ignore[assignment]
                    await transport.stop()

        assert signal.SIGINT in registered_signals, (
            "StdioTransport must register signal.signal(SIGINT, ...) on Windows "
            "as asyncio fallback; registered signals: "
            f"{registered_signals}"
        )
