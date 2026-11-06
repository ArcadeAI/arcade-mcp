"""Warn about dependencies that have no prebuilt wheel for the runner.

A dependency without a wheel for the runner's Python and platform compiles at deploy. That is
slow, can fail without system headers, and fails outright once the runner drops its
compilers. The deployer's machine usually has those headers, so running the server locally
doesn't catch it.

The check uses uv in two steps, for each Python runner and for both x86_64 and aarch64
(discovery names no architecture):

1. Resolve what the runner would install, with source builds allowed, as pip does there.
2. Check those exact versions with ``--only-binary :all:``: all at once, then each on its own
   only when that batch fails.

Only uv's "no usable wheels" names a package. Any other failure (network, index) is reported
as a check that didn't finish. The result is only ever a warning, never a refusal.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from packaging.utils import canonicalize_name

from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_checks import Protocol, declared_specs, install_source

ARCHITECTURES = ("x86_64", "aarch64")

# Packages that never ship wheels for Linux, and what to use instead.
HINTS = {
    "mysqlclient": "PyMySQL",
    "psycopg2": "psycopg[binary]",
    "cx-oracle": "oracledb",
}

# The manylinux targets uv accepts for --python-platform, by glibc version.
_UV_MANYLINUX: tuple[tuple[int, int], ...] = (
    *((2, minor) for minor in range(40, 30, -1)),
    (2, 28),
    (2, 17),
)

_RESOLVE_TIMEOUT = 300
_CHECK_TIMEOUT = 120
_CHECK_WORKERS = 8

_PINNED = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
_NO_WHEELS = re.compile(r"Because ([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+) has no usable wheels")
_INDEX_OPTION = re.compile(
    r"^(--index-url|-i|--extra-index-url|--find-links|-f|--no-index)(?:\s*=\s*|\s+|$)(\S*)$"
)
_INCLUDE = re.compile(r"^(?:-r|--requirement)(?:\s*=\s*|\s+)(\S+)$")

# Runs uv with these arguments in the project directory, with ``stdin`` as its input.
UvRunner = Callable[[list[str], str, int], subprocess.CompletedProcess[str]]


@dataclass
class WheelCheckResult:
    """What ``check_wheels`` found: warnings to show, and notes about checks skipped."""

    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class _Unfinished(Exception):
    """A uv step failed for a reason other than a missing wheel."""


def check_wheels(
    project_dir: Path,
    *,
    protocol: Protocol,
    runners: list[DeploymentsRunner],
    run_uv: UvRunner | None = None,
) -> WheelCheckResult:
    """Name the dependencies with no prebuilt wheel for each Python runner.

    ``run_uv`` replaces the uv subprocess, for tests; by default uv is found on ``PATH``.
    """
    result = WheelCheckResult()
    python_runners = [r for r in runners if r.language == "python"]
    if not python_runners:
        return result
    source = install_source(project_dir, protocol)
    if source is None:
        return result
    if run_uv is None:
        uv = shutil.which("uv")
        if uv is None:
            result.notes.append(
                "uv isn't on PATH, so dependencies weren't checked for prebuilt wheels "
                "for the runner. Install uv to have them checked."
            )
            return result
        run_uv = _subprocess_runner(uv, project_dir)

    try:
        requirements, index_args = _requirements(project_dir, source, run_uv)
    except _Unfinished as e:
        result.notes.append(f"The wheel check didn't finish: exporting uv.lock failed: {e}")
        return result
    if not requirements.strip():
        return result

    for runner in python_runners:
        label = f"{runner.platform}, Python {runner.version}"
        targets = _uv_targets(runner.platform)
        if targets is None:
            result.notes.append(
                f"The runner's platform ({runner.platform or 'not reported'}) isn't one uv "
                f"can target, so dependencies weren't checked for prebuilt wheels for "
                f"Python {runner.version}."
            )
            continue
        missing: dict[tuple[str, str], list[str]] = {}
        for arch, target in targets:
            try:
                found, errors = _missing_wheels(
                    run_uv, requirements, index_args, runner.version, target
                )
            except _Unfinished as e:
                errors, found = [str(e)], []
            if errors:
                result.notes.append(
                    f"The wheel check for the runner ({label}, {arch}) didn't finish: "
                    + "; ".join(errors)
                )
            for package in found:
                missing.setdefault(package, []).append(arch)
        if missing:
            result.warnings.append(_warning(label, missing))
    return result


def _uv_targets(platform: str) -> list[tuple[str, str]] | None:
    suffix = _uv_platform_suffix(platform)
    if suffix is None:
        return None
    return [(arch, f"{arch}-{suffix}") for arch in ARCHITECTURES]


def _uv_platform_suffix(platform: str) -> str | None:
    """The newest uv target the runner's libc runs: manylinux_2_41 maps to manylinux_2_40."""
    if platform.startswith("musllinux_"):
        return "unknown-linux-musl"
    if platform == "manylinux2014":
        return "manylinux2014"
    match = re.fullmatch(r"manylinux_(\d+)_(\d+)", platform)
    if not match:
        return None
    glibc = (int(match.group(1)), int(match.group(2)))
    supported = next((v for v in _UV_MANYLINUX if v <= glibc), None)
    return None if supported is None else f"manylinux_{supported[0]}_{supported[1]}"


