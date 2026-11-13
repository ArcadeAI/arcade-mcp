"""Warn about bundled shared libraries the runner can't load.

``native_libs`` names project directories of shared libraries (an ODBC driver, Oracle Instant
Client) that the runner puts on the server's library path. A library built for another
system, such as macOS, Windows, 32-bit Linux or Alpine (musl), or one that needs a newer glibc
than the runner has, fails only once the server loads it. Each ``.so`` under those
directories is read for its ELF header and dynamic section and compared with the runner's
platform from discovery: x86_64 or aarch64 (discovery names no architecture) and the libc and
glibc version of its wheel platform tag.

The result is only ever a warning: the reading is a heuristic, and the author may know the
library loads. With no runner platform to compare against (an Engine that predates it), the
check is skipped.
"""

from __future__ import annotations

import re
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from arcade_cli.console import console
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_config import DeployConfig

# ELF e_machine values of the architectures a runner may run on.
_MACHINES = {62: "x86_64", 183: "aarch64"}
_MACHINE_NAMES = {3: "x86 (32-bit)", 40: "ARM (32-bit)", 8: "MIPS", 20: "PowerPC", 21: "PowerPC64"}

_PT_LOAD, _PT_DYNAMIC, _PT_INTERP = 1, 2, 3
_DT_NULL, _DT_NEEDED, _DT_STRTAB, _DT_STRSZ = 0, 1, 5, 10

_GLIBC_VERSION = re.compile(rb"GLIBC_(\d+)\.(\d+)")
_SHARED_LIBRARY = re.compile(r".+\.so(\.\d+)*")
_LISTED = 5


@dataclass(frozen=True)
class _Runner:
    label: str
    libc: str  # "glibc" or "musl"
    glibc: tuple[int, int] | None


@dataclass(frozen=True)
class ElfInfo:
    """What the check reads from a shared library."""

    machine: str | None  # x86_64 or aarch64; None for any other architecture
    machine_name: str
    libc: str | None  # "glibc", "musl", or None when it links neither by name
    glibc: tuple[int, int] | None  # the newest GLIBC_x.y symbol version it needs


def native_lib_warnings(
    project_dir: Path, config: DeployConfig, runners: list[DeploymentsRunner]
) -> list[str]:
    """Warnings for the shared libraries in ``native_libs`` the runners can't load."""
    if not config.native_libs:
        return []
    targets = [r for r in (_runner(runner) for runner in runners) if r is not None]
    if not targets:
        return []

    problems: dict[str, list[str]] = {}
    for library in _shared_libraries(project_dir, config.native_libs):
        name = library.relative_to(project_dir).as_posix()
        try:
            info = read_elf(library)
        except OSError:
            continue
        for target in targets:
            problem = _mismatch(info, target)
            if problem:
                problems.setdefault(problem, []).append(name)
                break

    warnings = []
    for problem, names in problems.items():
        listed = ", ".join(names[:_LISTED])
        more = f" and {len(names) - _LISTED} more" if len(names) > _LISTED else ""
        warnings.append(
            f"Bundled libraries in native_libs may not load on the runner: {listed}{more} "
            f"({problem}). Bundle the Linux build for the runner's platform."
        )
    return warnings


def warn_about_native_libs(
    project_dir: Path, config: DeployConfig, runners: list[DeploymentsRunner]
) -> None:
    """Print the ``native_libs`` warnings; never refuse the deploy."""
    for warning in native_lib_warnings(project_dir, config, runners):
        console.print(f"[!] {warning}", style="yellow", markup=False)


def _runner(runner: DeploymentsRunner) -> _Runner | None:
    """The runner's libc from its wheel platform tag, or None when it can't be read."""
    platform = runner.platform
    label = f"{platform}, Python {runner.version}"
    if platform == "manylinux2014":
        return _Runner(label, "glibc", (2, 17))
    if match := re.fullmatch(r"manylinux_(\d+)_(\d+)", platform):
        return _Runner(label, "glibc", (int(match.group(1)), int(match.group(2))))
    if platform.startswith("musllinux_"):
        return _Runner(label, "musl", None)
    return None


