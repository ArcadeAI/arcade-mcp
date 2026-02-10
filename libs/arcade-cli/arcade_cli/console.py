"""Shared console setup for Arcade CLI output."""

from __future__ import annotations

import os
import sys

from rich.console import Console


def _needs_utf8(encoding: str | None) -> bool:
    if not encoding:
        return True
    return encoding.lower() not in {"utf-8", "utf8"}


def _configure_windows_utf8() -> None:
    """Ensure Windows console encoding won't raise UnicodeEncodeError."""
    if sys.platform != "win32":
        return

    needs_utf8 = _needs_utf8(getattr(sys.stdout, "encoding", None)) or _needs_utf8(
        getattr(sys.stderr, "encoding", None)
    )
    if not needs_utf8:
        return

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Fall back to environment hint for child processes.
        pass

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


_configure_windows_utf8()

# Shared console used across CLI modules.
console = Console()
