"""A context can be added, switched, inspected, removed -- and logged out of.

login signs in to one installation, so logout signs out of one. Deleting every
saved context because you wanted to sign out of the current one is the kind of
surprise that costs someone their other installations.
"""

import pytest
import yaml
from arcade_core.config_model import Config, NamedContext


@pytest.fixture
def two_contexts(tmp_path, monkeypatch):
    path = tmp_path / "credentials.yaml"
    path.write_text(
        yaml.dump(
            {
                "cloud": {
                    "active_context": "acme",
                    "contexts": {
                        "acme": {"kind": "self_hosted", "engine_url": "https://api.acme.internal"},
                        "cloud1": {"kind": "cloud", "engine_url": "https://api.arcade.dev"},
                    },
                }
            }
        )
    )
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "get_config_file_path", classmethod(lambda cls: path))
    monkeypatch.setattr(Config, "ensure_config_dir_exists", staticmethod(lambda: None))
    monkeypatch.setattr("arcade_cli.main.CREDENTIALS_FILE_PATH", str(path))
    monkeypatch.delenv("ARCADE_URL", raising=False)
    monkeypatch.delenv("ARCADE_API_KEY", raising=False)
    monkeypatch.delenv("ARCADE_CONTEXT", raising=False)
    return path


class TestRemoveContext:
    def test_removing_the_active_one_promotes_another(self):
        config = Config(
            contexts={"a": NamedContext(kind="cloud"), "b": NamedContext(kind="self_hosted")},
            active_context="a",
        )
        assert config.remove_context("a") is True
        assert config.active_context == "b"

    def test_removing_the_last_one_leaves_nothing_active(self):
        config = Config(contexts={"a": NamedContext(kind="cloud")}, active_context="a")
        assert config.remove_context("a") is False
        assert config.active_context is None
        assert config.auth is None

    def test_removing_an_inactive_one_leaves_the_active_alone(self):
        config = Config(
            contexts={"a": NamedContext(kind="cloud"), "b": NamedContext(kind="self_hosted")},
            active_context="a",
        )
        assert config.remove_context("b") is True
        assert config.active_context == "a"

    def test_removing_an_unknown_one_says_what_exists(self):
        config = Config(contexts={"a": NamedContext(kind="cloud")}, active_context="a")
        with pytest.raises(ValueError, match="Available contexts: a"):
            config.remove_context("nope")


class TestLogoutIsPerContext:
    def test_logout_leaves_the_other_context_and_the_file(self, two_contexts):
        from arcade_cli.main import logout

        logout(all_contexts=False, debug=False)

        assert two_contexts.exists(), "the other context still needs somewhere to live"
        cloud = yaml.safe_load(two_contexts.read_text())["cloud"]
        assert sorted(cloud["contexts"]) == ["cloud1"]
        assert cloud["active_context"] == "cloud1"

    def test_logout_all_removes_the_file(self, two_contexts):
        from arcade_cli.main import logout

        logout(all_contexts=True, debug=False)

        assert not two_contexts.exists()

    def test_logout_of_the_only_context_removes_the_file(self, tmp_path, monkeypatch):
        path = tmp_path / "credentials.yaml"
        path.write_text(
            yaml.dump({"cloud": {"active_context": "a", "contexts": {"a": {"kind": "cloud"}}}})
        )
        monkeypatch.setattr(Config, "get_config_file_path", classmethod(lambda cls: path))
        monkeypatch.setattr(Config, "ensure_config_dir_exists", staticmethod(lambda: None))
        monkeypatch.setattr("arcade_cli.main.CREDENTIALS_FILE_PATH", str(path))
        from arcade_cli.main import logout

        logout(all_contexts=False, debug=False)

        assert not path.exists()


class TestContextDelete:
    def test_delete_removes_just_that_context(self, two_contexts):
        from arcade_cli.contexts_cmd import context_delete

        context_delete("cloud1")

        cloud = yaml.safe_load(two_contexts.read_text())["cloud"]
        assert sorted(cloud["contexts"]) == ["acme"]
        assert cloud["active_context"] == "acme"


class TestContextSelection:
    def test_the_env_var_picks_a_context(self, two_contexts, monkeypatch):
        from arcade_cli import _startup_environment
        from arcade_cli.utils import resolve_engine_base_url

        monkeypatch.setenv("ARCADE_CONTEXT", "cloud1")
        _startup_environment.forget()
        _startup_environment.capture()

        assert resolve_engine_base_url(None, None, False, False) == "https://api.arcade.dev"

    def test_the_flag_wins_over_the_env_var(self, two_contexts, monkeypatch):
        from arcade_cli import _startup_environment
        from arcade_cli.context import override_context
        from arcade_cli.utils import resolve_engine_base_url

        monkeypatch.setenv("ARCADE_CONTEXT", "cloud1")
        _startup_environment.forget()
        _startup_environment.capture()
        override_context("acme")
        try:
            assert resolve_engine_base_url(None, None, False, False) == "https://api.acme.internal"
        finally:
            override_context(None)

    def test_neither_falls_back_to_the_active_context(self, two_contexts):
        from arcade_cli.utils import resolve_engine_base_url

        assert resolve_engine_base_url(None, None, False, False) == "https://api.acme.internal"

    def test_naming_a_context_that_does_not_exist_is_an_error(self, two_contexts):
        from arcade_cli.context import override_context, resolve_active_context

        override_context("nope")
        try:
            with pytest.raises(ValueError, match="not found"):
                resolve_active_context()
        finally:
            override_context(None)