def _mismatch(info: ElfInfo, runner: _Runner) -> str | None:
    if info.machine is None:
        return f"built for {info.machine_name}, not x86_64 or aarch64 Linux"
    if info.libc and info.libc != runner.libc:
        return f"built against {info.libc}; the runner ({runner.label}) uses {runner.libc}"
    if runner.glibc and info.glibc and info.glibc > runner.glibc:
        need = ".".join(map(str, info.glibc))
        has = ".".join(map(str, runner.glibc))
        return f"needs glibc {need}; the runner ({runner.label}) has glibc {has}"
    return None


def _shared_libraries(project_dir: Path, directories: list[str]) -> Iterator[Path]:
    seen: set[Path] = set()
    for entry in directories:
        for path in sorted((project_dir / entry).rglob("*")):
            if path in seen or path.is_symlink() or not path.is_file():
                continue
            if _SHARED_LIBRARY.fullmatch(path.name):
                seen.add(path)
                yield path


def read_elf(path: Path) -> ElfInfo:
    """Read a shared library's architecture and the libc it links; raises OSError."""
    with path.open("rb") as file:
        header = file.read(64)
        if header[:4] != b"\x7fELF":
            return ElfInfo(None, _foreign_format(header), None, None)
        if header[4] != 2 or header[5] != 1:
            bits = "32-bit" if header[4] == 1 else "big-endian"
            return ElfInfo(None, f"{bits} ELF", None, None)
        (machine,) = struct.unpack_from("<H", header, 18)
        arch = _MACHINES.get(machine)
        if arch is None:
            name = _MACHINE_NAMES.get(machine, f"ELF machine {machine}")
            return ElfInfo(None, name, None, None)
        needed, strings, interp = _dynamic(file, header)
    libc: str | None = None
    if (interp and b"ld-musl" in interp) or any(
        n.startswith("libc.musl") or n == "libc.so" for n in needed
    ):
        libc = "musl"
    elif (interp and b"ld-linux" in interp) or "libc.so.6" in needed:
        libc = "glibc"
    versions = [(int(a), int(b)) for a, b in _GLIBC_VERSION.findall(strings)]
    if versions and libc is None:
        libc = "glibc"
    return ElfInfo(arch, arch, libc, max(versions) if versions else None)


def _foreign_format(header: bytes) -> str:
    if header[:2] == b"MZ":
        return "Windows (PE)"
    if header[:4] in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return "macOS (Mach-O)"
    return "a format other than ELF"


def _dynamic(file: BinaryIO, header: bytes) -> tuple[list[str], bytes, bytes | None]:
    """The DT_NEEDED names, the dynamic string table and PT_INTERP of a 64-bit LE ELF."""
    read, seek = file.read, file.seek
    (phoff,) = struct.unpack_from("<Q", header, 32)
    phentsize, phnum = struct.unpack_from("<HH", header, 54)
    loads: list[tuple[int, int, int]] = []
    dynamic: tuple[int, int] | None = None
    interp_at: tuple[int, int] | None = None
    for index in range(min(phnum, 256)):
        seek(phoff + index * phentsize)
        entry = read(56)
        if len(entry) < 56:
            break
        p_type, _flags, offset, vaddr, _paddr, filesz = struct.unpack_from("<IIQQQQ", entry)
        if p_type == _PT_LOAD:
            loads.append((vaddr, offset, filesz))
        elif p_type == _PT_DYNAMIC:
            dynamic = (offset, filesz)
        elif p_type == _PT_INTERP:
            interp_at = (offset, filesz)

    interp = None
    if interp_at:
        seek(interp_at[0])
        interp = read(min(interp_at[1], 4096))
    if dynamic is None:
        return [], b"", interp

    seek(dynamic[0])
    raw = read(min(dynamic[1], 1 << 20))
    needed_offsets: list[int] = []
    strtab = strsz = None
    for at in range(0, len(raw) - 15, 16):
        tag, value = struct.unpack_from("<qQ", raw, at)
        if tag == _DT_NULL:
            break
        if tag == _DT_NEEDED:
            needed_offsets.append(value)
        elif tag == _DT_STRTAB:
            strtab = value
        elif tag == _DT_STRSZ:
            strsz = value
    if strtab is None or strsz is None:
        return [], b"", interp
    start = next(
        (
            offset + strtab - vaddr
            for vaddr, offset, size in loads
            if vaddr <= strtab < vaddr + size
        ),
        strtab,
    )
    seek(start)
    strings = read(min(strsz, 16 << 20))
    needed = [
        strings[o : strings.find(b"\0", o)].decode(errors="replace")
        for o in needed_offsets
        if o < len(strings)
    ]
    return needed, strings, interp
