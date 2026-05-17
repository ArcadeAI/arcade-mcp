from datetime import datetime, timedelta

import pytest
from arcade_core.config_model import AuthConfig, Config

from arcade_cli.utils import resolve_coordinator_url, resolve_engine_url


@pytest.fixture
def isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def staged_config(isolated_config_dir):
    Config(
        coordinator_url="https://cloud.example.dev",
        engine_url="https://api.example.dev",
        auth=AuthConfig(
            access_token="x",
            refresh_token="y",
            expires_at=datetime.now() + timedelta(hours=1),
        ),
    ).save_to_file()


# --- Engine ----------------------------------------------------------------


def test_resolve_engine_url_uses_saved_when_no_flags(staged_config) -> None:
    assert resolve_engine_url(None, None, False, False) == "https://api.example.dev"


def test_resolve_engine_url_explicit_host_wins(staged_config) -> None:
    assert (
        resolve_engine_url("api.arcade.dev", None, False, False) == "https://api.arcade.dev"
    )


def test_resolve_engine_url_explicit_port_wins(staged_config) -> None:
    assert resolve_engine_url(None, 9099, False, False) == "https://api.arcade.dev:9099"


def test_resolve_engine_url_force_tls_counts_as_override(staged_config) -> None:
    assert resolve_engine_url(None, None, True, False) == "https://api.arcade.dev"


def test_resolve_engine_url_force_no_tls_counts_as_override(staged_config) -> None:
    assert resolve_engine_url(None, None, False, True) == "http://api.arcade.dev"


def test_resolve_engine_url_no_creds_falls_back_to_prod(isolated_config_dir) -> None:
    assert resolve_engine_url(None, None, False, False) == "https://api.arcade.dev"


def test_resolve_engine_url_creds_without_engine_url_falls_back_to_prod(
    isolated_config_dir,
) -> None:
    Config(coordinator_url="https://cloud.arcade.dev").save_to_file()
    assert resolve_engine_url(None, None, False, False) == "https://api.arcade.dev"


# --- Coordinator -----------------------------------------------------------


def test_resolve_coordinator_url_uses_saved_when_no_flags(staged_config) -> None:
    assert resolve_coordinator_url(None, None, False, False) == "https://cloud.example.dev"


def test_resolve_coordinator_url_explicit_host_wins(staged_config) -> None:
    assert (
        resolve_coordinator_url("cloud.arcade.dev", None, False, False)
        == "https://cloud.arcade.dev"
    )


def test_resolve_coordinator_url_no_creds_falls_back_to_prod(isolated_config_dir) -> None:
    assert resolve_coordinator_url(None, None, False, False) == "https://cloud.arcade.dev"


def test_resolve_coordinator_url_force_no_tls_counts_as_override(staged_config) -> None:
    assert resolve_coordinator_url(None, None, False, True) == "http://cloud.arcade.dev"
