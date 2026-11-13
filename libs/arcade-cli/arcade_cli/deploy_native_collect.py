"""Collect the native libraries bundled extensions need from Debian trixie, before upload.

The runner image can't ship every native library, and authors can't install packages in the
cluster, so a library a bundled extension links (unixODBC for pyodbc, libaio for Oracle thick
mode, libgssapi_krb5 for gssapi) is collected on the deployer's machine and shipped in the
bundle under ``vendor/native``, which is appended to ``native_libs`` in ``.arcade/deploy.json``.

1. Walk the bundle's shared libraries: loose ``.so`` files and those inside bundled wheels.
   Libraries inside a wheel's ``<name>.libs`` directory are its own vendored copies and are
   not walked. Author ``native_libs`` libraries are walked so their own dependencies resolve.
2. For each ``DT_NEEDED`` name, subtract what the runner already has: glibc and the
   libraries PEP 600 lets a manylinux wheel assume (``MANYLINUX_LIBRARIES``), then whatever
   the library's ``DT_RUNPATH`` finds through ``$ORIGIN`` (such as a wheel's ``.libs``).
3. Subtract what a directory in the author's ``native_libs`` provides. An airgapped author
   sets ``native_libs`` themselves; when nothing is left, Debian is never contacted and no
   ``vendor/native`` is added.
4. Fetch the rest from a pinned Debian trixie snapshot: the ``InRelease`` file must match a
   pinned SHA256, the ``Packages`` index the hash ``InRelease`` lists, and each ``.deb`` the
   hash the index lists. The library is extracted by its SONAME, and its own dependencies are
   resolved the same way.

A library that needs a newer glibc than the runner's is refused, as is a collection over the
bundle size cap. When a library is still unresolved and Debian can't be reached, the deploy
is refused naming it. Nothing is written to the project: the collected libraries go straight
into the bundle. ``dlopen`` libraries aren't in ``DT_NEEDED``; the runner's install-time
native library check is the backstop for those.
"""

from __future__ import annotations

import hashlib
import io
import lzma
import os
import posixpath
import re
import tarfile
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

import httpx

from arcade_cli.console import console
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy import (
    MAX_UNCOMPRESSED_BUNDLE_BYTES,
    DeployRefusedError,
    arcade_archive_drops,
)
from arcade_cli.deploy_checks import Protocol
from arcade_cli.deploy_config import DeployConfig
from arcade_cli.deploy_native_libs import (
    _SHARED_LIBRARY,
    ElfInfo,
    TruncatedElfError,
    read_elf_from,
)

# Where collected libraries go in the bundle, and the entry appended to native_libs.
NATIVE_DIR = "vendor/native"

# The Debian snapshot libraries are collected from. The runner image is Debian trixie
# (python:3.12-slim-trixie), so its libraries match. Moving the snapshot means updating
# DEBIAN_INRELEASE_SHA256 to the new snapshot's InRelease; a test checks they move together.
DEBIAN_SUITE = "trixie"
DEBIAN_SNAPSHOT = "20261101T022418Z"
DEBIAN_INRELEASE_SHA256 = "0584fba32e13e0ab8285fb16c27adea1ec03a73669c18702821094fd6ca86675"
DEBIAN_SNAPSHOT_URL = f"https://snapshot.debian.org/archive/debian/{DEBIAN_SNAPSHOT}"

# trixie's glibc, the manylinux_2_41 policy; used when discovery names no runner platform.
RUNNER_GLIBC = (2, 41)

# What every runner provides, per PEP 600: glibc's libraries and the base libraries
# auditwheel's manylinux_2_x policies let a wheel link without bundling.
MANYLINUX_LIBRARIES = frozenset({
    # glibc
    "libc.so.6",
    "libm.so.6",
    "libdl.so.2",
    "librt.so.1",
    "libpthread.so.0",
    "libresolv.so.2",
    "libutil.so.1",
    "libnsl.so.1",
    "libanl.so.1",
    "libmvec.so.1",
    "ld-linux-x86-64.so.2",
    "ld-linux-aarch64.so.1",
    # The rest of the manylinux_2_x policy.
    "libgcc_s.so.1",
    "libstdc++.so.6",
    "libX11.so.6",
    "libXext.so.6",
    "libXrender.so.1",
    "libICE.so.6",
    "libSM.so.6",
    "libGL.so.1",
    "libgobject-2.0.so.0",
    "libgthread-2.0.so.0",
    "libglib-2.0.so.0",
})

