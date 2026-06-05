import pytest

from arcade_core.config_model import Config


@pytest.fixture
def isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    return tmp_path


def test_config_persists_engine_url(isolated_config_dir) -> None:
    cfg = Config(
        coordinator_url="https://cloud.example.dev",
        engine_url="https://api.example.dev",
    )
    cfg.save_to_file()

    loaded = Config.load_from_file()

    assert loaded.engine_url == "https://api.example.dev"
    assert loaded.coordinator_url == "https://cloud.example.dev"


def test_config_engine_url_optional(isolated_config_dir) -> None:
    cfg = Config(coordinator_url="https://cloud.arcade.dev")
    cfg.save_to_file()

    loaded = Config.load_from_file()

    assert loaded.engine_url is None


def test_config_engine_url_defaults_to_none() -> None:
    cfg = Config()
    assert cfg.engine_url is None
