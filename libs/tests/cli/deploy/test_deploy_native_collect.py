"""Collecting the native libraries bundled extensions need from Debian, before upload."""

import hashlib
import io
import json
import lzma
import os
import re
import struct
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from arcade_cli import deploy_native_collect as collect_module
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy import DeployRefusedError
from arcade_cli.deploy_config import load_deploy_config, runner_settings_json
from arcade_cli.deploy_native_collect import (
    DEBIAN_INRELEASE_SHA256,
    DEBIAN_SNAPSHOT,
    DEBIAN_SNAPSHOT_URL,
    NATIVE_DIR,
    DebianUnreachableError,
    NativeCollection,
    collect_native_libs,
    package_names,
)

X86_64, AARCH64 = 62, 183
RUNNER = [DeploymentsRunner(language="python", version="3.12", platform="manylinux_2_41")]
ARM_RUNNER = [
    DeploymentsRunner(
        language="python", version="3.12", platform="manylinux_2_41", architecture="aarch64"
    )
]


def elf(
    *,
    machine: int = X86_64,
    needed: tuple[str, ...] = ("libc.so.6",),
    glibc: str = "GLIBC_2.17",
    runpath: str | None = None,
    padding: int = 0,
) -> bytes:
    """A minimal 64-bit ELF shared library with DT_NEEDED, DT_RUNPATH and a glibc version."""
    strings = b"\0"
    offsets: dict[str, int] = {}
    for name in (*needed, glibc, *([runpath] if runpath else [])):
        offsets[name] = len(strings)
        strings += name.encode() + b"\0"
    strtab_at = 64 + 2 * 56
    dynamic_at = strtab_at + len(strings)
    base = 0x400000
    entries = [(1, offsets[name]) for name in needed]
    if runpath:
        entries.append((29, offsets[runpath]))
    entries += [(5, base + strtab_at), (10, len(strings)), (0, 0)]
    dynamic = b"".join(struct.pack("<qQ", tag, value) for tag, value in entries)
    size = dynamic_at + len(dynamic)
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    header = ident + struct.pack("<HHIQQQIHHHHHH", 3, machine, 1, 0, 64, 0, 0, 64, 56, 2, 64, 0, 0)
    phdrs = struct.pack("<IIQQQQQQ", 1, 5, 0, base, base, size, size, 0x1000)
    phdrs += struct.pack(
        "<IIQQQQQQ", 2, 6, dynamic_at, base + dynamic_at, 0, len(dynamic), len(dynamic), 8
    )
    return header + phdrs + strings + dynamic + bytes(padding)


def deb(files: dict[str, bytes], links: dict[str, str] | None = None) -> bytes:
    """A .deb: an ar archive holding debian-binary, control.tar.xz and data.tar.xz."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:xz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(f"./{name}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo(f"./{name}")
            info.type, info.linkname = tarfile.SYMTYPE, target
            tar.addfile(info)
    control = io.BytesIO()
    with tarfile.open(fileobj=control, mode="w:xz"):
        pass
    members = [
        ("debian-binary", b"2.0\n"),
        ("control.tar.xz", control.getvalue()),
        ("data.tar.xz", data.getvalue()),
    ]
    out = b"!<arch>\n"
    for name, content in members:
        header = f"{name:<16}{0:<12}{0:<6}{0:<6}{100644:<8}{len(content):<10}`\n"
        out += header.encode() + content + (b"\n" if len(content) % 2 else b"")
    return out


class FakeDebian:
    """A Debian snapshot served from memory; records every URL fetched."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, arch: str = "amd64") -> None:
        self.arch = arch
        self.debs: dict[str, tuple[str, bytes]] = {}  # package -> (version, .deb)
        self.requests: list[str] = []
        self.unreachable = False
        self.tamper: set[str] = set()
        self.monkeypatch = monkeypatch

    def add(self, package: str, files: dict[str, bytes], **kwargs: dict[str, str]) -> None:
        self.debs[package] = ("1.0-1", deb(files, **kwargs))

    def _packages(self) -> bytes:
        stanzas = []
        for package, (version, content) in self.debs.items():
            stanzas.append(
                f"Package: {package}\nVersion: {version}\nArchitecture: {self.arch}\n"
                f"Filename: pool/main/{package}_{version}_{self.arch}.deb\n"
                f"Size: {len(content)}\nSHA256: {hashlib.sha256(content).hexdigest()}\n"
            )
        return lzma.compress("\n".join(stanzas).encode())

    def _release(self) -> bytes:
        index = self._packages()
        digest = hashlib.sha256(index).hexdigest()
        release = (
            "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nCodename: trixie\nSHA256:\n"
            f" {digest} {len(index)} main/binary-{self.arch}/Packages.xz\n"
        ).encode()
        self.monkeypatch.setattr(
            collect_module, "DEBIAN_INRELEASE_SHA256", hashlib.sha256(release).hexdigest()
        )
        return release

    def fetch(self, url: str, limit: int) -> bytes:
        self.requests.append(url)
        if self.unreachable:
            raise DebianUnreachableError(f"{url}: connection refused")
        path = url.removeprefix(f"{DEBIAN_SNAPSHOT_URL}/")
        if path == "dists/trixie/InRelease":
            body = self._release()
        elif path == f"dists/trixie/main/binary-{self.arch}/Packages.xz":
            body = self._packages()
        else:
            package = path.split("/")[-1].split("_")[0]
            body = self.debs[package][1]
            if package in self.tamper:
                body = body[:-1] + bytes([body[-1] ^ 1])
        assert len(body) <= limit
        return body


