from __future__ import annotations

from pathlib import Path

import toml
from packaging.requirements import Requirement
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_pyproject(path: Path) -> dict:
    return toml.load(path)


def _get_requirement(dependencies: list[str], package_name: str) -> Requirement:
    for dep in dependencies:
        req = Requirement(dep)
        if req.name == package_name:
            return req
    raise AssertionError(f"Missing dependency for {package_name!r}")


def test_root_dependency_includes_workspace_arcade_core_version() -> None:
    root_pyproject = _load_pyproject(REPO_ROOT / "pyproject.toml")
    core_pyproject = _load_pyproject(REPO_ROOT / "libs/arcade-core/pyproject.toml")

    root_deps: list[str] = root_pyproject["project"]["dependencies"]
    core_version = Version(core_pyproject["project"]["version"])
    core_req = _get_requirement(root_deps, "arcade-core")

    assert core_version in core_req.specifier, (
        "Root dependency constraint for arcade-core must include the current "
        f"workspace version {core_version}; got {core_req.specifier!s}"
    )


def test_root_dependency_includes_workspace_arcade_mcp_server_version() -> None:
    root_pyproject = _load_pyproject(REPO_ROOT / "pyproject.toml")
    server_pyproject = _load_pyproject(REPO_ROOT / "libs/arcade-mcp-server/pyproject.toml")

    root_deps: list[str] = root_pyproject["project"]["dependencies"]
    server_version = Version(server_pyproject["project"]["version"])
    server_req = _get_requirement(root_deps, "arcade-mcp-server")

    assert server_version in server_req.specifier, (
        "Root dependency constraint for arcade-mcp-server must include the current "
        f"workspace version {server_version}; got {server_req.specifier!s}"
    )
