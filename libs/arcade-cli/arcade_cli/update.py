"""Logic for the `arcade update` / `arcade upgrade` CLI command."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from enum import Enum
from importlib import metadata
from urllib.request import urlopen

from arcade_cli.console import console

logger = logging.getLogger(__name__)

PACKAGE_NAME = "arcade-mcp"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"


class InstallMethod(str, Enum):
    UV_TOOL = "uv_tool"
    PIPX = "pipx"
    UV_PIP = "uv_pip"
    PIP = "pip"


def fetch_latest_pypi_version() -> str | None:
    """Query PyPI for the latest published version of the package."""
    try:
        with urlopen(PYPI_URL) as resp:  # noqa: S310
            if resp.status != 200:
                return None
            data = json.loads(resp.read())
            return data["info"]["version"]  # type: ignore[no-any-return]
    except Exception:
        return None


def detect_install_method() -> InstallMethod:
    """Auto-detect how the user originally installed the CLI."""
    # 1. Check uv tool
    if shutil.which("uv"):
        try:
            result = subprocess.run(
                ["uv", "tool", "list"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and PACKAGE_NAME in result.stdout:
                return InstallMethod.UV_TOOL
        except Exception:
            logger.debug("Failed to check uv tool list", exc_info=True)

    # 2. Check pipx
    if shutil.which("pipx"):
        try:
            result = subprocess.run(
                ["pipx", "list"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and PACKAGE_NAME in result.stdout:
                return InstallMethod.PIPX
        except Exception:
            logger.debug("Failed to check pipx list", exc_info=True)

    # 3. If uv is available, use uv pip
    if shutil.which("uv"):
        return InstallMethod.UV_PIP

    # 4. Fallback to pip
    return InstallMethod.PIP


_UPGRADE_COMMANDS: dict[InstallMethod, list[str]] = {
    InstallMethod.UV_TOOL: ["uv", "tool", "upgrade", PACKAGE_NAME],
    InstallMethod.PIPX: ["pipx", "upgrade", PACKAGE_NAME],
    InstallMethod.UV_PIP: ["uv", "pip", "install", "--upgrade", PACKAGE_NAME],
    InstallMethod.PIP: ["pip", "install", "--upgrade", PACKAGE_NAME],
}

_METHOD_LABELS: dict[InstallMethod, str] = {
    InstallMethod.UV_TOOL: "uv tool",
    InstallMethod.PIPX: "pipx",
    InstallMethod.UV_PIP: "uv pip",
    InstallMethod.PIP: "pip",
}


def _upgrade_command(method: InstallMethod) -> list[str]:
    """Return the shell command to run for a given install method."""
    return _UPGRADE_COMMANDS[method]


def _method_label(method: InstallMethod) -> str:
    return _METHOD_LABELS[method]


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

    from packaging.version import Version

    if Version(current) >= Version(latest):
        console.print(
            f"Arcade CLI is already up to date (version {current}).",
            style="bold green",
        )
        return

    console.print(f"Update available: {current} → {latest}")

    method = detect_install_method()
    cmd = _upgrade_command(method)

    # Warn if not using the recommended install method
    if method != InstallMethod.UV_TOOL:
        console.print(
            f"\n⚠️  Detected install method: {_method_label(method)}. "
            f"We recommend installing via `uv tool install {PACKAGE_NAME}` for the best experience.\n",
            style="yellow",
        )

    console.print(f"Upgrading via: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print(f"Successfully updated to {latest}!", style="bold green")
    else:
        console.print(
            f"\nAuto-upgrade failed. You can try manually:\n"
            f"  uv tool upgrade {PACKAGE_NAME}\n"
            f"  uv pip install -U {PACKAGE_NAME}\n"
            f"  pip install -U {PACKAGE_NAME}",
            style="red",
        )
