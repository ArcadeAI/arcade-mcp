from datetime import datetime, timedelta

import pytest
from arcade_core.config_model import AuthConfig, Config, ContextConfig, UserConfig
from typer.testing import CliRunner

from arcade_cli.main import cli


@pytest.fixture
def isolated_config_dir(tmp_path, monkeypatch):
    # Config.get_config_file_path() reads ARCADE_WORK_DIR dynamically.
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    # CREDENTIALS_FILE_PATH in arcade_core.constants is frozen at import time
    # and does NOT honor ARCADE_WORK_DIR; the main CLI callback uses it to gate
    # logged-in commands. Point it at the same file Config writes to so the
    # gate sees the staged credentials.
    credentials_file = str(tmp_path / "credentials.yaml")
    monkeypatch.setattr("arcade_cli.authn.CREDENTIALS_FILE_PATH", credentials_file)
    return tmp_path


@pytest.fixture
def runner():
    return CliRunner()


def _staged_auth() -> AuthConfig:
    return AuthConfig(
        access_token="x",
        refresh_token="y",
        expires_at=datetime.now() + timedelta(hours=1),
    )


def _staged_context() -> ContextConfig:
    return ContextConfig(
        org_id="org_1",
        org_name="Org One",
        project_id="proj_1",
        project_name="Proj One",
    )


def test_whoami_prints_both_urls_when_engine_url_saved(isolated_config_dir, runner) -> None:
    Config(
        coordinator_url="https://cloud.example.dev",
        engine_url="https://api.example.dev",
        auth=_staged_auth(),
        user=UserConfig(email="someone@example.dev"),
        context=_staged_context(),
    ).save_to_file()

    result = runner.invoke(cli, ["whoami"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "https://cloud.example.dev" in result.stdout
    assert "https://api.example.dev" in result.stdout


def test_whoami_prints_fallback_engine_url_when_unsaved(isolated_config_dir, runner) -> None:
    Config(
        coordinator_url="https://cloud.arcade.dev",
        auth=_staged_auth(),
        user=UserConfig(email="someone@example.dev"),
        context=_staged_context(),
    ).save_to_file()

    result = runner.invoke(cli, ["whoami"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "https://cloud.arcade.dev" in result.stdout
    assert "https://api.arcade.dev" in result.stdout
