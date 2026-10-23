"""Warning about dependencies with no prebuilt wheel for the runner (DEP-393)."""

import shutil
import subprocess
from pathlib import Path

import pytest
from arcade_cli import deploy_wheels
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy_wheels import uv_targets, wheel_warnings

MUSL = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]

RESOLVED = ["httpx==0.28.1", "mysqlclient==2.3.0", "psycopg2==2.9.13", "fastjson==1.0.0"]
# Packages with no wheel, and the architectures they lack one for.
NO_WHEEL = {
    "mysqlclient": {"x86_64", "aarch64"},
    "psycopg2": {"x86_64", "aarch64"},
    "fastjson": {"aarch64"},
}


class FakeUv:
    """Stands in for uv: resolves to RESOLVED and has no wheels for NO_WHEEL."""

    def __init__(self, resolved: list[str] = RESOLVED, resolve_error: str | None = None) -> None:
        self.calls: list[list[str]] = []
        self.resolved = resolved
        self.resolve_error = resolve_error

    def __call__(
        self, args: list[str], cwd: Path, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:1] == ["export"]:
            return self._done("httpx==0.28.1\n")
        arch = args[args.index("--python-platform") + 1].split("-")[0]
        if "--only-binary" not in args:
            if self.resolve_error:
                return self._done("", 1, self.resolve_error)
            return self._done("\n".join(self.resolved) + "\n")
        pins = stdin if stdin is not None else Path(cwd, args[2]).read_text()
        names = [line.split("==")[0] for line in pins.split()]
        missing = [name for name in names if arch in NO_WHEEL.get(name, set())]
        if missing:
            return self._done("", 1, f"Because {missing[0]} has no usable wheels ...")
        return self._done(pins)

    def _done(self, out: str, code: int = 0, err: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], code, out, err)


def use(monkeypatch: pytest.MonkeyPatch, fake: FakeUv) -> FakeUv:
    monkeypatch.setattr(deploy_wheels, "_run_uv", fake)
    monkeypatch.setattr(deploy_wheels, "_find_uv", lambda: "uv")
    return fake


@pytest.fixture
def fake_uv(monkeypatch: pytest.MonkeyPatch) -> FakeUv:
    return use(monkeypatch, FakeUv())


class TestTargets:
    def test_musllinux_checks_both_architectures(self) -> None:
        assert uv_targets("musllinux_1_2") == [
            ("x86_64", "x86_64-unknown-linux-musl"),
            ("aarch64", "aarch64-unknown-linux-musl"),
        ]

    def test_a_newer_manylinux_than_uv_knows_uses_its_newest(self) -> None:
        assert uv_targets("manylinux_2_41") == [
            ("x86_64", "x86_64-manylinux_2_40"),
            ("aarch64", "aarch64-manylinux_2_40"),
        ]

    def test_an_unknown_platform_has_no_targets(self) -> None:
        assert uv_targets("win_amd64") == []
        assert uv_targets("") == []


class TestWheelWarnings:
    def test_packages_without_wheels_are_named_with_hints(
        self, tmp_path: Path, fake_uv: FakeUv
    ) -> None:
        (tmp_path / "requirements.txt").write_text("httpx\nmysqlclient\npsycopg2\nfastjson\n")

        warnings = wheel_warnings(tmp_path, "requirements.txt", MUSL)

        assert len(warnings) == 1
        warning = warnings[0]
        assert "musllinux_1_2, Python 3.12" in warning
        assert "mysqlclient 2.3.0 (use PyMySQL instead)" in warning
        assert "psycopg2 2.9.13 (use psycopg[binary] instead)" in warning
        assert "fastjson 1.0.0 (aarch64 only)" in warning
        assert "httpx" not in warning

    def test_all_wheels_present_is_quiet_and_needs_one_check_per_architecture(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = use(monkeypatch, FakeUv(resolved=["httpx==0.28.1", "anyio==4.15.1"]))
        (tmp_path / "requirements.txt").write_text("httpx\n")

        assert wheel_warnings(tmp_path, "requirements.txt", MUSL) == []
        assert sum("--only-binary" in call for call in fake.calls) == 2

    def test_a_lock_is_exported_first(self, tmp_path: Path, fake_uv: FakeUv) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "srv"\nversion = "0"\n')
        (tmp_path / "uv.lock").write_text("")

        wheel_warnings(tmp_path, "uv.lock", MUSL)

        assert fake_uv.calls[0][:1] == ["export"]
        assert "--frozen" in fake_uv.calls[0]
        assert "--no-dev" in fake_uv.calls[0]

    def test_resolution_uses_the_runners_python(self, tmp_path: Path, fake_uv: FakeUv) -> None:
        (tmp_path / "requirements.txt").write_text("httpx\n")

        wheel_warnings(tmp_path, "requirements.txt", MUSL)

        resolve = fake_uv.calls[0]
        assert resolve[resolve.index("--python-version") + 1] == "3.12"

    def test_a_failed_resolution_is_a_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use(monkeypatch, FakeUv(resolve_error="error: nope\n"))
        (tmp_path / "requirements.txt").write_text("httpx\n")

        warnings = wheel_warnings(tmp_path, "requirements.txt", MUSL)

        assert any("Couldn't resolve" in w and "error: nope" in w for w in warnings)

    def test_without_uv_the_check_is_skipped_with_a_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(deploy_wheels, "_find_uv", lambda: None)
        (tmp_path / "requirements.txt").write_text("httpx\n")

        assert wheel_warnings(tmp_path, "requirements.txt", MUSL) == [
            "Skipped the check for prebuilt wheels: uv isn't installed."
        ]

    def test_an_engine_without_a_platform_skips_the_check(
        self, tmp_path: Path, fake_uv: FakeUv
    ) -> None:
        runners = [DeploymentsRunner(language="python", version="3.12")]

        assert wheel_warnings(tmp_path, "requirements.txt", runners) == []
        assert fake_uv.calls == []


@pytest.mark.deploy_matrix
@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_real_uv_finds_the_packages_that_compile(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("httpx\nmysqlclient\npsycopg2\n")

    warnings = wheel_warnings(tmp_path, "requirements.txt", MUSL)

    assert len(warnings) == 1
    assert "mysqlclient" in warnings[0]
    assert "PyMySQL" in warnings[0]
    assert "psycopg2" in warnings[0]
    assert "httpx" not in warnings[0]
