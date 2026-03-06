from __future__ import annotations

import signal
import subprocess
import sys
from unittest.mock import MagicMock, patch

from arcade_core.subprocess_utils import (
    build_windows_hidden_startupinfo,
    get_windows_no_window_creationflags,
    graceful_terminate_process,
)


class _DummyStartupInfo:
    def __init__(self) -> None:
        self.dwFlags = 0
        self.wShowWindow = 1


def test_creationflags_return_zero_on_non_windows() -> None:
    with patch.object(sys, "platform", "linux"):
        assert get_windows_no_window_creationflags() == 0
        assert get_windows_no_window_creationflags(new_process_group=True) == 0


def test_creationflags_windows_include_no_window_flag() -> None:
    create_no_window = 0x08000000

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(subprocess, "CREATE_NO_WINDOW", create_no_window, create=True),
    ):
        flags = get_windows_no_window_creationflags()

    assert flags == create_no_window


def test_creationflags_windows_can_include_new_process_group() -> None:
    create_no_window = 0x08000000
    create_new_group = 0x00000200

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(subprocess, "CREATE_NO_WINDOW", create_no_window, create=True),
        patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_group, create=True),
    ):
        flags = get_windows_no_window_creationflags(new_process_group=True)

    assert flags & create_no_window
    assert flags & create_new_group


def test_hidden_startupinfo_returns_none_on_non_windows() -> None:
    with patch.object(sys, "platform", "linux"):
        assert build_windows_hidden_startupinfo() is None


def test_hidden_startupinfo_sets_sw_hide_on_windows() -> None:
    startf_use_show_window = 0x00000001

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(subprocess, "STARTUPINFO", _DummyStartupInfo, create=True),
        patch.object(subprocess, "STARTF_USESHOWWINDOW", startf_use_show_window, create=True),
    ):
        startupinfo = build_windows_hidden_startupinfo()

    assert startupinfo is not None
    assert startupinfo.wShowWindow == 0
    assert startupinfo.dwFlags & startf_use_show_window


def test_hidden_startupinfo_returns_none_if_startupinfo_missing() -> None:
    with (
        patch.object(sys, "platform", "win32"),
        patch.object(subprocess, "STARTUPINFO", None, create=True),
    ):
        assert build_windows_hidden_startupinfo() is None


def test_graceful_terminate_uses_ctrl_break_on_windows() -> None:
    ctrl_break_event = 1
    process = MagicMock()

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(signal, "CTRL_BREAK_EVENT", ctrl_break_event, create=True),
    ):
        graceful_terminate_process(process)

    process.send_signal.assert_called_once_with(ctrl_break_event)
    process.terminate.assert_not_called()


def test_graceful_terminate_falls_back_to_terminate_on_windows_signal_error() -> None:
    ctrl_break_event = 1
    process = MagicMock()
    process.send_signal.side_effect = OSError("already exited")

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(signal, "CTRL_BREAK_EVENT", ctrl_break_event, create=True),
    ):
        graceful_terminate_process(process)

    process.send_signal.assert_called_once_with(ctrl_break_event)
    process.terminate.assert_called_once()


def test_graceful_terminate_calls_terminate_on_non_windows() -> None:
    process = MagicMock()

    with patch.object(sys, "platform", "linux"):
        graceful_terminate_process(process)

    process.send_signal.assert_not_called()
    process.terminate.assert_called_once()


def test_graceful_terminate_swallows_terminate_oserror() -> None:
    process = MagicMock()
    process.terminate.side_effect = OSError("already exited")

    with patch.object(sys, "platform", "linux"):
        graceful_terminate_process(process)
