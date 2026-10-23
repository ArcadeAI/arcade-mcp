"""Checks on a project before ``arcade deploy`` uploads it.

The protocol comes from the project's dependencies: ``arcade-mcp-server`` or ``arcade-mcp``
means an Arcade server, anything else an MCP server. The rest checks what the runner will
install: refusing what it can't, and warning about what may install differently than the
deployer tested.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, Literal

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name

from arcade_cli.context import DeploymentsRunner
from arcade_cli.start_command import load_toml, requirement_specs

Protocol = Literal["arcade", "mcp"]
InstallSource = Literal["uv.lock", "fastmcp.json", "requirements.txt", "pyproject.toml"]

_ARCADE_PACKAGES = {"arcade-mcp-server", "arcade-mcp"}
_UNPINNED_LISTED = 5


class ProjectCheckError(ValueError):
    """The project can't be deployed as it is; nothing is uploaded."""


def detect_protocol(project_dir: Path) -> Protocol:
    """``arcade`` when the project depends on arcade-mcp, otherwise ``mcp``."""
    sources = [
        name
        for name in ("pyproject.toml", "requirements.txt", "fastmcp.json")
        if (project_dir / name).is_file()
    ]
    if not sources:
        raise ProjectCheckError(
            "No dependency source found: add a pyproject.toml, requirements.txt or "
            "fastmcp.json listing the server's dependencies."
        )
    names = {_name(spec) for source in sources for spec in declared_specs(project_dir, source)}
    return "arcade" if names & _ARCADE_PACKAGES else "mcp"


def install_source(project_dir: Path, protocol: Protocol) -> InstallSource | None:
    """The file the runner installs dependencies from: the first of these that exists.

    uv.lock, then (for MCP servers) fastmcp.json, then requirements.txt, then
    pyproject.toml.
    """
    order: tuple[InstallSource, ...] = ("uv.lock", "requirements.txt", "pyproject.toml")
    if protocol == "mcp":
        order = ("uv.lock", "fastmcp.json", "requirements.txt", "pyproject.toml")
    return next((source for source in order if (project_dir / source).is_file()), None)


def check_project(
    project_dir: Path, *, protocol: Protocol, runners: list[DeploymentsRunner]
) -> list[str]:
    """Refuse a project the runner can't install; return warnings about the rest.

    Arcade servers deploy as before: they get only the uv sources warning.
    """
    pyproject = _pyproject(project_dir)
    warnings = _uv_sources_warning(project_dir, pyproject)
    if protocol == "arcade":
        return warnings

    _refuse_poetry_without_export(project_dir, pyproject)
    _refuse_excluded_python(pyproject, [r for r in runners if r.language == "python"])
    return [*_unpinned_warning(project_dir, protocol), *warnings]


def _refuse_poetry_without_export(project_dir: Path, pyproject: dict[str, Any]) -> None:
    """Refuse dependencies only Poetry can install: pip reads [project].dependencies only."""
    poetry_dependencies = pyproject.get("tool", {}).get("poetry", {}).get("dependencies") or {}
    ignored = sorted(name for name in poetry_dependencies if name.lower() != "python")
    if not ignored or install_source(project_dir, "mcp") != "pyproject.toml":
        return
    raise ProjectCheckError(
        "The runner installs with pip, which ignores [tool.poetry.dependencies] "
        f"({', '.join(ignored)}). Export them with "
        "`poetry export -f requirements.txt --output requirements.txt` and deploy again."
    )


def _refuse_excluded_python(pyproject: dict[str, Any], runners: list[DeploymentsRunner]) -> None:
    requires_python = pyproject.get("project", {}).get("requires-python")
    if not requires_python or not runners:
        return
    try:
        specifier = SpecifierSet(requires_python)
    except InvalidSpecifier as e:
        raise ProjectCheckError(f"requires-python {requires_python!r} isn't valid: {e}") from e
    if any(_admits(specifier, runner.version) for runner in runners):
        return
    versions = " or ".join(f"Python {runner.version}" for runner in runners)
    raise ProjectCheckError(
        f"requires-python is {requires_python!r}, which excludes the runner's {versions}. "
        "Widen it to include that version."
    )


