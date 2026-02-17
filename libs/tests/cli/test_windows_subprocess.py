"""Tests for Windows-specific subprocess flags and signal handling.

Verifies that:
- Background subprocess calls set CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP on Windows.
- _graceful_terminate sends CTRL_BREAK_EVENT on Windows, falls back to terminate().
- mcp_app.py shutdown_server_process also uses CTRL_BREAK_EVENT on Windows.
- stdio transport registers a stdlib signal.signal fallback on Windows.
"""

from __future__ import annotations

import inspect
import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_proc

        # On non-Windows, CREATE_NO_WINDOW doesn't exist; patch deploy's subprocess
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        create_new_pg = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

        with patch.object(sys, "platform", "win32"):
            with patch.object(
                subprocess, "CREATE_NO_WINDOW", create_no_window, create=True
            ), patch.object(
                subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_pg, create=True
            ):
                from arcade_cli.deploy import start_server_process
                start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        flags = kwargs.get("creationflags", 0)
        # Both flags must be present
        assert flags & create_no_window, "CREATE_NO_WINDOW must be set"
        assert flags & create_new_pg, "CREATE_NEW_PROCESS_GROUP must be set"

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_no_creationflags_on_non_windows(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        mock_python.return_value = Path("python3")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        with patch.object(sys, "platform", "linux"):
            from arcade_cli.deploy import start_server_process
            start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        assert kwargs.get("creationflags") == 0

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_non_debug_uses_devnull_streams(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        """Non-debug startup should avoid PIPE deadlocks by using DEVNULL."""
        mock_python.return_value = Path("python.exe")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        create_new_pg = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

        with patch.object(sys, "platform", "win32"):
            with patch.object(
                subprocess, "CREATE_NO_WINDOW", create_no_window, create=True
            ), patch.object(
                subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_pg, create=True
            ):
                from arcade_cli.deploy import start_server_process
                start_server_process("server.py", debug=False)

        _, kwargs = mock_popen.call_args
        assert kwargs.get("stdout") == subprocess.DEVNULL
        assert kwargs.get("stderr") == subprocess.DEVNULL

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_debug_inherits_parent_streams(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        """Debug startup should inherit parent streams for live logs."""
        mock_python.return_value = Path("python.exe")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        create_new_pg = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

        with patch.object(sys, "platform", "win32"):
            with patch.object(
                subprocess, "CREATE_NO_WINDOW", create_no_window, create=True
            ), patch.object(
                subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_pg, create=True
            ):
                from arcade_cli.deploy import start_server_process
                start_server_process("server.py", debug=True)

        _, kwargs = mock_popen.call_args
        assert kwargs.get("stdout") is None
        assert kwargs.get("stderr") is None


# ---------------------------------------------------------------------------
# deploy.py — _graceful_terminate()
# ---------------------------------------------------------------------------


class TestGracefulTerminate:
    """Verify _graceful_terminate uses CTRL_BREAK_EVENT on Windows."""

    def test_sends_ctrl_break_on_win32(self) -> None:
        """On Windows, _graceful_terminate should send CTRL_BREAK_EVENT."""
        from arcade_cli.deploy import _graceful_terminate

        mock_proc = MagicMock()

        # On non-Windows, CTRL_BREAK_EVENT doesn't exist; provide constant
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", 1)

        with patch.object(sys, "platform", "win32"):
            with patch.object(signal, "CTRL_BREAK_EVENT", ctrl_break, create=True):
                _graceful_terminate(mock_proc)

        # Should try send_signal with CTRL_BREAK_EVENT (not terminate)
        mock_proc.send_signal.assert_called_once_with(ctrl_break)
        mock_proc.terminate.assert_not_called()

    def test_falls_back_to_terminate_on_win32_oserror(self) -> None:
        """If send_signal fails on Windows, fall back to terminate."""
        from arcade_cli.deploy import _graceful_terminate

        mock_proc = MagicMock()
        mock_proc.send_signal.side_effect = OSError("Process exited")

        with patch.object(sys, "platform", "win32"):
            _graceful_terminate(mock_proc)

        mock_proc.terminate.assert_called_once()

    def test_calls_terminate_on_linux(self) -> None:
        """On Linux/macOS, _graceful_terminate should call terminate() directly."""
        from arcade_cli.deploy import _graceful_terminate

        mock_proc = MagicMock()

        with patch.object(sys, "platform", "linux"):
            _graceful_terminate(mock_proc)

        mock_proc.terminate.assert_called_once()
        mock_proc.send_signal.assert_not_called()


# ---------------------------------------------------------------------------
# mcp_app.py — source-level checks
# ---------------------------------------------------------------------------


class TestMcpAppSubprocess:
    """Verify mcp_app.py subprocess patterns at the source level."""

    def test_has_create_no_window(self) -> None:
        """Source must contain CREATE_NO_WINDOW."""
        import arcade_mcp_server.mcp_app as mcp_mod
        source = inspect.getsource(mcp_mod)
        assert "CREATE_NO_WINDOW" in source

    def test_has_create_new_process_group(self) -> None:
        """Source must contain CREATE_NEW_PROCESS_GROUP for CTRL_BREAK_EVENT support."""
        import arcade_mcp_server.mcp_app as mcp_mod
        source = inspect.getsource(mcp_mod)
        assert "CREATE_NEW_PROCESS_GROUP" in source

    def test_has_ctrl_break_event(self) -> None:
        """Source must use CTRL_BREAK_EVENT for graceful shutdown on Windows."""
        import arcade_mcp_server.mcp_app as mcp_mod
        source = inspect.getsource(mcp_mod)
        assert "CTRL_BREAK_EVENT" in source

    def test_checks_platform(self) -> None:
        """Source must check sys.platform before setting Windows flags."""
        import arcade_mcp_server.mcp_app as mcp_mod
        source = inspect.getsource(mcp_mod)
        assert 'sys.platform == "win32"' in source or "sys.platform == 'win32'" in source


# ---------------------------------------------------------------------------
# stdio.py — signal handler fallback
# ---------------------------------------------------------------------------


class TestStdioSignalFallback:
    """Verify stdio transport registers a stdlib signal handler on Windows."""

    def test_has_signal_signal_fallback(self) -> None:
        """Source must contain signal.signal(SIGINT, ...) fallback for Windows."""
        import arcade_mcp_server.transports.stdio as stdio_mod
        source = inspect.getsource(stdio_mod)
        assert "signal.signal" in source, (
            "stdio.py should register a stdlib signal handler as Windows fallback"
        )
        assert "signal.SIGINT" in source, (
            "stdio.py should register the fallback for SIGINT"
        )

    def test_suppresses_windows_signal_support_message(self) -> None:
        """Source should suppress noisy Windows signal-support messages."""
        import arcade_mcp_server.transports.stdio as stdio_mod
        source = inspect.getsource(stdio_mod)
        assert "Windows does not support asyncio signal handlers" not in source, (
            "stdio.py should not emit this user-facing Windows support message"
        )
