"""Warn about dependencies with no prebuilt wheel for the runner.

A package without a wheel for the runner compiles at deploy: slow, it may fail without
system headers, and it fails outright once the runner drops its compilers (DEP-424). The
deployer's machine usually has those headers, so a local run can't catch it.

uv resolves the dependencies the way the runner installs them, for the runner's Python and
libc platform, then checks those exact versions with wheels only. Discovery names no
architecture, so both x86_64 and aarch64 are checked. uv's own index settings apply.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from packaging.utils import canonicalize_name

from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_checks import InstallSource, declared_specs

ARCHITECTURES = ("x86_64", "aarch64")
# The newest manylinux uv can target; a newer runner glibc still runs these wheels.
_NEWEST_UV_MANYLINUX = 40
_OLDEST_UV_MANYLINUX = 31

# Packages that always compile, and the drop-in that ships wheels.
_REPLACEMENTS = {
    "mysqlclient": "PyMySQL",
    "psycopg2": "psycopg[binary]",
    "cx-oracle": "oracledb",
}

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)")


def uv_targets(platform: str) -> list[tuple[str, str]]:
    """``(architecture, uv --python-platform)`` for a libc platform tag such as musllinux_1_2."""
    if platform.startswith("musllinux_"):
        return [(arch, f"{arch}-unknown-linux-musl") for arch in ARCHITECTURES]
    manylinux = re.fullmatch(r"manylinux_2_(\d+)", platform)
    if manylinux and int(manylinux.group(1)) >= _OLDEST_UV_MANYLINUX:
        minor = min(int(manylinux.group(1)), _NEWEST_UV_MANYLINUX)
        return [(arch, f"{arch}-manylinux_2_{minor}") for arch in ARCHITECTURES]
    return []


def wheel_warnings(
    project_dir: Path, source: InstallSource | None, runners: list[DeploymentsRunner]
) -> list[str]:
    """Name every dependency the runner would compile, with a replacement when one is known."""
    checked = [(runner, uv_targets(runner.platform)) for runner in runners]
    checked = [(runner, targets) for runner, targets in checked if targets]
    if not checked or source is None:
        return []
    if _find_uv() is None:
        return ["Skipped the check for prebuilt wheels: uv isn't installed."]

    with tempfile.TemporaryDirectory() as scratch:
        requirements = _requirements_file(project_dir, source, Path(scratch))
        if isinstance(requirements, str):
            return [requirements]
        return [
            warning
            for runner, targets in checked
            for warning in _check_runner(project_dir, requirements, runner, targets, Path(scratch))
        ]


def _check_runner(
    project_dir: Path,
    requirements: Path,
    runner: DeploymentsRunner,
    targets: list[tuple[str, str]],
    scratch: Path,
) -> list[str]:
    where = f"{runner.platform}, Python {runner.version}"
    compiled: dict[str, tuple[str, set[str]]] = {}
    for arch, target in targets:
        pins = _resolve(project_dir, requirements, runner.version, target)
        if isinstance(pins, str):
            return [
                f"Couldn't resolve the dependencies for the runner ({where}, {arch}) to check "
                f"for prebuilt wheels: {pins}"
            ]
        for name, version in _without_wheels(project_dir, pins, runner.version, target, scratch):
            compiled.setdefault(canonicalize_name(name), (version, set()))[1].add(arch)
    if not compiled:
        return []
    listed = ", ".join(
        _describe(name, version, archs) for name, (version, archs) in sorted(compiled.items())
    )
    return [
        f"These packages have no prebuilt wheel for the runner ({where}), so they compile at "
        "deploy, which is slow, can fail without system headers, and will fail once the "
        f"runner drops its compilers: {listed}."
    ]


def _describe(name: str, version: str, archs: set[str]) -> str:
    notes = []
    if set(ARCHITECTURES) - archs:
        notes.append(f"{' and '.join(sorted(archs))} only")
    if name in _REPLACEMENTS:
        notes.append(f"use {_REPLACEMENTS[name]} instead")
    return f"{name} {version}" + (f" ({'; '.join(notes)})" if notes else "")


def _requirements_file(project_dir: Path, source: InstallSource, scratch: Path) -> Path | str:
    """A file uv can resolve that holds what the runner installs; a warning on failure."""
    if source == "requirements.txt":
        return project_dir / "requirements.txt"
    if source == "pyproject.toml":
        return project_dir / "pyproject.toml"
    path = scratch / "requirements.txt"
    if source == "uv.lock":
        exported = _run_uv(
            ["export", "--frozen", "--no-dev", "--no-hashes", "--no-emit-project", "--no-header"],
            project_dir,
        )
        if exported.returncode != 0:
            return f"Couldn't read uv.lock to check for prebuilt wheels: {_last_line(exported)}"
        path.write_text(exported.stdout, encoding="utf-8")
    else:
        path.write_text("\n".join(declared_specs(project_dir, source)) + "\n", encoding="utf-8")
    return path


def _resolve(project_dir: Path, requirements: Path, python: str, target: str) -> list[str] | str:
    """The ``name==version`` pins the runner would install for ``target``, or why not."""
    resolved = _run_uv(
        ["pip", "compile", str(requirements), *_target_args(python, target), "--no-annotate"],
        project_dir,
    )
    if resolved.returncode != 0:
        return _last_line(resolved)
    return [line for line in resolved.stdout.splitlines() if _PIN.match(line)]


def _without_wheels(
    project_dir: Path, pins: list[str], python: str, target: str, scratch: Path
) -> list[tuple[str, str]]:
    """``(name, version)`` of each pin with no wheel for ``target``.

    One check of every pin first; only when it fails is each pin checked on its own.
    """
    if not pins:
        return []
    batch = scratch / f"pins-{target}.txt"
    batch.write_text("\n".join(pins) + "\n", encoding="utf-8")
    wheels_only = [*_target_args(python, target), "--no-deps", "--only-binary", ":all:"]
    if _run_uv(["pip", "compile", str(batch), *wheels_only], project_dir).returncode == 0:
        return []

    def lacks_wheel(pin: str) -> bool:
        checked = _run_uv(["pip", "compile", "-", *wheels_only], project_dir, stdin=pin + "\n")
        return checked.returncode != 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        lacking = [pin for pin, lacks in zip(pins, pool.map(lacks_wheel, pins)) if lacks]
    return [(match.group(1), match.group(2)) for pin in lacking if (match := _PIN.match(pin))]


def _target_args(python: str, target: str) -> list[str]:
    return ["--python-version", python, "--python-platform", target, "--no-header", "--quiet"]


def _last_line(process: subprocess.CompletedProcess[str]) -> str:
    lines = [line.strip() for line in (process.stderr or process.stdout).splitlines()]
    return next((line for line in reversed(lines) if line), f"uv exited with {process.returncode}")


def _find_uv() -> str | None:
    return shutil.which("uv")


def _run_uv(
    args: list[str], cwd: Path, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    uv = _find_uv() or "uv"
    return subprocess.run(
        [uv, *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
