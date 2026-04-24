#!/usr/bin/env python3
# ruff: noqa: S603, S607
#
# This script shells out to `git` via PATH on purpose: it runs inside
# pre-commit and GitHub Actions, both of which guarantee git on PATH, and
# hard-coding an absolute path would break portability. The subprocess
# invocations here pass only constant argv lists, so S603/S607 don't apply.
"""
Guard: the debug-exposure flags in ``arcade_mcp_server/_debug_exposure.py``
must never ship in the "on" state through committed files.

The two env vars
    ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES
    ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES
only activate when set to one specific acknowledgement string. Therefore we
only need to guarantee that string never appears in the tree outside a tiny
allowlist of files (the source that defines it, the tests that exercise it,
the developer doc, and this guard itself).

This script is run both as a pre-commit hook and as a dedicated CI workflow.

Exit codes:
  0  OK — flags cannot be activated by anything in the tree.
  1  FAIL — the magic string was found in a non-allowlisted file.
  2  Infrastructure error (e.g. ``git ls-files`` unavailable).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# The activation ack string. Kept as the sole constant so updating it in one
# place (arcade_mcp_server/_debug_exposure.py) also updates the guard.
MAGIC = "yes-i-accept-leaking-internals-to-the-agent"

# Files that are *allowed* to mention the magic string. Everything else is a
# hard fail. Paths are relative to the repository root and use forward slashes.
ALLOWLIST: frozenset[str] = frozenset({
    # The source of truth for the flags.
    "libs/arcade-mcp-server/arcade_mcp_server/_debug_exposure.py",
    # Unit tests for the pure augmentation function.
    "libs/tests/arcade_mcp_server/test_debug_exposure.py",
    # Integration tests for the MCP-boundary wire-up.
    "libs/tests/arcade_mcp_server/test_debug_exposure_integration.py",
    # Developer documentation for the flags.
    "CLAUDE.md",
    # This guard itself.
    "scripts/check_debug_leak_flags_off.py",
})


def _repo_root() -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("check_debug_leak_flags_off: not a git checkout", file=sys.stderr)
        raise SystemExit(2) from None
    return Path(out.strip())


def _tracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("check_debug_leak_flags_off: git ls-files failed", file=sys.stderr)
        raise SystemExit(2) from None
    return [line for line in out.splitlines() if line]


def main() -> int:
    root = _repo_root()
    failures: list[str] = []

    for rel in _tracked_files(root):
        if rel in ALLOWLIST:
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if MAGIC in text:
            failures.append(rel)

    if failures:
        print("Debug-leak flag guard: FAIL", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "The activation acknowledgement string for the unsafe debug-leak "
            "flags was found in files that must never contain it:",
            file=sys.stderr,
        )
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "These env vars must stay off by default everywhere the repo ships. "
            "If you need to iterate locally, export the magic value in your "
            "shell only — never commit it.",
            file=sys.stderr,
        )
        print(
            "See libs/arcade-mcp-server/arcade_mcp_server/_debug_exposure.py "
            "for the full rationale.",
            file=sys.stderr,
        )
        return 1

    print("Debug-leak flag guard: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
