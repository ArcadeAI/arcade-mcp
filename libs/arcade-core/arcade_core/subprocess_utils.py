"""Shared Windows subprocess helpers used across Arcade libraries."""

from __future__ import annotations

import contextlib
import signal
import subprocess
import sys
from typing import Any


def get_windows_no_window_creationflags(*, new_process_group: bool = False) -> int:
    """Return Windows creation flags to suppress phantom console windows.

    Args:
        new_process_group: When true, include ``CREATE_NEW_PROCESS_GROUP`` to
            allow graceful ``CTRL_BREAK_EVENT`` signaling.

    Returns:
        A bitmask of subprocess creation flags on Windows, otherwise ``0``.
    """
    if sys.platform != "win32":
        return 0

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    if new_process_group:
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    return flags


def build_windows_hidden_startupinfo() -> Any | None:
    """Create a Windows ``STARTUPINFO`` configured with ``SW_HIDE``.

    Returns:
        A configured ``STARTUPINFO`` instance on Windows when available,
        otherwise ``None``.
    """
    if sys.platform != "win32":
        return None

    startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_cls is None:
        return None

    startupinfo = startupinfo_cls()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
    startupinfo.wShowWindow = 0
    return startupinfo


def graceful_terminate_process(process: subprocess.Popen[Any]) -> None:
    """Terminate a process with Windows-friendly graceful fallback behavior.

    On Windows, try ``CTRL_BREAK_EVENT`` first (when supported) so child
    processes can exit cleanly. If signaling fails, fall back to
    ``process.terminate()``. Any ``OSError`` during termination is swallowed
    because the process may already have exited.
    """
    if sys.platform == "win32":
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        except (OSError, AttributeError):
            pass
        else:
            return

    with contextlib.suppress(OSError):
        process.terminate()