# Debian's name for each runner architecture, and the ELF machine it reports.
_DEBIAN_ARCH = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
_ELF_MACHINE = {"amd64": "x86_64", "arm64": "aarch64"}
_TRIPLETS = {"amd64": "x86_64-linux-gnu", "arm64": "aarch64-linux-gnu"}

_INDEX_LIMIT = 64 << 20  # Packages.xz is ~10 MiB
_UNPACKED_INDEX_LIMIT = 256 << 20  # and ~60 MiB unpacked
_TIMEOUT = 60
_MAX_LINKS = 8

# Fetches a URL's body, refusing one larger than the given number of bytes.
Fetch = Callable[[str, int], bytes]


class DebianUnreachableError(Exception):
    """The Debian snapshot couldn't be reached or answered with an error."""


@dataclass(frozen=True)
class CollectedLibrary:
    """A library extracted from a Debian package, named by its SONAME."""

    soname: str
    package: str
    version: str
    data: bytes


@dataclass(frozen=True)
class NativeCollection:
    """The libraries to ship under ``vendor/native``."""

    libraries: tuple[CollectedLibrary, ...]

    def files(self) -> dict[str, bytes]:
        """The bundle files, by path relative to the project."""
        return {f"{NATIVE_DIR}/{lib.soname}": lib.data for lib in self.libraries}


@dataclass(frozen=True)
class _Library:
    """A shared library in the bundle, with the files its $ORIGIN can see."""

    name: str  # for messages: a project path, or "wheel.whl:member"
    info: ElfInfo
    origin: str  # the directory $ORIGIN expands to, within ``files``
    files: frozenset[str]
    authors: bool = False  # under an author native_libs directory


def collect_native_libs(
    project_dir: Path,
    config: DeployConfig,
    runners: list[DeploymentsRunner],
    *,
    protocol: Protocol,
    fetch: Fetch | None = None,
) -> NativeCollection | None:
    """Collect what the bundle's extensions need and the runner lacks.

    Returns ``None`` when nothing is missing; Debian is then never contacted.
    Raises ``DeployRefusedError`` for anything that would leave a library unresolved.
    """
    if any(runner.platform.startswith("musllinux") for runner in runners):
        return None  # An Alpine runner can't load Debian's glibc libraries.
    arch = _debian_arch(runners)
    machine = _ELF_MACHINE[arch]

    files = _bundled_files(project_dir, protocol)
    author_dirs = set(config.native_libs)
    libraries = [
        lib for lib in _libraries(project_dir, files, author_dirs) if lib.info.machine == machine
    ]
    if not libraries:
        return None
    runner_glibc = _runner_glibc(runners)

    provided = _author_sonames(project_dir, config.native_libs)
    needed_by: dict[str, str] = {}
    for lib in libraries:
        missing = [
            soname
            for soname in lib.info.needed
            if soname not in MANYLINUX_LIBRARIES
            and soname not in provided
            and not _on_runpath(lib, soname)
        ]
        if missing and not lib.authors:
            # Debian's libraries can't make a library built for a newer glibc load.
            _refuse_newer_glibc(lib.name, lib.info, runner_glibc)
        for soname in missing:
            needed_by.setdefault(soname, lib.name)
    if not needed_by:
        return None

    if (project_dir / NATIVE_DIR).exists():
        raise DeployRefusedError(
            f"The project already has {NATIVE_DIR}, where the deploy puts the native "
            f"libraries it collects ({', '.join(sorted(needed_by))}). Rename that directory "
            "and list it in native_libs."
        )

    console.print(
        f"\nCollecting native libraries the runner lacks from Debian {DEBIAN_SUITE} "
        f"({arch}): {', '.join(sorted(needed_by))}",
        style="dim",
    )
    archive = _DebianArchive(arch, fetch or _http_get)
    collected: dict[str, CollectedLibrary] = {}
    queue = sorted(needed_by)
    total = 0
    try:
        while queue:
            soname = queue[0]
            library, info = archive.library(soname, needed_by[soname])
            _refuse_newer_glibc(
                f"{soname} (Debian package {library.package} {library.version})",
                info,
                runner_glibc,
            )
            total += len(library.data)
            if total > MAX_UNCOMPRESSED_BUNDLE_BYTES:
                cap = MAX_UNCOMPRESSED_BUNDLE_BYTES >> 20
                raise DeployRefusedError(
                    f"The native libraries collected from Debian are over the {cap} MiB "
                    "bundle size cap. Bundle fewer libraries, or provide them in a "
                    "native_libs directory."
                )
            collected[soname] = library
            queue.pop(0)
            console.print(
                f"✓ {soname} from Debian package {library.package} {library.version}",
                style="green",
                markup=False,
            )
            for dependency in info.needed:
                if (
                    dependency in MANYLINUX_LIBRARIES
                    or dependency in provided
                    or dependency in collected
                    or dependency in queue
                ):
                    continue
                needed_by[dependency] = soname
                queue.append(dependency)
    except DebianUnreachableError as e:
        unresolved = ", ".join(f"{name} (needed by {needed_by[name]})" for name in queue)
        raise DeployRefusedError(
            f"These native libraries aren't provided by the runner or native_libs, and the "
            f"Debian snapshot they're collected from couldn't be reached ({e}): {unresolved}. "
            "Deploy again when it can be reached, or put the libraries in a directory and "
            "list it in native_libs."
        ) from e
    return NativeCollection(tuple(collected[name] for name in sorted(collected)))


