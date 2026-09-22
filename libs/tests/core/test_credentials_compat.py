"""The credentials file has to stay readable by the arcade-core that wrote it last.

A CLI release cannot be unpublished and a migrated file cannot be un-migrated,
so the format has to work in both directions rather than only forwards.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from arcade_core.config_model import AuthConfig, Config, ContextConfig, NamedContext, UserConfig
from arcade_core.constants import arcade_config_path
from pydantic import BaseModel, ConfigDict


class PreContextsConfig(BaseModel):
    """arcade-core 4.18 as it reads the file: flat keys, unknown keys ignored."""

    model_config = ConfigDict(extra="ignore")

    coordinator_url: str | None = None
    auth: AuthConfig | None = None
    context: ContextConfig | None = None
    user: UserConfig | None = None


@pytest.fixture
def config_home(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Config, "get_config_file_path", classmethod(lambda cls: tmp_path / "credentials.yaml")
    )
    monkeypatch.setattr(Config, "ensure_config_dir_exists", staticmethod(lambda: None))
    return tmp_path / "credentials.yaml"


def _named() -> NamedContext:
    return NamedContext(
        kind="cloud",
        coordinator_url="https://cloud.arcade.dev",
        auth=AuthConfig(
            access_token="tok",
            refresh_token="refresh",
            expires_at=datetime.now() + timedelta(days=1),
        ),
        user=UserConfig(email="a@b.c"),
        context=ContextConfig(org_id="o", org_name="O", project_id="p", project_name="P"),
    )


class TestOlderCoreCanStillRead:
    def test_a_saved_file_still_authenticates_an_older_core(self, config_home):
        config = Config(contexts={"default": _named()}, active_context="default")
        config._apply_named_context("default", _named())
        config.save_to_file()

        cloud = yaml.safe_load(config_home.read_text())["cloud"]
        old = PreContextsConfig(**cloud)

        assert old.auth is not None, "an older arcade-core would read this file as logged out"
        assert old.auth.access_token == "tok"
        assert old.user is not None and old.user.email == "a@b.c"
        assert old.context is not None and old.context.org_id == "o"

    def test_the_named_contexts_are_still_written(self, config_home):
        config = Config(contexts={"default": _named()}, active_context="default")
        config._apply_named_context("default", _named())
        config.save_to_file()

        cloud = yaml.safe_load(config_home.read_text())["cloud"]
        assert cloud["active_context"] == "default"
        assert cloud["contexts"]["default"]["auth"]["access_token"] == "tok"

    def test_a_legacy_file_still_migrates(self, config_home):
        config_home.write_text(
            yaml.dump({
                "cloud": {
                    "coordinator_url": "https://cloud.arcade.dev",
                    "auth": {
                        "access_token": "tok",
                        "refresh_token": "refresh",
                        "expires_at": "2030-01-01T00:00:00",
                    },
                    "user": {"email": "a@b.c"},
                    "context": {
                        "org_id": "o",
                        "org_name": "O",
                        "project_id": "p",
                        "project_name": "P",
                    },
                }
            })
        )
        loaded = Config.load_from_file()
        assert loaded.is_authenticated()
        assert loaded.active_context == "default"
        assert loaded.kind == "cloud"

    def test_a_round_trip_prefers_the_named_context(self, config_home):
        config = Config(contexts={"default": _named()}, active_context="default")
        config._apply_named_context("default", _named())
        config.save_to_file()
        assert Config.load_from_file().is_authenticated()


class TestOneConfigDirectory:
    def test_both_resolvers_agree_under_a_relocated_work_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
        assert Config.get_config_dir_path() == Path(arcade_config_path()).resolve()

    def test_the_work_dir_is_the_config_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
        assert Config.get_config_dir_path() == tmp_path.resolve()


class TestTheActiveContextIsAlwaysWritten:
    """A save has to land somewhere the next load will look.

    ``load_from_file`` prefers the contexts map, so state written only to the
    flat keys is read back as whatever the map happens to hold instead.
    """

    def _orphaned(self, token: str) -> Config:
        config = Config(contexts={"acme": _named()}, active_context="deleted-context")
        fresh = _named()
        fresh.auth.access_token = token
        config._apply_named_context("default", fresh)
        config.active_context = "deleted-context"
        return config

    def test_a_refreshed_token_survives_the_round_trip(self, config_home):
        self._orphaned("refreshed").save_to_file()

        assert Config.load_from_file().auth.access_token == "refreshed"

    def test_the_active_name_is_kept_rather_than_replaced(self, config_home):
        self._orphaned("refreshed").save_to_file()

        cloud = yaml.safe_load(config_home.read_text())["cloud"]
        assert cloud["active_context"] == "deleted-context"
        assert cloud["contexts"]["deleted-context"]["auth"]["access_token"] == "refreshed"

    def test_the_other_contexts_are_left_alone(self, config_home):
        self._orphaned("refreshed").save_to_file()

        assert "acme" in yaml.safe_load(config_home.read_text())["cloud"]["contexts"]

    def test_an_unset_active_name_falls_back_to_default(self, config_home):
        config = Config(contexts={"acme": _named()}, active_context=None)
        config._apply_named_context("default", _named())
        config.active_context = None

        config.save_to_file()

        assert Config.load_from_file().active_context == "default"
