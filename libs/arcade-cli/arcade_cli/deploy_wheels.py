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
# The manylinux glibc versions uv can target. A runner's glibc runs wheels built for any
# older one, so a platform between them is checked as the next older target.
_UV_MANYLINUX = (17, 28, *range(31, 41))

# Packages that always compile, and the drop-in that ships wheels.
_REPLACEMENTS = {
    "mysqlclient": "PyMySQL",
    "psycopg2": "psycopg[binary]",
    "cx-oracle": "oracledb",
}

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)")
# Requirements-file options that say where packages come from.
_INDEX_OPTION = re.compile(
    r"^(--index-url|-i|--extra-index-url|--find-links|-f|--no-index)(?:\s*=\s*|\s+)?(\S*)$"
)
# How uv reports a package that can only be built from source.
_NO_WHEEL = re.compile(r"no usable wheels|no wheels with a matching", re.IGNORECASE)


def uv_targets(platform: str) -> list[tuple[str, str]]:
    """``(architecture, uv --python-platform)`` for a libc platform tag such as musllinux_1_2."""
    if platform.startswith("musllinux_"):
        return [(arch, f"{arch}-unknown-linux-musl") for arch in ARCHITECTURES]
    if platform == "manylinux2014":
        return [(arch, f"{arch}-manylinux2014") for arch in ARCHITECTURES]
    manylinux = re.fullmatch(r"manylinux_2_(\d+)", platform)
    supported = [minor for minor in _UV_MANYLINUX if manylinux and minor <= int(manylinux.group(1))]
    if not supported:
        return []
    return [(arch, f"{arch}-manylinux_2_{supported[-1]}") for arch in ARCHITECTURES]


def wheel_warnings(
    project_dir: Path, source: InstallSource | None, runners: list[DeploymentsRunner]
) -> list[str]:
    """Name every dependency the runner would compile, with a replacement when one is known."""
    checked = [
        (runner, uv_targets(runner.platform)) for runner in runners if runner.language == "python"
    ]
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
    options = _index_options(requirements)
    problems: list[str] = []
    compiled: dict[str, tuple[str, set[str]]] = {}
    for arch, target in targets:
        pins = _resolve(project_dir, requirements, runner.version, target)
        if isinstance(pins, str):
            problems.append(
                f"Couldn't resolve the dependencies for the runner ({where}, {arch}) to check "
                f"for prebuilt wheels: {pins}"
            )
            continue
        lacking = _without_wheels(project_dir, pins, options, runner.version, target, scratch)
        if isinstance(lacking, str):
            problems.append(f"Couldn't check for prebuilt wheels ({where}, {arch}): {lacking}")
            continue
        for name, version in lacking:
            compiled.setdefault(canonicalize_name(name), (version, set()))[1].add(arch)
    if not compiled:
        return problems
    listed = ", ".join(
        _describe(name, version, archs) for name, (version, archs) in sorted(compiled.items())
    )
    return [
        *problems,
        f"These packages have no prebuilt wheel for the runner ({where}), so they compile at "
        "deploy, which is slow, can fail without system headers, and will fail once the "
        f"runner drops its compilers: {listed}.",
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
    project_dir: Path,
    pins: list[str],
    options: list[str],
    python: str,
    target: str,
    scratch: Path,
) -> list[tuple[str, str]] | str:
    """``(name, version)`` of each pin with no wheel for ``target``, or why that's unknown.

    One check of every pin first; only when it fails is each pin checked on its own. The
    requirements' index options apply to every check, so a private index is searched too.
    """
    if not pins:
        return []
    wheels_only = [*_target_args(python, target), "--no-deps", "--only-binary", ":all:"]

    def check(name: str, checked_pins: list[str]) -> subprocess.CompletedProcess[str]:
        path = scratch / f"{target}-{name}.txt"
        path.write_text("\n".join([*options, *checked_pins]) + "\n", encoding="utf-8")
        return _run_uv(["pip", "compile", str(path), *wheels_only], project_dir)

    batch = check("all", pins)
    if batch.returncode == 0:
        return []
    if not _NO_WHEEL.search(batch.stderr or batch.stdout):
        return _last_line(batch)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda pair: check(str(pair[0]), [pair[1]]), enumerate(pins)))
    lacking: list[tuple[str, str]] = []
    for pin, result in zip(pins, results):
        if result.returncode == 0:
            continue
        if not _NO_WHEEL.search(result.stderr or result.stdout):
            return _last_line(result)
        if match := _PIN.match(pin):
            lacking.append((match.group(1), match.group(2)))
    return lacking


def _index_options(requirements: Path, seen: set[Path] | None = None) -> list[str]:
    """The index options in a requirements file and its ``-r`` includes, paths made absolute."""
    if requirements.suffix != ".txt":
        return []
    seen = set() if seen is None else seen
    path = requirements.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    options: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        include = re.match(r"(?:-r|--requirement)(?:\s*=\s*|\s+)(\S+)$", line)
        if include:
            options.extend(_index_options(path.parent / include.group(1), seen))
            continue
        option = _INDEX_OPTION.match(line)
        if not option:
            continue
        flag, value = option.groups()
        flag = {"-i": "--index-url", "-f": "--find-links"}.get(flag, flag)
        if flag == "--find-links" and "://" not in value:
            value = str((path.parent / value).resolve())
        options.append(f"{flag} {value}".strip())
    return options


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
