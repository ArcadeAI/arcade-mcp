"""The check for dependencies with no prebuilt wheel for the runner."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from arcade_cli import deploy_wheels
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_wheels import check_wheels

MUSL = DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")


@dataclass
class FakeUv:
    """Stands in for uv: resolves to ``resolution`` and fails wheel checks for ``no_wheels``.

    ``no_wheels`` and ``failures`` are keyed by architecture. A failure makes every uv call
    for that architecture fail as a network error would.
    """

    resolution: list[str] = field(default_factory=lambda: ["httpx==0.28.1"])
    no_wheels: dict[str, set[str]] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    export: str = ""
    calls: list[tuple[list[str], str]] = field(default_factory=list)

    def __call__(
        self, args: list[str], stdin: str, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((args, stdin))
        if args[0] == "export":
            return subprocess.CompletedProcess(args, 0, self.export, "")
        arch = args[args.index("--python-platform") + 1].split("-")[0]
        if arch in self.failures:
            return subprocess.CompletedProcess(args, 2, "", self.failures[arch])
        if "--only-binary" not in args:
            return subprocess.CompletedProcess(args, 0, "\n".join(self.resolution) + "\n", "")
        for line in stdin.splitlines():
            name, version = line.split("==")
            if name in self.no_wheels.get(arch, set()):
                return subprocess.CompletedProcess(
                    args,
                    1,
                    "",
                    "error: No solution found when resolving dependencies\n"
                    f"  cause: Because {name}=={version} has no usable wheels and you require "
                    f"{name}=={version}, we can conclude that your requirements are "
                    "unsatisfiable.\n",
                )
        return subprocess.CompletedProcess(args, 0, stdin, "")

    def resolves(self) -> list[tuple[list[str], str]]:
        return [
            c for c in self.calls if c[0][:2] == ["pip", "compile"] and "--only-binary" not in c[0]
        ]

    def checks(self) -> list[tuple[list[str], str]]:
        return [c for c in self.calls if "--only-binary" in c[0]]


def project(tmp_path: Path, requirements: str = "httpx\n") -> Path:
    (tmp_path / "requirements.txt").write_text(requirements)
    return tmp_path


def option(args: list[str], name: str) -> str:
    return args[args.index(name) + 1]


class TestMissingWheels:
    def test_packages_without_wheels_are_named_with_hints_and_architecture_notes(
        self, tmp_path: Path
    ) -> None:
        uv = FakeUv(
            resolution=["cx-oracle==8.3.0", "httpx==0.28.1", "mysqlclient==2.3.0", "orjson==3.11"],
            no_wheels={
                "x86_64": {"cx-oracle", "mysqlclient"},
                "aarch64": {"cx-oracle", "mysqlclient", "orjson"},
            },
        )

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert result.notes == []
        assert result.warnings == [
            "These packages have no prebuilt wheel for the runner (musllinux_1_2, Python 3.12), "
            "so they compile at deploy, which is slow, can fail without system headers, and "
            "will fail once the runner drops its compilers: cx-oracle 8.3.0 (use oracledb "
            "instead), mysqlclient 2.3.0 (use PyMySQL instead), orjson 3.11 (aarch64 only)."
        ]

    def test_psycopg2_hints_the_binary_psycopg(self, tmp_path: Path) -> None:
        uv = FakeUv(
            resolution=["psycopg2==2.9.10"],
            no_wheels={"x86_64": {"psycopg2"}, "aarch64": {"psycopg2"}},
        )

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert "psycopg2 2.9.10 (use psycopg[binary] instead)" in result.warnings[0]

    def test_every_package_with_wheels_means_no_warning_and_one_check_per_architecture(
        self, tmp_path: Path
    ) -> None:
        uv = FakeUv(resolution=["anyio==4.16.0", "httpx==0.28.1"])

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert result.warnings == [] and result.notes == []
        assert [stdin for _, stdin in uv.checks()] == ["anyio==4.16.0\nhttpx==0.28.1\n"] * 2

    def test_a_failed_batch_checks_each_package_on_its_own(self, tmp_path: Path) -> None:
        uv = FakeUv(
            resolution=["anyio==4.16.0", "mysqlclient==2.3.0"],
            no_wheels={"x86_64": {"mysqlclient"}, "aarch64": {"mysqlclient"}},
        )

        check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        singles = sorted(stdin for _, stdin in uv.checks() if stdin.count("\n") == 1)
        assert singles == ["anyio==4.16.0\n"] * 2 + ["mysqlclient==2.3.0\n"] * 2

    def test_direct_and_local_references_are_not_checked(self, tmp_path: Path) -> None:
        uv = FakeUv(resolution=["-e ./libs/helper", "helper @ file:///x/helper", "httpx==0.28.1"])

        check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert {stdin for _, stdin in uv.checks()} == {"httpx==0.28.1\n"}


class TestWhatTheRunnerInstalls:
    def test_a_lock_is_exported_first(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text("version = 1\n")
        project(tmp_path, "ignored-because-of-the-lock\n")
        uv = FakeUv(export="httpx==0.28.1\n")

        check_wheels(tmp_path, protocol="mcp", runners=[MUSL], run_uv=uv)

        first_args, _ = uv.calls[0]
        assert first_args[:4] == ["export", "--frozen", "--no-dev", "--no-hashes"]
        assert "--no-emit-project" in first_args
        assert {stdin for _, stdin in uv.resolves()} == {"httpx==0.28.1\n"}

    def test_a_lock_that_cant_be_exported_is_an_unfinished_check(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text("version = 1\n")

        def failing(args: list[str], stdin: str, timeout: int) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 2, "", "error: The lockfile is outdated\n")

        result = check_wheels(tmp_path, protocol="mcp", runners=[MUSL], run_uv=failing)

        assert result.warnings == []
        assert result.notes == [
            "The wheel check didn't finish: exporting uv.lock failed: "
            "error: The lockfile is outdated"
        ]

    def test_requirements_txt_is_passed_as_a_path_not_on_stdin(self, tmp_path: Path) -> None:
        # uv can't parse an `-r C:\...` line read from stdin, so Windows paths broke the check.
        uv = FakeUv()

        check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        for args, stdin in uv.resolves():
            assert args[2] == str(tmp_path / "requirements.txt")
            assert stdin == ""

    def test_fastmcp_json_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "fastmcp.json").write_text(
            json.dumps({"environment": {"dependencies": ["fastmcp>=2", "mysqlclient"]}})
        )
        project(tmp_path, "ignored-because-of-fastmcp-json\n")
        uv = FakeUv()

        check_wheels(tmp_path, protocol="mcp", runners=[MUSL], run_uv=uv)

        assert {stdin for _, stdin in uv.resolves()} == {"fastmcp>=2\nmysqlclient\n"}

    def test_pyproject_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "srv"\nversion = "1"\ndependencies = ["httpx>=0.27"]\n'
        )
        uv = FakeUv()

        check_wheels(tmp_path, protocol="mcp", runners=[MUSL], run_uv=uv)

        assert {stdin for _, stdin in uv.resolves()} == {"httpx>=0.27\n"}

    def test_the_runners_python_and_platform_are_used(self, tmp_path: Path) -> None:
        uv = FakeUv()
        runner = DeploymentsRunner(language="python", version="3.13", platform="manylinux_2_41")

        check_wheels(project(tmp_path), protocol="mcp", runners=[runner], run_uv=uv)

        assert {option(args, "--python-version") for args, _ in uv.calls} == {"3.13"}
        assert sorted({option(args, "--python-platform") for args, _ in uv.calls}) == [
            "aarch64-manylinux_2_40",
            "x86_64-manylinux_2_40",
        ]

    def test_resolving_allows_source_builds_and_checking_does_not(self, tmp_path: Path) -> None:
        uv = FakeUv()

        check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert all(
            "--only-binary" not in args and "--no-build" not in args for args, _ in uv.resolves()
        )
        assert all(option(args, "--only-binary") == ":all:" for args, _ in uv.checks())

    def test_index_options_are_carried_into_every_check(self, tmp_path: Path) -> None:
        wheels = tmp_path / "wheels"
        wheels.mkdir()
        (tmp_path / "private.txt").write_text(
            "--index-url https://pypi.internal/simple\n"
            "--extra-index-url=https://extra.internal/simple\n"
            "-f wheels\n"
            "internal-sdk==1.0\n"
        )
        uv = FakeUv(
            resolution=["internal-sdk==1.0", "mysqlclient==2.3.0"],
            no_wheels={"x86_64": {"mysqlclient"}, "aarch64": {"mysqlclient"}},
        )

        check_wheels(
            project(tmp_path, "-r private.txt\nmysqlclient\n"),
            protocol="mcp",
            runners=[MUSL],
            run_uv=uv,
        )

        expected = [
            "--index-url",
            "https://pypi.internal/simple",
            "--extra-index-url",
            "https://extra.internal/simple",
            "--find-links",
            str(wheels.resolve()),
        ]
        compiles = [args for args, _ in uv.calls if args[:2] == ["pip", "compile"]]
        assert len(compiles) == 2 * (1 + 1 + 2)  # per architecture: resolve, batch, singles
        for args in compiles:
            assert args[-len(expected) :] == expected


class TestUnfinishedChecks:
    NETWORK_ERROR = (
        "error: Request failed after 3 retries\n"
        "  cause: Failed to fetch: https://pypi.org/simple/httpx/\n"
        "  cause: Connection refused (os error 111)\n"
    )

    def test_a_network_failure_names_no_packages(self, tmp_path: Path) -> None:
        uv = FakeUv(failures={"x86_64": self.NETWORK_ERROR, "aarch64": self.NETWORK_ERROR})

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert result.warnings == []
        assert result.notes == [
            f"The wheel check for the runner (musllinux_1_2, Python 3.12, {arch}) didn't "
            "finish: error: Request failed after 3 retries (Connection refused (os error 111))"
            for arch in ("x86_64", "aarch64")
        ]

    def test_one_failed_architecture_keeps_the_others_results(self, tmp_path: Path) -> None:
        uv = FakeUv(
            resolution=["mysqlclient==2.3.0"],
            no_wheels={"x86_64": {"mysqlclient"}},
            failures={"aarch64": self.NETWORK_ERROR},
        )

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=uv)

        assert len(result.warnings) == 1
        assert "mysqlclient 2.3.0 (x86_64 only; use PyMySQL instead)" in result.warnings[0]
        assert len(result.notes) == 1
        assert "aarch64) didn't finish" in result.notes[0]

    def test_a_single_check_failing_otherwise_keeps_the_named_packages(
        self, tmp_path: Path
    ) -> None:
        uv = FakeUv(
            resolution=["flaky==1.0", "mysqlclient==2.3.0"],
            no_wheels={"x86_64": {"mysqlclient"}, "aarch64": {"mysqlclient"}},
        )
        inner = uv.__call__

        def run(args: list[str], stdin: str, timeout: int) -> subprocess.CompletedProcess[str]:
            if stdin == "flaky==1.0\n":
                return subprocess.CompletedProcess(args, 2, "", "error: index returned 503\n")
            return inner(args, stdin, timeout)

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL], run_uv=run)

        assert "mysqlclient 2.3.0" in result.warnings[0]
        assert "flaky" not in result.warnings[0]
        assert all("flaky 1.0: error: index returned 503" in note for note in result.notes)


class TestWhichRunner:
    @pytest.mark.parametrize(
        ("platform", "target"),
        [
            ("musllinux_1_2", "unknown-linux-musl"),
            ("manylinux_2_41", "manylinux_2_40"),
            ("manylinux_2_40", "manylinux_2_40"),
            ("manylinux_2_30", "manylinux_2_28"),
            ("manylinux_2_28", "manylinux_2_28"),
            ("manylinux_2_20", "manylinux_2_17"),
            ("manylinux2014", "manylinux2014"),
        ],
    )
    def test_each_platform_maps_to_the_newest_uv_target_its_libc_runs(
        self, tmp_path: Path, platform: str, target: str
    ) -> None:
        uv = FakeUv()
        runner = DeploymentsRunner(language="python", version="3.12", platform=platform)

        check_wheels(project(tmp_path), protocol="mcp", runners=[runner], run_uv=uv)

        assert sorted({option(args, "--python-platform") for args, _ in uv.calls}) == [
            f"aarch64-{target}",
            f"x86_64-{target}",
        ]

    @pytest.mark.parametrize("platform", ["", "manylinux_2_5", "win_amd64"])
    def test_a_platform_uv_cant_target_is_skipped_with_a_note(
        self, tmp_path: Path, platform: str
    ) -> None:
        uv = FakeUv()
        runner = DeploymentsRunner(language="python", version="3.12", platform=platform)

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[runner], run_uv=uv)

        assert uv.calls == []
        assert result.warnings == []
        assert "weren't checked for prebuilt wheels" in result.notes[0]

    def test_other_languages_are_skipped(self, tmp_path: Path) -> None:
        uv = FakeUv()
        node = DeploymentsRunner(language="node", version="22", platform="musllinux_1_2")

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[node], run_uv=uv)

        assert uv.calls == []
        assert result.warnings == [] and result.notes == []

    def test_without_uv_the_check_is_skipped_with_a_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(deploy_wheels.shutil, "which", lambda name: None)

        result = check_wheels(project(tmp_path), protocol="mcp", runners=[MUSL])

        assert result.warnings == []
        assert result.notes == [
            "uv isn't on PATH, so dependencies weren't checked for prebuilt wheels for the "
            "runner. Install uv to have them checked."
        ]


@pytest.mark.deploy_matrix
@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_real_uv_names_packages_without_wheels(tmp_path: Path) -> None:
    project(tmp_path, "mysqlclient\npsycopg2\nhttpx\n")

    result = check_wheels(tmp_path, protocol="mcp", runners=[MUSL])

    assert result.notes == []
    [warning] = result.warnings
    assert "mysqlclient " in warning
    assert "psycopg2 " in warning
    assert "httpx" not in warning
