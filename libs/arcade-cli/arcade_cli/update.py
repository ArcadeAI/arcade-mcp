"""Logic for the `arcade update` / `arcade upgrade` CLI command."""

from __future__ import annotations

import contextlib
import dataclasses
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from importlib import metadata
from urllib.request import urlopen

from arcade_core.constants import ARCADE_CONFIG_PATH
from arcade_core.subprocess_utils import (
    build_windows_hidden_startupinfo,
    get_windows_no_window_creationflags,
)
from packaging.version import Version

from arcade_cli.console import console

logger = logging.getLogger(__name__)

PACKAGE_NAME = "arcade-mcp"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
# Pattern to match PACKAGE_NAME exactly (not as a prefix of e.g. "arcade-mcp-server")
_PACKAGE_RE = re.compile(rf"(?:^|\s){re.escape(PACKAGE_NAME)}(?:\s|$)", re.MULTILINE)

UPDATE_CACHE_PATH = os.path.join(ARCADE_CONFIG_PATH, "update_cache.json")
# Minimum interval between background PyPI version checks
CHECK_INTERVAL_SECONDS = 4 * 60 * 60  # 4 hours


# ---------------------------------------------------------------------------
# Update cache dataclass and I/O
# ---------------------------------------------------------------------------


@dataclass
class UpdateCache:
    latest_version: str
    checked_at: float  # time.time()


def read_update_cache(cache_path: str) -> UpdateCache | None:
    """Read the update cache from disk. Returns None if missing or corrupt."""
    try:
        with open(cache_path) as f:
            data = json.load(f)
        # Only extract fields defined on UpdateCache so schema changes stay in sync
        fields = {f.name for f in dataclasses.fields(UpdateCache)}
        return UpdateCache(**{k: data[k] for k in fields})
    except Exception:
        return None


