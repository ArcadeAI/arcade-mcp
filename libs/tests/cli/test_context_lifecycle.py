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


class TestTheLastContextLeavesNothingBehind:
    """save_to_file rebuilds a `default` context from the flat fields when the
    map is empty. Deleting the last context therefore has to take the file with
    it, or the CLI reports nothing remains while a context it invented sits on
    disk -- self_hosted, credential-less, and enough to arm the no-Cloud guard.
    """

    @pytest.fixture
    def one_self_hosted(self, tmp_path, monkeypatch):
        path = tmp_path / "credentials.yaml"
        monkeypatch.setattr(Config, "get_config_file_path", classmethod(lambda cls: path))
        monkeypatch.setattr(Config, "ensure_config_dir_exists", staticmethod(lambda: None))
        config = Config(
            contexts={
                "acme": NamedContext(kind="self_hosted", engine_url="https://api.acme.internal")
            },
            active_context="acme",
        )
        config._apply_named_context("acme", config.contexts["acme"])
        config.save_to_file()
        return path

    def test_deleting_the_last_context_removes_the_file(self, one_self_hosted):
        from arcade_cli.contexts_cmd import context_delete

        context_delete("acme")

        assert not one_self_hosted.exists()

    def test_no_context_is_invented_in_its_place(self, one_self_hosted):
        from arcade_cli.contexts_cmd import context_delete

        context_delete("acme")

        assert not one_self_hosted.exists()
        with pytest.raises(FileNotFoundError):
            Config.load_from_file()

    def test_remove_context_clears_the_kind_it_cannot_default(self):
        config = Config(
            contexts={"acme": NamedContext(kind="self_hosted")}, active_context="acme"
        )
        config.kind = "self_hosted"

        assert config.remove_context("acme") is False
        assert config.kind == "cloud", "a stale self_hosted would arm the guard"

    def test_a_save_after_the_last_removal_cannot_revive_it(self, one_self_hosted):
        import yaml

        config = Config.load_from_file()
        config.remove_context("acme")
        config.save_to_file()

        cloud = yaml.safe_load(one_self_hosted.read_text())["cloud"]
        revived = cloud.get("contexts", {}).get("default")
        assert revived is None or revived.get("kind") == "cloud"


class TestTheSelectedContextSuppliesCredentialsToo:
    """Choosing a context has to move everything, not just the URLs.

    The engine and coordinator come from the URL resolvers, but the bearer
    token, the org and project scoping and the token refresh all come from a
    Config loaded elsewhere. Move only the URLs and a command reaches one
    installation holding another installation's credentials.
    """

    @pytest.fixture
    def two_installations(self, tmp_path, monkeypatch):
        def ctx(token, org, kind, engine, coordinator):
            return {
                "kind": kind,
                "engine_url": engine,
                "coordinator_url": coordinator,
                "auth": {
                    "access_token": token,
                    "refresh_token": "r",
                    "expires_at": "2099-01-01T00:00:00",
                },
                "user": {"email": "me@example.com"},
                "context": {
                    "org_id": org,
                    "org_name": "O",
                    "project_id": f"{org}-PROJ",
                    "project_name": "P",
                },
            }

        path = tmp_path / "credentials.yaml"
        path.write_text(
            yaml.dump(
                {
                    "cloud": {
                        "active_context": "cloud1",
                        "contexts": {
                            "cloud1": ctx(
                                "CLOUD-TOKEN", "CLOUD-ORG", "cloud",
                                "https://api.arcade.dev", "https://cloud.arcade.dev",
                            ),
                            "onprem": ctx(
                                "ONPREM-TOKEN", "ONPREM-ORG", "self_hosted",
                                "https://api.acme.internal", "https://cloud.acme.internal",
                            ),
                        },
                    }
                }
            )
        )
        monkeypatch.setattr(Config, "get_config_file_path", classmethod(lambda cls: path))
        monkeypatch.setattr(Config, "ensure_config_dir_exists", staticmethod(lambda: None))
        monkeypatch.delenv("ARCADE_URL", raising=False)
        monkeypatch.delenv("ARCADE_API_KEY", raising=False)
        monkeypatch.delenv("ARCADE_CONTEXT", raising=False)

        from arcade_cli.context import override_context

        override_context("onprem")
        yield
        override_context(None)

    def test_the_engine_follows_the_selection(self, two_installations):
        from arcade_cli.utils import resolve_engine_base_url

        assert resolve_engine_base_url(None, None, False, False) == "https://api.acme.internal"

    def test_the_token_follows_the_selection(self, two_installations):
        from arcade_cli.utils import validate_and_get_config

        assert validate_and_get_config().auth.access_token == "ONPREM-TOKEN"

    def test_the_org_and_project_scoping_follows_the_selection(self, two_installations):
        from arcade_cli.utils import get_org_scoped_url

        url = get_org_scoped_url("https://api.acme.internal", "/secrets")
        assert "ONPREM-ORG" in url
        assert "CLOUD-ORG" not in url

    def test_the_coordinator_follows_the_selection(self, two_installations):
        from arcade_cli.utils import resolve_coordinator_base_url

        assert (
            resolve_coordinator_base_url(None, None, False, False)
            == "https://cloud.acme.internal"
        )

    def test_a_plain_load_sees_the_selection(self, two_installations):
        assert Config.load_from_file().auth.access_token == "ONPREM-TOKEN"
