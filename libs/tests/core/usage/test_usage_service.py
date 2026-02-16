from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

from arcade_core.usage.usage_service import UsageService


class _DummyStartupInfo:
    def __init__(self) -> None:
        self.dwFlags = 0
        self.wShowWindow = 1


def test_capture_windows_prefers_pythonw_and_hides_window() -> None:
    service = UsageService()

    with (
        patch("arcade_core.usage.usage_service.is_tracking_enabled", return_value=True),
        patch.object(sys, "platform", "win32"),
        patch.object(sys, "executable", r"C:\Python\python.exe"),
        patch("arcade_core.usage.usage_service.Path.exists", return_value=True),
        patch.object(subprocess, "STARTUPINFO", _DummyStartupInfo, create=True),
        patch.object(subprocess, "STARTF_USESHOWWINDOW", 0x00000001, create=True),
        patch.object(subprocess, "DETACHED_PROCESS", 0x00000008, create=True),
        patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200, create=True),
        patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True),
        patch("arcade_core.usage.usage_service.subprocess.Popen") as mock_popen,
    ):
        service.capture("event", "distinct-id", {"k": "v"})

    args, kwargs = mock_popen.call_args
    cmd = args[0]

    assert cmd[0].lower().endswith("pythonw.exe")
    assert cmd[1:] == ["-m", "arcade_core.usage"]

    flags = kwargs["creationflags"]
    assert flags & 0x00000008  # DETACHED_PROCESS
    assert flags & 0x00000200  # CREATE_NEW_PROCESS_GROUP
    assert flags & 0x08000000  # CREATE_NO_WINDOW

    startupinfo = kwargs["startupinfo"]
    assert startupinfo is not None
    assert startupinfo.wShowWindow == 0
    assert startupinfo.dwFlags & 0x00000001


def test_capture_windows_falls_back_to_python_when_pythonw_missing() -> None:
    service = UsageService()

    with (
        patch("arcade_core.usage.usage_service.is_tracking_enabled", return_value=True),
        patch.object(sys, "platform", "win32"),
        patch.object(sys, "executable", r"C:\Python\python.exe"),
        patch("arcade_core.usage.usage_service.Path.exists", return_value=False),
        patch.object(subprocess, "STARTUPINFO", _DummyStartupInfo, create=True),
        patch.object(subprocess, "STARTF_USESHOWWINDOW", 0x00000001, create=True),
        patch.object(subprocess, "DETACHED_PROCESS", 0x00000008, create=True),
        patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200, create=True),
        patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True),
        patch("arcade_core.usage.usage_service.subprocess.Popen") as mock_popen,
    ):
        service.capture("event", "distinct-id", {"k": "v"})

    args, _kwargs = mock_popen.call_args
    cmd = args[0]
    assert cmd[0] == r"C:\Python\python.exe"
    assert cmd[1:] == ["-m", "arcade_core.usage"]


def test_capture_non_windows_uses_start_new_session() -> None:
    service = UsageService()

    with (
        patch("arcade_core.usage.usage_service.is_tracking_enabled", return_value=True),
        patch.object(sys, "platform", "linux"),
        patch("arcade_core.usage.usage_service.subprocess.Popen") as mock_popen,
    ):
        service.capture("event", "distinct-id", {"k": "v"})

    _, kwargs = mock_popen.call_args
    assert kwargs["start_new_session"] is True
    assert "creationflags" not in kwargs


def test_capture_noop_when_tracking_disabled() -> None:
    service = UsageService()

    with (
        patch("arcade_core.usage.usage_service.is_tracking_enabled", return_value=False),
        patch("arcade_core.usage.usage_service.subprocess.Popen") as mock_popen,
    ):
        service.capture("event", "distinct-id", {"k": "v"})

    mock_popen.assert_not_called()