def _admits(specifier: SpecifierSet, version: str) -> bool:
    """Whether ``specifier`` admits ``version``, or for a bare "3.12" any 3.12 release."""
    if version.count(".") == 1:
        return any(specifier.contains(f"{version}.{patch}") for patch in range(100))
    return specifier.contains(version)


def _unpinned_warning(project_dir: Path, protocol: Protocol) -> list[str]:
    source = install_source(project_dir, protocol)
    if source is None or source == "uv.lock":
        return []
    unpinned = sorted(
        {_name(spec) for spec in declared_specs(project_dir, source) if not _is_pinned(spec)} - {""}
    )
    if not unpinned:
        return []
    listed = ", ".join(unpinned[:_UNPINNED_LISTED])
    if len(unpinned) > _UNPINNED_LISTED:
        listed += f" and {len(unpinned) - _UNPINNED_LISTED} more"
    return [
        f"These dependencies in {source} aren't pinned, so the deploy may install versions "
        f"you haven't tested: {listed}. Pin them with `uv lock`, or "
        "`pip freeze > requirements.txt`."
    ]


def _uv_sources_warning(project_dir: Path, pyproject: dict[str, Any]) -> list[str]:
    if not pyproject.get("tool", {}).get("uv", {}).get("sources"):
        return []
    if (project_dir / "uv.lock").is_file():
        return []
    return [
        "pyproject.toml has [tool.uv.sources] but no uv.lock. Without a lock the runner "
        "installs with pip, which ignores uv sources, so those packages come from PyPI "
        "instead. Run `uv lock` and deploy again."
    ]


def _is_pinned(spec: str) -> bool:
    try:
        requirement = Requirement(spec)
    except InvalidRequirement:
        return True
    if requirement.url:
        return True
    return any(
        s.operator == "===" or (s.operator == "==" and not s.version.endswith(".*"))
        for s in requirement.specifier
    )


def _name(spec: str) -> str:
    with contextlib.suppress(InvalidRequirement):
        return canonicalize_name(Requirement(spec).name)
    return ""


def declared_specs(project_dir: Path, source: str) -> list[str]:
    """The requirement specs a dependency source declares."""
    path = project_dir / source
    if source == "requirements.txt":
        return list(requirement_specs(path))
    if source == "pyproject.toml":
        return list(_pyproject(project_dir).get("project", {}).get("dependencies", []) or [])
    if source == "fastmcp.json":
        return _fastmcp_json_specs(path)
    return []


def _fastmcp_json_specs(path: Path) -> list[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise ProjectCheckError(f"fastmcp.json couldn't be read: {e}") from e
    if not isinstance(document, dict):
        raise ProjectCheckError("fastmcp.json isn't a JSON object.")
    environment = document.get("environment") or {}
    if not isinstance(environment, dict):
        raise ProjectCheckError("fastmcp.json: `environment` isn't an object.")
    dependencies = environment.get("dependencies") or []
    if not isinstance(dependencies, list) or not all(isinstance(d, str) for d in dependencies):
        raise ProjectCheckError("fastmcp.json: `environment.dependencies` isn't a list of strings.")
    specs = list(dependencies)
    requirements = environment.get("requirements")
    if requirements is not None:
        if not isinstance(requirements, str):
            raise ProjectCheckError("fastmcp.json: `environment.requirements` isn't a file path.")
        if not (path.parent / requirements).is_file():
            raise ProjectCheckError(
                f"fastmcp.json: `environment.requirements` names {requirements}, which doesn't exist."
            )
        specs.extend(requirement_specs(path.parent / requirements))
    return specs


def _pyproject(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return load_toml(path)
    except Exception as e:
        raise ProjectCheckError(f"pyproject.toml couldn't be read: {e}") from e