def _debian_arch(runners: list[DeploymentsRunner]) -> str:
    """The runner's Debian architecture; amd64 when the Engine doesn't name one."""
    for runner in runners:
        if runner.architecture:
            arch = _DEBIAN_ARCH.get(runner.architecture.lower())
            if arch is None:
                raise DeployRefusedError(
                    f"The runner's architecture {runner.architecture!r} isn't one native "
                    "libraries can be collected for (x86_64 or aarch64)."
                )
            return arch
    return "amd64"


def _runner_glibc(runners: list[DeploymentsRunner]) -> tuple[int, int]:
    """The runner's glibc from its manylinux tag; trixie's when the Engine names none."""
    for runner in runners:
        match = re.fullmatch(r"manylinux_(\d+)_(\d+)", runner.platform)
        if match:
            return int(match.group(1)), int(match.group(2))
    return RUNNER_GLIBC


def _refuse_newer_glibc(name: str, info: ElfInfo, runner_glibc: tuple[int, int]) -> None:
    if info.glibc and info.glibc > runner_glibc:
        need = ".".join(map(str, info.glibc))
        has = ".".join(map(str, runner_glibc))
        raise DeployRefusedError(
            f"{name} needs glibc {need}, but the runner has glibc {has}. Use a build of it "
            f"for glibc {has} or older."
        )


# Walking the bundle


def _bundled_files(project_dir: Path, protocol: Protocol) -> frozenset[str]:
    """The project files the bundle carries, as project-relative POSIX paths."""

    def dropped(part: str) -> bool:
        if protocol == "arcade":
            return arcade_archive_drops(part)
        return part.startswith(".") or part == "__pycache__" or part.endswith(".egg-info")

    files: set[str] = set()
    for parent, dirs, names in os.walk(project_dir):
        here = Path(parent)
        dirs[:] = [
            d for d in sorted(dirs) if not dropped(d) and not (here / d / "pyvenv.cfg").is_file()
        ]
        relative = here.relative_to(project_dir).as_posix()
        for name in names:
            if not dropped(name):
                files.add(name if relative == "." else f"{relative}/{name}")
    return frozenset(files)


def _libraries(
    project_dir: Path, files: frozenset[str], author_dirs: set[str]
) -> Iterator[_Library]:
    """Each shared library in the bundle, including those inside bundled wheels."""
    seen: set[Path] = set()
    for name in sorted(files):
        path = project_dir / name
        if name.endswith(".whl"):
            yield from _wheel_libraries(path, name)
            continue
        if not _SHARED_LIBRARY.fullmatch(posixpath.basename(name)) or _in_dot_libs(name):
            continue
        target = path.resolve()
        if target in seen or not target.is_file():
            continue
        seen.add(target)
        info = _read(path.open("rb"), name)
        if info is not None:
            authors = any(name.startswith(f"{entry}/") for entry in author_dirs)
            yield _Library(name, info, posixpath.dirname(name), files, authors)


def _wheel_libraries(path: Path, name: str) -> Iterator[_Library]:
    try:
        wheel = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        return
    with wheel:
        members = frozenset(m for m in wheel.namelist() if not m.endswith("/"))
        for member in sorted(members):
            if not _SHARED_LIBRARY.fullmatch(posixpath.basename(member)) or _in_dot_libs(member):
                continue
            info = _read(wheel.open(member), f"{name}:{member}")
            if info is not None:
                yield _Library(f"{name}:{member}", info, posixpath.dirname(member), members)


def _read(file: IO[bytes], name: str) -> ElfInfo | None:
    with file:
        try:
            return read_elf_from(file, name)
        except (TruncatedElfError, OSError):
            return None


def _in_dot_libs(name: str) -> bool:
    """Whether a path is inside a wheel's vendored ``<name>.libs`` directory."""
    return any(part.endswith(".libs") for part in name.split("/")[:-1])


