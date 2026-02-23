from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from arcade_core.subprocess_utils import (
    build_windows_hidden_startupinfo,
    get_windows_no_window_creationflags,
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
