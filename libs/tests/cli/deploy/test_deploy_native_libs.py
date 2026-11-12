"""Warnings about shared libraries in native_libs that the runner can't load."""

import struct
from pathlib import Path

import pytest
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_config import load_deploy_config
from arcade_cli.deploy_native_libs import native_lib_warnings, read_elf

X86_64, AARCH64, I386 = 62, 183, 3
GLIBC_RUNNER = [DeploymentsRunner(language="python", version="3.12", platform="manylinux_2_41")]
MUSL_RUNNER = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]


def elf(
    *,
    machine: int = X86_64,
    needed: tuple[str, ...] = ("libc.so.6",),
    versions: tuple[str, ...] = ("GLIBC_2.17",),
    interp: bytes | None = None,
    bits: int = 64,
) -> bytes:
    """A minimal ELF shared library: a header, program headers, a dynamic section."""
    ident = b"\x7fELF" + bytes([2 if bits == 64 else 1, 1, 1]) + bytes(9)
    if bits != 64:
        return ident + struct.pack("<HH", 3, machine) + bytes(44)

    strings = b"\0"
    offsets = []
    for name in (*needed, *versions):
        offsets.append(len(strings))
        strings += name.encode() + b"\0"
    phnum = 3 if interp else 2
    strtab_at = 64 + phnum * 56
    interp_at = strtab_at + len(strings)
    dynamic_at = interp_at + (len(interp) if interp else 0)
    base = 0x400000
    entries = [(1, offsets[i]) for i in range(len(needed))]
    entries += [(5, base + strtab_at), (10, len(strings)), (0, 0)]
    dynamic = b"".join(struct.pack("<qQ", tag, value) for tag, value in entries)
    size = dynamic_at + len(dynamic)

    header = ident + struct.pack(
        "<HHIQQQIHHHHHH", 3, machine, 1, 0, 64, 0, 0, 64, 56, phnum, 64, 0, 0
    )
    phdrs = struct.pack("<IIQQQQQQ", 1, 5, 0, base, base, size, size, 0x1000)
    phdrs += struct.pack(
        "<IIQQQQQQ", 2, 6, dynamic_at, base + dynamic_at, 0, len(dynamic), len(dynamic), 8
    )
    if interp:
        phdrs += struct.pack("<IIQQQQQQ", 3, 4, interp_at, 0, 0, len(interp), len(interp), 1)
    return header + phdrs + strings + (interp or b"") + dynamic


def project(tmp_path: Path, libraries: dict[str, bytes]) -> Path:
    (tmp_path / "arcade.toml").write_text('[deploy]\nnative_libs = ["vendor/odbc"]\n')
    for name, content in libraries.items():
        path = tmp_path / "vendor" / "odbc" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (tmp_path / "vendor" / "odbc").mkdir(parents=True, exist_ok=True)
    return tmp_path


def warnings(project_dir: Path, runners: list[DeploymentsRunner] = GLIBC_RUNNER) -> list[str]:
    return native_lib_warnings(project_dir, load_deploy_config(project_dir), runners)


class TestReadElf:
    def test_a_glibc_library(self, tmp_path: Path) -> None:
        (tmp_path / "libx.so").write_bytes(elf(versions=("GLIBC_2.17", "GLIBC_2.34")))

        info = read_elf(tmp_path / "libx.so")

        assert (info.machine, info.libc, info.glibc) == ("x86_64", "glibc", (2, 34))

    def test_a_musl_library(self, tmp_path: Path) -> None:
        (tmp_path / "libx.so").write_bytes(elf(needed=("libc.musl-x86_64.so.1",), versions=()))

        assert read_elf(tmp_path / "libx.so").libc == "musl"

    def test_a_musl_interpreter(self, tmp_path: Path) -> None:
        data = elf(needed=(), versions=(), interp=b"/lib/ld-musl-x86_64.so.1\0")
        (tmp_path / "libx.so").write_bytes(data)

        assert read_elf(tmp_path / "libx.so").libc == "musl"

    @pytest.mark.skipif(
        not Path("/lib/x86_64-linux-gnu/libc.so.6").is_file(), reason="needs glibc on x86_64"
    )
    def test_the_systems_own_libc(self) -> None:
        info = read_elf(Path("/lib/x86_64-linux-gnu/libc.so.6"))

        assert (info.machine, info.libc) == ("x86_64", "glibc")
        assert info.glibc is not None


class TestWarnings:
    def test_matching_libraries_have_no_warning(self, tmp_path: Path) -> None:
        project(
            tmp_path,
            {
                "libmsodbcsql-18.so.1.1": elf(versions=("GLIBC_2.17", "GLIBC_2.38")),
                "libarm.so": elf(machine=AARCH64),
                "README.txt": b"not a library",
            },
        )

        assert warnings(tmp_path) == []

    @pytest.mark.parametrize(
        ("content", "reason"),
        [
            (b"\xcf\xfa\xed\xfe" + bytes(60), "macOS (Mach-O)"),
            (b"MZ" + bytes(62), "Windows (PE)"),
            (elf(bits=32, machine=I386), "32-bit ELF"),
            (elf(machine=I386), "x86 (32-bit)"),
            (elf(needed=("libc.musl-x86_64.so.1",), versions=()), "built against musl"),
            (elf(versions=("GLIBC_2.42",)), "needs glibc 2.42"),
        ],
        ids=["mach-o", "pe", "elf32", "i386", "musl", "newer glibc"],
    )
    def test_a_library_the_runner_cant_load_is_warned(
        self, tmp_path: Path, content: bytes, reason: str
    ) -> None:
        project(tmp_path, {"libodbc.so.2": content})

        [warning] = warnings(tmp_path)

        assert "vendor/odbc/libodbc.so.2" in warning
        assert reason in warning

    def test_a_glibc_library_on_a_musl_runner_is_warned(self, tmp_path: Path) -> None:
        project(tmp_path, {"libodbc.so": elf()})

        [warning] = warnings(tmp_path, MUSL_RUNNER)

        assert "built against glibc" in warning

    @pytest.mark.parametrize("platform", ["", "macosx_14_0", "linux"])
    def test_no_readable_runner_platform_skips_the_check(
        self, tmp_path: Path, platform: str
    ) -> None:
        project(tmp_path, {"libodbc.so": b"MZ" + bytes(62)})
        runners = [DeploymentsRunner(language="python", version="3.12", platform=platform)]

        assert warnings(tmp_path, runners) == []
        assert warnings(tmp_path, []) == []

    def test_no_native_libs_reads_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "libodbc.so").write_bytes(b"MZ")

        assert warnings(tmp_path) == []

    def test_libraries_with_one_problem_share_a_warning(self, tmp_path: Path) -> None:
        mach_o = b"\xcf\xfa\xed\xfe" + bytes(60)
        project(tmp_path, {f"lib{i}.so": mach_o for i in range(7)})

        [warning] = warnings(tmp_path)

        assert "and 2 more" in warning
