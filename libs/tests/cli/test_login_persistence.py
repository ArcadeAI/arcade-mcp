import pytest
from arcade_core.auth_tokens import TokenResponse
from arcade_core.config_model import Config

from arcade_cli.authn import OrgInfo, ProjectInfo, WhoAmIResponse, save_credentials_from_whoami


@pytest.fixture
def isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    return tmp_path


def _fake_tokens() -> TokenResponse:
    return TokenResponse(
        access_token="access",
        refresh_token="refresh",
        expires_in=3600,
        token_type="Bearer",
    )


def _fake_whoami() -> WhoAmIResponse:
    return WhoAmIResponse(
        account_id="acct_1",
        email="someone@example.dev",
        organizations=[OrgInfo(org_id="org_1", name="Org One", is_default=True)],
        projects=[ProjectInfo(project_id="proj_1", name="Proj One", is_default=True)],
    )


def test_save_credentials_persists_engine_url(isolated_config_dir) -> None:
    save_credentials_from_whoami(
        tokens=_fake_tokens(),
        whoami=_fake_whoami(),
        coordinator_url="https://cloud.example.dev",
        engine_url="https://api.example.dev",
    )

    cfg = Config.load_from_file()
    assert cfg.coordinator_url == "https://cloud.example.dev"
    assert cfg.engine_url == "https://api.example.dev"


def test_save_credentials_without_engine_url_leaves_field_unset(isolated_config_dir) -> None:
    save_credentials_from_whoami(
        tokens=_fake_tokens(),
        whoami=_fake_whoami(),
        coordinator_url="https://cloud.arcade.dev",
    )

    cfg = Config.load_from_file()
    assert cfg.coordinator_url == "https://cloud.arcade.dev"
    assert cfg.engine_url is None