def write_update_cache(cache_path: str, cache: UpdateCache) -> None:
    """Write the update cache to disk."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(dataclasses.asdict(cache), f)


def should_check_for_update(cache: UpdateCache | None) -> bool:
    """Determine whether a background PyPI check is needed."""
    if os.environ.get("ARCADE_DISABLE_AUTOUPDATE") == "1":
        return False
    if cache is None:
        return True
    return (time.time() - cache.checked_at) > CHECK_INTERVAL_SECONDS


def fork_background_check() -> None:
    """Spawn a detached process that checks PyPI and writes the cache."""
    cache = read_update_cache(UPDATE_CACHE_PATH)
    if not should_check_for_update(cache):
        return
    cmd = [
        sys.executable,
        "-c",
        "from arcade_cli.update import _background_check; _background_check()",
    ]
    with contextlib.suppress(Exception):
        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=get_windows_no_window_creationflags(new_process_group=True),
                startupinfo=build_windows_hidden_startupinfo(),
                close_fds=True,
            )
        else:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )


def _background_check() -> None:
    """Entry point for the detached background process. Fetches PyPI, writes cache.

    Always updates ``checked_at`` so that failed checks don't bypass the throttle
    and spawn a new background process on every CLI invocation.
    """
    latest = fetch_latest_pypi_version()
    # Preserve the previously cached version when the fetch fails
    existing = read_update_cache(UPDATE_CACHE_PATH)
    cached_version = latest or (existing.latest_version if existing else "")
    write_update_cache(
        UPDATE_CACHE_PATH, UpdateCache(latest_version=cached_version, checked_at=time.time())
    )


def check_and_notify() -> None:
    """Read cache, print notification if update available, fork background check."""
    if os.environ.get("ARCADE_DISABLE_AUTOUPDATE") == "1":
        return
    cache = read_update_cache(UPDATE_CACHE_PATH)
    if cache:
        try:
            cached_version = Version(cache.latest_version)
            if cached_version > Version(metadata.version(PACKAGE_NAME)):
                console.print(
                    f"Update available: {metadata.version(PACKAGE_NAME)} → {cache.latest_version}  "
                    f"Run `arcade update` to upgrade.",
                    style="yellow",
                )
        except Exception:
            logger.debug("Failed to check cached update version", exc_info=True)
    fork_background_check()


class InstallMethod(str, Enum):
    UV_TOOL = "uv_tool"
    PIPX = "pipx"
    UV_PIP = "uv_pip"
    PIP = "pip"


def fetch_latest_pypi_version() -> str | None:
    """Query PyPI for the latest stable version of the package.

    Returns None only if the fetch fails or no stable version exists.
    If ``data["info"]["version"]`` is a stable, non-yanked release it is returned
    immediately.  Otherwise falls back to scanning all releases for the highest
    stable, non-yanked version.
    """
    try:
        with urlopen(PYPI_URL, timeout=5) as resp:  # noqa: S310
            if resp.status != 200:
                return None
            data = json.loads(resp.read())
            latest: str = data["info"]["version"]
            releases = data.get("releases", {})
            latest_files = releases.get(latest, [])
            # Return immediately only if stable AND not yanked
            if (
                not Version(latest).is_prerelease
                and latest_files
                and not all(f.get("yanked", False) for f in latest_files)
            ):
                return latest
            # Scan releases for the newest stable, non-yanked version
            releases = data.get("releases", {})
            stable_versions: list[Version] = []
            for v, files in releases.items():
                with contextlib.suppress(Exception):
                    parsed = Version(v)
                    if parsed.is_prerelease:
                        continue
                    # Skip yanked releases (all files marked yanked, or no files)
                    if not files or all(f.get("yanked", False) for f in files):
                        continue
                    stable_versions.append(parsed)
            if not stable_versions:
                return None
            return str(max(stable_versions))
    except Exception:
        return None


def detect_install_method() -> InstallMethod:
    """Auto-detect how the user originally installed the CLI.

    Detection order:
    1. uv tool — check ``uv tool list`` for the package
    2. pipx — check ``pipx list`` for the package
    3. uv pip — if ``uv`` is on PATH but the package wasn't installed via uv tool
    4. pip — fallback
    """
    if shutil.which("uv"):
        try:
            result = subprocess.run(
                ["uv", "tool", "list"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and _PACKAGE_RE.search(result.stdout):
                return InstallMethod.UV_TOOL
        except Exception:
            logger.debug("Failed to check uv tool list", exc_info=True)

    if shutil.which("pipx"):
        try:
            result = subprocess.run(
                ["pipx", "list"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and _PACKAGE_RE.search(result.stdout):
                return InstallMethod.PIPX
        except Exception:
            logger.debug("Failed to check pipx list", exc_info=True)

    if shutil.which("uv"):
        # Only use uv pip if the package is actually installed in the current
        # interpreter's environment.  Without this check we might upgrade into a
        # different environment than the one backing the running ``arcade`` executable.
        try:
            result = subprocess.run(
                ["uv", "pip", "show", PACKAGE_NAME, "--python", sys.executable],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and PACKAGE_NAME in result.stdout:
                return InstallMethod.UV_PIP
        except Exception:
            logger.debug("Failed to check uv pip show", exc_info=True)

    return InstallMethod.PIP


_UPGRADE_COMMANDS: dict[InstallMethod, list[str]] = {
    InstallMethod.UV_TOOL: ["uv", "tool", "upgrade", PACKAGE_NAME],
    InstallMethod.PIPX: ["pipx", "upgrade", PACKAGE_NAME],
    InstallMethod.UV_PIP: [
        "uv",
        "pip",
        "install",
        "--upgrade",
        "--python",
        sys.executable,
        PACKAGE_NAME,
    ],
    InstallMethod.PIP: ["pip", "install", "--upgrade", PACKAGE_NAME],
}

_METHOD_LABELS: dict[InstallMethod, str] = {
    InstallMethod.UV_TOOL: "uv tool",
    InstallMethod.PIPX: "pipx",
    InstallMethod.UV_PIP: "uv pip",
    InstallMethod.PIP: "pip",
}


def run_update() -> None:
    """Check for updates and install if available."""
    console.print("Checking for updates…")

    latest = fetch_latest_pypi_version()
    if latest is None:
        console.print(
            "Could not check for updates. Verify your internet connection and try again.",
            style="yellow",
        )
        return

    current = metadata.version(PACKAGE_NAME)

    if Version(current) >= Version(latest):
        console.print(
            f"Arcade CLI is already up to date (version {current}).",
            style="bold green",
        )
        return

    console.print(f"Update available: {current} → {latest}")

    method = detect_install_method()
    cmd = _UPGRADE_COMMANDS[method]

    # Warn if not using the recommended install method
    if method != InstallMethod.UV_TOOL:
        console.print(
            f"\n⚠️  Detected install method: {_METHOD_LABELS[method]}. "
            f"We recommend installing via `uv tool install {PACKAGE_NAME}` for the best experience.\n",
            style="yellow",
        )

    console.print(f"Upgrading via: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print(f"Successfully updated to {latest}!", style="bold green")
    else:
        console.print(
            f"\nAuto-upgrade failed. Try upgrading manually:\n"
            f"  uv tool upgrade {PACKAGE_NAME}\n\n"
            f"If you don't use `uv tool`, try one of these alternatives instead:\n"
            f"  uv pip install -U {PACKAGE_NAME}\n"
            f"  pip install -U {PACKAGE_NAME}",
            style="red",
        )