@pytest.fixture
def debian(monkeypatch: pytest.MonkeyPatch) -> FakeDebian:
    fake = FakeDebian(monkeypatch)
    monkeypatch.setattr(collect_module, "_http_get", fake.fetch)
    return fake


def project(tmp_path: Path, native_libs: list[str] | None = None) -> Path:
    root = tmp_path / "srv"
    root.mkdir()
    (root / "requirements.txt").write_text("pyodbc==5.2.0\n")
    if native_libs is not None:
        (root / "arcade.toml").write_text(f"[deploy]\nnative_libs = {json.dumps(native_libs)}\n")
        for entry in native_libs:
            (root / entry).mkdir(parents=True, exist_ok=True)
    return root


def write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def collect(root: Path, runners: list[DeploymentsRunner] = RUNNER) -> NativeCollection | None:
    return collect_native_libs(root, load_deploy_config(root), runners, protocol="mcp")


def tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")}


PYODBC = "pyodbc.cpython-312-x86_64-linux-gnu.so"
LIBODBC = "usr/lib/x86_64-linux-gnu/libodbc.so.2"


class TestCollects:
    def test_an_unresolved_library_is_extracted_by_soname_from_a_verified_deb(
        self, tmp_path: Path, debian: FakeDebian, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = project(tmp_path)
        write(root / "app" / PYODBC, elf(needed=("libodbc.so.2", "libc.so.6")))
        library = elf(needed=("libltdl.so.7",))
        debian.add(
            "libodbc2",
            {"usr/lib/x86_64-linux-gnu/libodbc.so.2.0.0": library},
            links={LIBODBC: "libodbc.so.2.0.0"},
        )
        debian.add("libltdl7", {"usr/lib/x86_64-linux-gnu/libltdl.so.7": elf()})
        before = tree(root)

        collection = collect(root)

        assert collection is not None
        assert collection.files() == {
            f"{NATIVE_DIR}/libodbc.so.2": library,
            f"{NATIVE_DIR}/libltdl.so.7": elf(),
        }
        # Nothing is written to the project: the libraries go straight into the bundle.
        assert tree(root) == before
        output = " ".join(capsys.readouterr().out.split())
        assert "libodbc.so.2 from Debian package libodbc2 1.0-1" in output
        assert "libltdl.so.7 from Debian package libltdl7 1.0-1" in output

    def test_vendor_native_is_appended_to_the_authors_native_libs(self, tmp_path: Path) -> None:
        root = project(tmp_path, ["drivers/oracle"])

        settings = runner_settings_json(load_deploy_config(root), [NATIVE_DIR])

        assert json.loads(settings or "") == {"native_libs": ["drivers/oracle", NATIVE_DIR]}

    def test_libraries_inside_bundled_wheels_are_walked(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        (root / "wheels").mkdir()
        with zipfile.ZipFile(
            root / "wheels" / "pyodbc-5.2.0-cp312-manylinux_2_17_x86_64.whl", "w"
        ) as wheel:
            wheel.writestr(f"pyodbc/{PYODBC}", elf(needed=("libodbc.so.2",)))
        debian.add("libodbc2", {LIBODBC: elf()})

        collection = collect(root)

        assert collection is not None
        assert list(collection.files()) == [f"{NATIVE_DIR}/libodbc.so.2"]

    def test_the_runners_architecture_picks_the_debian_index(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeDebian(monkeypatch, arch="arm64")
        monkeypatch.setattr(collect_module, "_http_get", fake.fetch)
        root = project(tmp_path)
        write(root / "ext.so", elf(machine=AARCH64, needed=("libaio.so.1",)))
        fake.add("libaio1t64", {"usr/lib/aarch64-linux-gnu/libaio.so.1": elf(machine=AARCH64)})

        collection = collect(root, ARM_RUNNER)

        assert collection is not None
        assert any("binary-arm64/Packages.xz" in url for url in fake.requests)

    def test_an_engine_without_an_architecture_defaults_to_amd64(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libaio.so.1",)))
        debian.add("libaio1t64", {"usr/lib/x86_64-linux-gnu/libaio.so.1": elf()})

        assert collect(root) is not None
        assert any("binary-amd64/Packages.xz" in url for url in debian.requests)


class TestNotCopied:
    def test_nothing_unresolved_contacts_no_one_and_invents_no_vendor_native(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "app" / PYODBC, elf(needed=("libc.so.6", "libstdc++.so.6", "libm.so.6")))

        assert collect(root) is None
        assert debian.requests == []
        assert not (root / NATIVE_DIR).exists()

    def test_a_project_with_no_libraries_contacts_no_one(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        assert collect(project(tmp_path)) is None
        assert debian.requests == []

    def test_a_wheels_dot_libs_copy_found_through_origin_isnt_copied(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(
            root / "site" / "pkg" / "ext.so",
            elf(needed=("libgfortran-1a2b.so.5",), runpath="$ORIGIN/../pkg.libs"),
        )
        # The vendored copy is never walked, so its own DT_NEEDED isn't collected either.
        write(root / "site" / "pkg.libs" / "libgfortran-1a2b.so.5", elf(needed=("libquad.so.0",)))

        assert collect(root) is None
        assert debian.requests == []

    def test_an_airgapped_author_whose_native_libs_resolve_everything_never_contacts_debian(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def no_network(url: str, limit: int) -> bytes:
            raise AssertionError(f"Debian was contacted: {url}")

        monkeypatch.setattr(collect_module, "_http_get", no_network)
        root = project(tmp_path, ["drivers/odbc", "drivers/krb5"])
        write(root / "app" / PYODBC, elf(needed=("libodbc.so.2", "libc.so.6")))
        write(root / "app" / "gssapi_ext.so", elf(needed=("libgssapi_krb5.so.2",)))
        # The author's own libraries' dependencies resolve through native_libs too.
        write(root / "drivers/odbc/libodbc.so.2", elf(needed=("libltdl.so.7",)))
        write(root / "drivers/odbc/libltdl.so.7", elf())
        write(root / "drivers/krb5/libgssapi_krb5.so.2", elf(needed=("libpthread.so.0",)))

        assert collect(root) is None
        assert not (root / NATIVE_DIR).exists()

    def test_only_what_native_libs_doesnt_provide_is_fetched(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path, ["drivers/odbc"])
        write(root / "app" / PYODBC, elf(needed=("libodbc.so.2", "libaio.so.1")))
        write(root / "drivers/odbc/libodbc.so.2", elf())
        debian.add("libaio1t64", {"usr/lib/x86_64-linux-gnu/libaio.so.1": elf()})

        collection = collect(root)

        assert collection is not None
        assert list(collection.files()) == [f"{NATIVE_DIR}/libaio.so.1"]
        assert not any("libodbc" in url for url in debian.requests)

    def test_a_musl_runner_collects_nothing(self, tmp_path: Path, debian: FakeDebian) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        musl = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]

        assert collect(root, musl) is None
        assert debian.requests == []


class TestRefused:
    def test_an_unreachable_snapshot_names_the_missing_soname(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "app" / PYODBC, elf(needed=("libodbc.so.2",)))
        debian.unreachable = True

        with pytest.raises(DeployRefusedError, match=r"libodbc\.so\.2 \(needed by app/pyodbc"):
            collect(root)

    def test_a_soname_no_debian_package_provides_is_named(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libmsodbcsql-18.so.1",)))

        with pytest.raises(DeployRefusedError, match=r"libmsodbcsql-18\.so\.1 .*native_libs"):
            collect(root)

    def test_a_deb_that_doesnt_match_its_index_hash(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        debian.add("libodbc2", {LIBODBC: elf()})
        debian.tamper.add("libodbc2")

        with pytest.raises(DeployRefusedError, match="doesn't match the SHA256"):
            collect(root)

    def test_an_inrelease_that_isnt_the_pinned_one(
        self, tmp_path: Path, debian: FakeDebian, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        debian.add("libodbc2", {LIBODBC: elf()})
        original = debian.fetch

        def forged(url: str, limit: int) -> bytes:
            body = original(url, limit)
            if url.endswith("InRelease"):
                monkeypatch.setattr(collect_module, "DEBIAN_INRELEASE_SHA256", "0" * 64)
            return body

        monkeypatch.setattr(collect_module, "_http_get", forged)

        with pytest.raises(DeployRefusedError, match="InRelease"):
            collect(root)

    def test_a_bundled_library_needing_a_newer_glibc_names_both_versions(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",), glibc="GLIBC_2.43"))

        with pytest.raises(DeployRefusedError, match=r"needs glibc 2\.43.*has glibc 2\.41"):
            collect(root)
        assert debian.requests == []

    def test_a_debian_library_needing_a_newer_glibc_names_both_versions(
        self, tmp_path: Path, debian: FakeDebian
    ) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        debian.add("libodbc2", {LIBODBC: elf(glibc="GLIBC_2.42")})

        with pytest.raises(DeployRefusedError, match=r"libodbc2.*glibc 2\.42.*glibc 2\.41"):
            collect(root)

    def test_libraries_over_the_bundle_cap_name_the_cap(
        self, tmp_path: Path, debian: FakeDebian, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(collect_module, "MAX_UNCOMPRESSED_BUNDLE_BYTES", 1 << 20)
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        debian.add("libodbc2", {LIBODBC: elf(padding=(1 << 20) + 1)})

        with pytest.raises(DeployRefusedError, match="1 MiB bundle size cap"):
            collect(root)

    def test_the_real_cap_is_256_mib(self) -> None:
        assert collect_module.MAX_UNCOMPRESSED_BUNDLE_BYTES >> 20 == 256

    def test_an_existing_vendor_native_directory(self, tmp_path: Path, debian: FakeDebian) -> None:
        root = project(tmp_path)
        write(root / "ext.so", elf(needed=("libodbc.so.2",)))
        (root / NATIVE_DIR).mkdir(parents=True)

        with pytest.raises(DeployRefusedError, match="already has vendor/native"):
            collect(root)
        assert debian.requests == []


class TestPackageNames:
    @pytest.mark.parametrize(
        ("soname", "package"),
        [
            ("libodbc.so.2", "libodbc2"),
            ("libgssapi_krb5.so.2", "libgssapi-krb5-2"),
            ("libaio.so.1", "libaio1"),
            ("libltdl.so.7", "libltdl7"),
            ("libsqlite3.so.0", "libsqlite3-0"),
        ],
    )
    def test_debian_policy_names(self, soname: str, package: str) -> None:
        assert package_names(soname) == [package, f"{package}t64"]

    def test_a_name_without_a_version_has_none(self) -> None:
        assert package_names("libfoo.so") == []


# The snapshot and the SHA256 of its InRelease file move together: update both, and this
# table, when moving the snapshot.
PINNED_SNAPSHOTS = {
    "20261101T022418Z": "0584fba32e13e0ab8285fb16c27adea1ec03a73669c18702821094fd6ca86675",
}


class TestSnapshotDrift:
    def test_the_snapshot_and_its_inrelease_hash_move_together(self) -> None:
        assert PINNED_SNAPSHOTS.get(DEBIAN_SNAPSHOT) == DEBIAN_INRELEASE_SHA256

    def test_the_snapshot_is_a_dated_snapshot_in_the_past(self) -> None:
        assert re.fullmatch(r"\d{8}T\d{6}Z", DEBIAN_SNAPSHOT)
        taken = datetime.strptime(DEBIAN_SNAPSHOT, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        assert taken < datetime.now(timezone.utc)
        assert DEBIAN_SNAPSHOT_URL.endswith(f"/archive/debian/{DEBIAN_SNAPSHOT}")

    @pytest.mark.skipif(
        not os.environ.get("ARCADE_TEST_DEBIAN_SNAPSHOT"),
        reason="contacts snapshot.debian.org; set ARCADE_TEST_DEBIAN_SNAPSHOT=1",
    )
    def test_the_live_snapshot_still_serves_the_pinned_inrelease(self) -> None:
        release = collect_module._http_get(f"{DEBIAN_SNAPSHOT_URL}/dists/trixie/InRelease", 1 << 20)

        assert hashlib.sha256(release).hexdigest() == DEBIAN_INRELEASE_SHA256
        assert b"Codename: trixie" in release