def _requirements(project_dir: Path, source: str, run_uv: UvRunner) -> tuple[str, list[str]]:
    """The requirements the runner installs from ``source``, and the index options they use."""
    if source == "uv.lock":
        exported = run_uv(
            ["export", "--frozen", "--no-dev", "--no-hashes", "--no-emit-project", "--no-header"],
            "",
            _RESOLVE_TIMEOUT,
        )
        if exported.returncode != 0:
            raise _Unfinished(_first_error(exported.stderr))
        return exported.stdout, []
    if source == "requirements.txt":
        path = project_dir / "requirements.txt"
        return f"-r {path}\n", _index_options(path)
    specs = declared_specs(project_dir, source)
    index_args: list[str] = []
    if source == "fastmcp.json":
        included = _fastmcp_requirements_file(project_dir)
        if included is not None:
            index_args = _index_options(included)
    return "".join(f"{spec}\n" for spec in specs), index_args


def _fastmcp_requirements_file(project_dir: Path) -> Path | None:
    document = json.loads((project_dir / "fastmcp.json").read_text(encoding="utf-8-sig"))
    requirements = (document.get("environment") or {}).get("requirements")
    return project_dir / requirements if isinstance(requirements, str) else None


def _index_options(path: Path, seen: set[Path] | None = None) -> list[str]:
    """The index options in a requirements file and its ``-r`` includes, as uv arguments.

    Relative ``--find-links`` directories are resolved against the file that names them.
    """
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    text = re.sub(r"\\\r?\n", " ", path.read_text(encoding="utf-8-sig"))
    options: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*", "", line).strip()
        include = _INCLUDE.match(line)
        if include:
            options.extend(_index_options(path.parent / include.group(1), seen))
            continue
        option = _INDEX_OPTION.match(line)
        if not option:
            continue
        name, value = option.groups()
        name = {"-i": "--index-url", "-f": "--find-links"}.get(name, name)
        if name == "--no-index":
            options.append(name)
        elif value:
            if name == "--find-links" and "://" not in value:
                local = path.parent / value
                value = str(local.resolve()) if local.exists() else value
            options.extend([name, value])
    return options


def _missing_wheels(
    run_uv: UvRunner, requirements: str, index_args: list[str], python: str, target: str
) -> tuple[list[tuple[str, str]], list[str]]:
    """The (name, version) pairs with no wheel for ``target``, and the checks that failed."""
    common = ["--python-version", python, "--python-platform", target, *index_args]
    resolved = run_uv(
        ["pip", "compile", "-", "--no-header", "--no-annotate", *common],
        requirements,
        _RESOLVE_TIMEOUT,
    )
    if resolved.returncode != 0:
        raise _Unfinished(_first_error(resolved.stderr))
    pins = _pins(resolved.stdout)
    if not pins:
        return [], []

    def check(batch: list[tuple[str, str]]) -> subprocess.CompletedProcess[str]:
        return run_uv(
            ["pip", "compile", "-", "--only-binary", ":all:", "--no-deps", "--no-header",
             "--no-annotate", *common],
            "".join(f"{name}=={version}\n" for name, version in batch),
            _CHECK_TIMEOUT,
        )  # fmt: skip

    if check(pins).returncode == 0:
        return [], []
    with ThreadPoolExecutor(max_workers=_CHECK_WORKERS) as pool:
        outcomes = list(pool.map(lambda pin: (pin, check([pin])), pins))
    missing: list[tuple[str, str]] = []
    errors: list[str] = []
    for pin, outcome in outcomes:
        if outcome.returncode == 0:
            continue
        if _names_missing_wheel(outcome.stderr, pin[0]):
            missing.append(pin)
        else:
            errors.append(f"{pin[0]} {pin[1]}: {_first_error(outcome.stderr)}")
    return missing, errors


def _pins(output: str) -> list[tuple[str, str]]:
    """The ``name==version`` lines of a resolution, leaving out direct and local references."""
    pins: dict[str, tuple[str, str]] = {}
    for line in output.splitlines():
        match = _PINNED.match(line.strip())
        if match:
            name = canonicalize_name(match.group(1))
            pins[name] = (name, match.group(2))
    return sorted(pins.values())


def _names_missing_wheel(stderr: str, name: str) -> bool:
    return any(canonicalize_name(m.group(1)) == name for m in _NO_WHEELS.finditer(stderr))


def _warning(label: str, missing: dict[tuple[str, str], list[str]]) -> str:
    entries = []
    for (name, version), archs in sorted(missing.items()):
        notes = []
        if len(archs) < len(ARCHITECTURES):
            notes.append(f"{' and '.join(archs)} only")
        if name in HINTS:
            notes.append(f"use {HINTS[name]} instead")
        entries.append(f"{name} {version}" + (f" ({'; '.join(notes)})" if notes else ""))
    return (
        f"These packages have no prebuilt wheel for the runner ({label}), so they compile at "
        "deploy, which is slow, can fail without system headers, and will fail once the "
        f"runner drops its compilers: {', '.join(entries)}."
    )


def _first_error(stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    causes = [line for line in lines if line.startswith("cause:")]
    first = lines[0] if lines else "uv failed with no output"
    return first if not causes else f"{first} ({causes[-1].removeprefix('cause:').strip()})"


def _subprocess_runner(uv: str, project_dir: Path) -> UvRunner:
    env = {**os.environ, "NO_COLOR": "1", "UV_NO_PROGRESS": "1"}
    # The runner's own environment is irrelevant: uv resolves for the target, not this one.
    env.pop("VIRTUAL_ENV", None)

    def run(args: list[str], stdin: str, timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [uv, *args],
                input=stdin,
                capture_output=True,
                text=True,
                cwd=project_dir,
                env=env,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                [uv, *args], 1, "", f"uv timed out after {timeout} seconds"
            )
        except OSError as e:
            return subprocess.CompletedProcess([uv, *args], 1, "", f"uv couldn't run: {e}")

    return run
