import pytest
from arcade_cli._startup_environment import capture as pin_ci_environment
from arcade_cli.context import ARCADE_API_KEY_ENV, ARCADE_URL_ENV, resolve_ci_context


@pytest.fixture(autouse=True)
def no_ambient_credentials(monkeypatch):
    monkeypatch.delenv(ARCADE_URL_ENV, raising=False)
    monkeypatch.delenv(ARCADE_API_KEY_ENV, raising=False)


def _load_a_project_env_file(monkeypatch) -> None:
    monkeypatch.setenv(ARCADE_URL_ENV, "https://engine.acme.internal")
    monkeypatch.setenv(ARCADE_API_KEY_ENV, "the-project-key")


class TestCIEnvironmentPinning:
    def test_a_project_env_file_cannot_introduce_ci_credentials(self, monkeypatch):
        pin_ci_environment()
        _load_a_project_env_file(monkeypatch)

        assert resolve_ci_context() is None

    def test_credentials_present_at_start_still_drive_ci(self, monkeypatch):
        monkeypatch.setenv(ARCADE_URL_ENV, "https://engine.acme.internal")
        monkeypatch.setenv(ARCADE_API_KEY_ENV, "the-ci-key")

        pin_ci_environment()

        resolved = resolve_ci_context()
        assert resolved is not None
        assert resolved.is_ci is True
        assert resolved.api_key == "the-ci-key"

    def test_a_project_env_file_cannot_replace_the_ci_credentials(self, monkeypatch):
        monkeypatch.setenv(ARCADE_URL_ENV, "https://engine.acme.internal")
        monkeypatch.setenv(ARCADE_API_KEY_ENV, "the-ci-key")

        pin_ci_environment()
        _load_a_project_env_file(monkeypatch)

        resolved = resolve_ci_context()
        assert resolved is not None
        assert resolved.api_key == "the-ci-key"

    def test_without_pinning_the_environment_is_read_live(self, monkeypatch):
        monkeypatch.setenv(ARCADE_URL_ENV, "https://engine.acme.internal")
        monkeypatch.setenv(ARCADE_API_KEY_ENV, "the-ci-key")

        resolved = resolve_ci_context()
        assert resolved is not None
        assert resolved.api_key == "the-ci-key"


IMPORT_THE_CLI_THEN_ASK = """
import arcade_cli.main  # noqa: F401
from arcade_cli.context import resolve_ci_context

print("CI" if resolve_ci_context() is not None else "NOT_CI")
"""


class TestTheProjectEnvFileLoadedByImports:
    def test_importing_the_cli_cannot_arm_ci_mode(self, tmp_path):
        import os
        import subprocess
        import sys

        (tmp_path / ".env").write_text(
            "ARCADE_URL=https://engine.acme.internal\nARCADE_API_KEY=the-project-key\n"
        )

        environment = {
            k: v for k, v in os.environ.items() if k not in {ARCADE_URL_ENV, ARCADE_API_KEY_ENV}
        }

        result = subprocess.run(
            [sys.executable, "-c", IMPORT_THE_CLI_THEN_ASK],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().splitlines()[-1] == "NOT_CI"