def _on_runpath(lib: _Library, soname: str) -> bool:
    """Whether the library's run path finds ``soname`` among the files beside it."""
    for entry in lib.info.runpath:
        if "$ORIGIN" not in entry and "${ORIGIN}" not in entry:
            continue  # An absolute or working-directory path names nothing in the bundle.
        directory = entry.replace("${ORIGIN}", lib.origin or ".").replace(
            "$ORIGIN", lib.origin or "."
        )
        candidate = posixpath.normpath(posixpath.join(directory, soname))
        if candidate in lib.files:
            return True
    return False


def _author_sonames(project_dir: Path, native_libs: list[str]) -> set[str]:
    """The library names the author's native_libs directories put on the library path."""
    names: set[str] = set()
    for entry in native_libs:
        directory = project_dir / entry
        if directory.is_dir():
            names |= {child.name for child in directory.iterdir() if child.is_file()}
    return names


# Debian


@dataclass(frozen=True)
class _Package:
    name: str
    version: str
    filename: str
    sha256: str
    size: int


@dataclass
class _DebianArchive:
    arch: str
    fetch: Fetch
    _packages: dict[str, _Package] | None = field(default=None, init=False)

    def library(self, soname: str, needed_by: str) -> tuple[CollectedLibrary, ElfInfo]:
        """The library named ``soname``, from the package Debian names after it."""
        packages = self.packages()
        candidates = [packages[name] for name in package_names(soname) if name in packages]
        for package in candidates:
            data = self._extract(package, soname)
            if data is not None:
                info = read_elf_from(io.BytesIO(data), soname)
                if info.machine != _ELF_MACHINE[self.arch]:
                    raise DeployRefusedError(
                        f"{soname} in Debian package {package.name} is built for "
                        f"{info.machine_name}, not {_ELF_MACHINE[self.arch]}."
                    )
                return CollectedLibrary(soname, package.name, package.version, data), info
        tried = ", ".join(package_names(soname)) or "none"
        raise DeployRefusedError(
            f"{soname} (needed by {needed_by}) isn't provided by the runner or native_libs, "
            f"and no Debian {DEBIAN_SUITE} package named after it provides it (looked for: "
            f"{tried}). Put the library in a directory and list it in native_libs."
        )

    def packages(self) -> dict[str, _Package]:
        if self._packages is None:
            self._packages = self._load_packages()
        return self._packages

    def _load_packages(self) -> dict[str, _Package]:
        release = self.fetch(f"{DEBIAN_SNAPSHOT_URL}/dists/{DEBIAN_SUITE}/InRelease", 1 << 20)
        if hashlib.sha256(release).hexdigest() != DEBIAN_INRELEASE_SHA256:
            raise DeployRefusedError(
                f"The Debian {DEBIAN_SUITE} snapshot {DEBIAN_SNAPSHOT} returned an InRelease "
                "file that doesn't match the one this CLI pins, so nothing was collected."
            )
        index_path = f"main/binary-{self.arch}/Packages.xz"
        sha256, size = _release_entry(release, index_path)
        index = self.fetch(f"{DEBIAN_SNAPSHOT_URL}/dists/{DEBIAN_SUITE}/{index_path}", _INDEX_LIMIT)
        _verify(index, sha256, size, index_path)
        decompressor = lzma.LZMADecompressor()
        try:
            text = decompressor.decompress(index, max_length=_UNPACKED_INDEX_LIMIT)
        except lzma.LZMAError as e:
            raise DeployRefusedError(f"Debian's {index_path} couldn't be read: {e}") from e
        if not decompressor.eof:
            raise DeployRefusedError(f"Debian's {index_path} is larger than expected.")
        return parse_packages(text.decode("utf-8", errors="replace"), self.arch)

    def _extract(self, package: _Package, soname: str) -> bytes | None:
        if package.size > MAX_UNCOMPRESSED_BUNDLE_BYTES:
            cap = MAX_UNCOMPRESSED_BUNDLE_BYTES >> 20
            raise DeployRefusedError(
                f"Debian package {package.name} is over the {cap} MiB bundle size cap."
            )
        deb = self.fetch(f"{DEBIAN_SNAPSHOT_URL}/{package.filename}", package.size)
        _verify(deb, package.sha256, package.size, package.filename)
        return extract_library(deb, soname, self.arch, package.name)


def package_names(soname: str) -> list[str]:
    """The Debian package names a library's SONAME gives, per Debian policy 8.1.

    ``libodbc.so.2`` is in ``libodbc2``, ``libgssapi_krb5.so.2`` in ``libgssapi-krb5-2``.
    Since the 64-bit time_t transition some have a ``t64`` suffix (``libaio1t64``).
    """
    match = re.fullmatch(r"(.+)\.so\.(\d[\w.]*?)", soname)
    if match is None:
        return []
    base, version = match.group(1).lower().replace("_", "-"), match.group(2)
    name = f"{base}-{version}" if base[-1].isdigit() else f"{base}{version}"
    return [name, f"{name}t64"]


def _release_entry(release: bytes, path: str) -> tuple[str, int]:
    """The SHA256 and size ``InRelease`` lists for ``path``."""
    in_sha256 = False
    for line in release.decode("utf-8", errors="replace").splitlines():
        if not line.startswith(" "):
            in_sha256 = line.strip() == "SHA256:"
            continue
        parts = line.split()
        if in_sha256 and len(parts) == 3 and parts[2] == path:
            return parts[0], int(parts[1])
    raise DeployRefusedError(f"Debian's InRelease doesn't list {path}.")


def parse_packages(text: str, arch: str) -> dict[str, _Package]:
    """The binary packages a ``Packages`` index lists for ``arch``, by name."""
    packages: dict[str, _Package] = {}
    for stanza in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in stanza.splitlines():
            if line[:1] in (" ", "\t") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key] = value.strip()
        try:
            package = _Package(
                fields["Package"],
                fields["Version"],
                fields["Filename"],
                fields["SHA256"],
                int(fields["Size"]),
            )
        except (KeyError, ValueError):
            continue
        if fields.get("Architecture") in (arch, "all") and package.name not in packages:
            packages[package.name] = package
    return packages


def _verify(data: bytes, sha256: str, size: int, what: str) -> None:
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
        raise DeployRefusedError(
            f"{what} from the Debian snapshot doesn't match the SHA256 its signed index "
            "lists, so nothing was collected."
        )


def extract_library(deb: bytes, soname: str, arch: str, package: str) -> bytes | None:
    """The contents of ``soname`` in a ``.deb``, following links; ``None`` when it's absent."""
    data_tar = _ar_member(deb, "data.tar", package)
    try:
        with tarfile.open(fileobj=io.BytesIO(data_tar), mode="r:*") as tar:
            return _find_library(tar, soname, _TRIPLETS[arch])
    except (tarfile.TarError, lzma.LZMAError, EOFError, OSError) as e:
        raise DeployRefusedError(f"Debian package {package} couldn't be unpacked: {e}") from e


def _find_library(tar: tarfile.TarFile, soname: str, triplet: str) -> bytes | None:
    members = {posixpath.normpath(m.name.lstrip("./") or "."): m for m in tar.getmembers()}
    for library_dir in (f"usr/lib/{triplet}", f"lib/{triplet}", "usr/lib", "lib"):
        directory, path = library_dir, f"{library_dir}/{soname}"
        member = members.get(path)
        for _ in range(_MAX_LINKS):
            if member is None or not member.issym():
                break
            target = member.linkname
            path = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else posixpath.join(directory, target)
            )
            directory = posixpath.dirname(path)
            member = members.get(path)
        if member is not None and member.isfile():
            extracted = tar.extractfile(member)
            if extracted is not None:
                return extracted.read()
    return None


def _ar_member(deb: bytes, prefix: str, package: str) -> bytes:
    """The first member of an ``ar`` archive whose name starts with ``prefix``."""
    if not deb.startswith(b"!<arch>\n"):
        raise DeployRefusedError(f"Debian package {package} isn't an ar archive.")
    at = 8
    while at + 60 <= len(deb):
        header = deb[at : at + 60]
        name = header[:16].decode("ascii", errors="replace").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError as e:
            raise DeployRefusedError(f"Debian package {package} is damaged.") from e
        start = at + 60
        if name.startswith(prefix):
            return deb[start : start + size]
        at = start + size + (size & 1)
    raise DeployRefusedError(f"Debian package {package} has no {prefix} member.")


def _http_get(url: str, limit: int) -> bytes:
    """GET ``url``, refusing a body over ``limit`` bytes."""
    try:
        with httpx.stream("GET", url, timeout=_TIMEOUT, follow_redirects=True) as response:
            if response.status_code != 200:
                raise DebianUnreachableError(f"{url} answered {response.status_code}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > limit:
                    raise DeployRefusedError(f"{url} is larger than expected.")
            return bytes(body)
    except httpx.HTTPError as e:
        raise DebianUnreachableError(f"{url}: {e}") from e
