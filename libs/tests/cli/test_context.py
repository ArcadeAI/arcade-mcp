import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import yaml
from arcade_cli.context import (
    ARCADE_API_KEY_ENV,
    ARCADE_URL_ENV,
    DiscoveryError,
    DiscoveryNotFoundError,
    NoCloudGuardError,
    fetch_discovery,
    guard_no_cloud,
    is_cloud_host,
    kind_for_urls,
    resolve_active_context,
    resolve_ci_context,
)
from arcade_core.config_model import AuthConfig, Config, ContextConfig, NamedContext, UserConfig


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    return tmp_path


def _write_credentials(work_dir: Path, cloud: dict) -> None:
    (work_dir / "credentials.yaml").write_text(yaml.dump({"cloud": cloud}), encoding="utf-8")


def _legacy_cloud() -> dict:
    return {
        "coordinator_url": "https://cloud.arcade.dev",
        "auth": {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": "2030-01-01T00:00:00",
        },
        "user": {"email": "user@example.com"},
        "context": {
            "org_id": "org",
            "org_name": "Org",
            "project_id": "proj",
            "project_name": "Proj",
        },
    }


class TestConfigMigration:
    def test_legacy_file_migrates_to_default_context(self, work_dir: Path):
        _write_credentials(work_dir, _legacy_cloud())

        config = Config.load_from_file()

        assert config.list_context_names() == ["default"]
        assert config.active_context == "default"
        assert config.kind == "cloud"
        assert config.coordinator_url == "https://cloud.arcade.dev"
        assert config.user is not None and config.user.email == "user@example.com"

    def test_migrated_file_is_rewritten_in_context_format(self, work_dir: Path):
        _write_credentials(work_dir, _legacy_cloud())

        Config.load_from_file().save_to_file()

        raw = yaml.safe_load((work_dir / "credentials.yaml").read_text())
        assert raw["cloud"]["active_context"] == "default"
        assert "default" in raw["cloud"]["contexts"]

    def test_migrated_file_still_reads_to_an_older_core(self, work_dir: Path):
        # The active context is written in the flat shape as well. An
        # arcade-core that predates named contexts ignores the keys it does not
        # know and still finds its credentials, so downgrading does not present
        # the user as logged out.
        _write_credentials(work_dir, _legacy_cloud())

        Config.load_from_file().save_to_file()

        cloud = yaml.safe_load((work_dir / "credentials.yaml").read_text())["cloud"]
        assert cloud["auth"]["access_token"] == _legacy_cloud()["auth"]["access_token"]
        assert cloud["user"]["email"] == _legacy_cloud()["user"]["email"]
        assert cloud["context"]["org_id"] == _legacy_cloud()["context"]["org_id"]

    def test_round_trip_preserves_auth(self, work_dir: Path):
        _write_credentials(work_dir, _legacy_cloud())
        Config.load_from_file().save_to_file()

        reloaded = Config.load_from_file()
        assert reloaded.auth is not None
        assert reloaded.auth.access_token == "tok"


class TestNamedContexts:
    def test_use_context_switches_active(self, work_dir: Path):
        config = Config()
        config.contexts = {
            "cloud": NamedContext(kind="cloud", engine_url="https://api.arcade.dev"),
            "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal"),
        }
        config._apply_named_context("cloud", config.contexts["cloud"])
        config.save_to_file()

        reloaded = Config.load_from_file()
        reloaded.use_context("onprem")
        reloaded.save_to_file()

        assert Config.load_from_file().active_context == "onprem"
        assert Config.load_from_file().kind == "self_hosted"

    def test_use_unknown_context_raises(self, work_dir: Path):
        config = Config()
        config.contexts = {"cloud": NamedContext(kind="cloud")}

        with pytest.raises(ValueError, match="not found"):
            config.use_context("missing")

    def test_saving_active_context_does_not_drop_others(self, work_dir: Path):
        config = Config()
        config.contexts = {
            "a": NamedContext(kind="cloud", engine_url="https://api.arcade.dev"),
            "b": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal"),
        }
        config._apply_named_context("a", config.contexts["a"])
        config.save_to_file()

        assert set(Config.load_from_file().list_context_names()) == {"a", "b"}


class TestSaveCredentialsPreservesContexts:
    def _whoami(self):
        from arcade_cli.authn import OrgInfo, ProjectInfo, WhoAmIResponse

        return WhoAmIResponse(
            account_id="acct-1",
            email="user@acme.internal",
            organizations=[OrgInfo(org_id="o", name="Org", is_default=True)],
            projects=[ProjectInfo(project_id="p", name="tools", is_default=True)],
        )

    def _tokens(self):
        from arcade_core.auth_tokens import TokenResponse

        return TokenResponse(
            access_token="a", refresh_token="r", expires_in=3600, token_type="Bearer"
        )

    def test_login_adds_context_without_dropping_existing(self, work_dir: Path):
        from arcade_cli.authn import save_credentials_from_whoami

        seed = Config()
        seed.contexts = {"cloud": NamedContext(kind="cloud", engine_url="https://api.arcade.dev")}
        seed._apply_named_context("cloud", seed.contexts["cloud"])
        seed.save_to_file()

        save_credentials_from_whoami(
            self._tokens(),
            self._whoami(),
            "https://coord.acme.internal",
            context_name="onprem",
            engine_url="https://engine.acme.internal",
            kind="self_hosted",
        )

        reloaded = Config.load_from_file()
        assert set(reloaded.list_context_names()) == {"cloud", "onprem"}
        assert reloaded.active_context == "onprem"
        assert reloaded.user is not None and reloaded.user.account_id == "acct-1"


class TestCloudHostDetection:
    @pytest.mark.parametrize(
        "host,expected",
        [
            ("api.arcade.dev", True),
            ("cloud.arcade.dev", True),
            ("foo.arcade.dev", True),
            ("engine.acme.internal", False),
            ("localhost", False),
            (None, False),
        ],
    )
    def test_is_cloud_host(self, host, expected):
        assert is_cloud_host(host) is expected

    def test_kind_for_urls(self):
        assert kind_for_urls("https://api.arcade.dev") == "cloud"
        assert kind_for_urls("https://engine.acme.internal") == "self_hosted"
        assert kind_for_urls("https://engine.acme.internal", "https://cloud.arcade.dev") == "cloud"


class TestDiscovery:
    def _response(self, status_code: int, json_body=None) -> httpx.Response:
        return httpx.Response(
            status_code,
            json=json_body if json_body is not None else {},
            request=httpx.Request("GET", "https://engine.acme.internal/.well-known/arcade"),
        )

    def test_fetch_discovery_parses_document(self):
        body = {
            "engine": "https://engine.acme.internal",
            "coordinator": "https://coord.acme.internal",
            "dashboard": "https://dash.acme.internal",
            "version": "1.2.3",
            "deployments": {"enabled": True},
        }
        with patch("arcade_cli.context.httpx.get", return_value=self._response(200, body)):
            doc = fetch_discovery("https://engine.acme.internal")

        assert doc.engine == "https://engine.acme.internal"
        assert doc.coordinator == "https://coord.acme.internal"
        assert doc.deployments.enabled is True

    def test_fetch_discovery_reports_deployments_reason(self):
        body = {
            "engine": "https://engine.acme.internal",
            "deployments": {"enabled": False, "reason": "deployments are not enabled"},
        }
        with patch("arcade_cli.context.httpx.get", return_value=self._response(200, body)):
            doc = fetch_discovery("https://engine.acme.internal")

        assert doc.deployments.enabled is False
        assert doc.deployments.reason == "deployments are not enabled"

    def test_missing_document_raises_predates(self):
        with (
            patch("arcade_cli.context.httpx.get", return_value=self._response(404)),
            pytest.raises(DiscoveryNotFoundError, match="predates discovery"),
        ):
            fetch_discovery("https://engine.acme.internal")

    def test_unreachable_host_raises(self):
        with (
            patch(
                "arcade_cli.context.httpx.get",
                side_effect=httpx.ConnectError("nope"),
            ),
            pytest.raises(DiscoveryError, match="Could not reach"),
        ):
            fetch_discovery("https://engine.acme.internal")

    def test_server_error_raises_discovery_error(self):
        with (
            patch("arcade_cli.context.httpx.get", return_value=self._response(503)),
            pytest.raises(DiscoveryError, match="failed with HTTP 503"),
        ):
            fetch_discovery("https://engine.acme.internal")

    def test_bare_host_gets_https_scheme(self):
        captured: dict = {}

        def _fake_get(url, *args, **kwargs):
            captured["url"] = url
            return self._response(200, {"engine": "https://engine.acme.internal"})

        with patch("arcade_cli.context.httpx.get", side_effect=_fake_get):
            fetch_discovery("engine.acme.internal")

        assert captured["url"] == "https://engine.acme.internal/.well-known/arcade"

    def test_invalid_json_raises_predates(self):
        bad = httpx.Response(
            200,
            content=b"not json",
            request=httpx.Request("GET", "https://engine.acme.internal/.well-known/arcade"),
        )
        with (
            patch("arcade_cli.context.httpx.get", return_value=bad),
            pytest.raises(DiscoveryNotFoundError),
        ):
            fetch_discovery("https://engine.acme.internal")

    def test_addresses_nested_under_urls_are_read(self):
        body = {
            "urls": {
                "engine": "https://engine.acme.internal",
                "coordinator": "https://coord.acme.internal",
                "dashboard": "https://dash.acme.internal",
            },
            "version": "1.2.3",
        }
        with patch("arcade_cli.context.httpx.get", return_value=self._response(200, body)):
            doc = fetch_discovery("https://engine.acme.internal")

        assert doc.engine == "https://engine.acme.internal"
        assert doc.coordinator == "https://coord.acme.internal"
        assert doc.dashboard == "https://dash.acme.internal"

    def test_top_level_addresses_win_over_nested_ones(self):
        body = {
            "engine": "https://engine.acme.internal",
            "coordinator": "https://coord.acme.internal",
            "urls": {
                "engine": "https://stale.acme.internal",
                "coordinator": "https://stale-coord.acme.internal",
            },
        }
        with patch("arcade_cli.context.httpx.get", return_value=self._response(200, body)):
            doc = fetch_discovery("https://engine.acme.internal")

        assert doc.engine == "https://engine.acme.internal"
        assert doc.coordinator == "https://coord.acme.internal"

    def test_an_unusable_urls_field_is_ignored(self):
        body = {"engine": "https://engine.acme.internal", "urls": "not an object"}
        with patch("arcade_cli.context.httpx.get", return_value=self._response(200, body)):
            doc = fetch_discovery("https://engine.acme.internal")

        assert doc.engine == "https://engine.acme.internal"


class TestCIContext:
    def test_ci_context_from_env(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "key"

        ctx = resolve_ci_context()

        assert ctx is not None
        assert ctx.is_ci is True
        assert ctx.engine_url == "https://engine.acme.internal"
        assert ctx.api_key == "key"
        assert ctx.kind == "self_hosted"

    def test_no_ci_context_when_partial(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ.pop(ARCADE_API_KEY_ENV, None)

        assert resolve_ci_context() is None

    def test_resolve_active_context_prefers_ci(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "key"

        assert resolve_active_context().is_ci is True


def _save_self_hosted_context() -> None:
    config = Config()
    config.contexts = {
        "onprem": NamedContext(
            kind="self_hosted",
            engine_url="https://engine.acme.internal",
            coordinator_url="https://coord.acme.internal",
            auth=AuthConfig(access_token="a", refresh_token="r", expires_at=datetime(2030, 1, 1)),
            user=UserConfig(email="u@acme.internal"),
            context=ContextConfig(org_id="o", org_name="O", project_id="p", project_name="P"),
        )
    }
    config._apply_named_context("onprem", config.contexts["onprem"])
    config.save_to_file()


class TestNoCloudGuard:
    def test_guard_refuses_cloud_under_self_hosted(self, work_dir: Path):
        _save_self_hosted_context()

        with pytest.raises(NoCloudGuardError, match="Refusing to contact"):
            guard_no_cloud("https://api.arcade.dev/v1/deployments")

    def test_guard_allows_self_hosted_host(self, work_dir: Path):
        _save_self_hosted_context()

        guard_no_cloud("https://engine.acme.internal/v1/deployments")

    def test_guard_is_noop_without_active_context(self, work_dir: Path):
        guard_no_cloud("https://api.arcade.dev/v1/deployments")

    def test_guard_allows_cloud_under_cloud_context(self, work_dir: Path):
        config = Config()
        config.contexts = {
            "default": NamedContext(kind="cloud", engine_url="https://api.arcade.dev")
        }
        config._apply_named_context("default", config.contexts["default"])
        config.save_to_file()

        guard_no_cloud("https://api.arcade.dev/v1/deployments")


class TestEngineUrlResolution:
    def test_resolve_engine_url_uses_active_context(self, work_dir: Path):
        config = Config()
        config.contexts = {
            "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal")
        }
        config._apply_named_context("onprem", config.contexts["onprem"])
        config.save_to_file()

        from arcade_cli.utils import resolve_engine_base_url

        assert resolve_engine_base_url(None, None, False, False) == "https://engine.acme.internal"

    def test_resolve_engine_url_guards_cloud_override(self, work_dir: Path):
        config = Config()
        config.contexts = {
            "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal")
        }
        config._apply_named_context("onprem", config.contexts["onprem"])
        config.save_to_file()

        from arcade_cli.utils import resolve_engine_base_url

        with pytest.raises(NoCloudGuardError):
            resolve_engine_base_url("api.arcade.dev", None, False, False)


class TestLoginGuardIsPerContext:
    def _signed_in(self) -> dict:
        return {
            "kind": "self_hosted",
            "coordinator_url": "https://cloud.acme.internal",
            "auth": {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": "2030-01-01T00:00:00",
            },
            "user": {"email": "someone@acme.dev"},
        }

    def _cloud(self) -> dict:
        return {
            "kind": "cloud",
            "coordinator_url": "https://cloud.arcade.dev",
            "auth": {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": "2030-01-01T00:00:00",
            },
            "user": {"email": "user@example.com"},
            "context": {
                "org_id": "org",
                "org_name": "Org",
                "project_id": "proj",
                "project_name": "Proj",
            },
        }

    def _seed(self, work_dir: Path):
        _write_credentials(
            work_dir, {"active_context": "acme", "contexts": {"acme": self._signed_in()}}
        )
        return patch("arcade_cli.authn.CREDENTIALS_FILE_PATH", str(work_dir / "credentials.yaml"))

    def test_a_context_that_was_never_saved_is_not_signed_in(self, work_dir: Path):
        from arcade_cli.authn import check_existing_login

        with self._seed(work_dir):
            assert check_existing_login(suppress_message=True, context_name="default") is False

    def test_the_named_context_is_the_one_checked(self, work_dir: Path):
        from arcade_cli.authn import check_existing_login

        with self._seed(work_dir):
            assert check_existing_login(suppress_message=True, context_name="acme") is True

    def test_without_a_name_the_active_context_is_checked(self, work_dir: Path):
        from arcade_cli.authn import check_existing_login

        with self._seed(work_dir):
            assert check_existing_login(suppress_message=True) is True

    def test_a_cloud_only_login_is_still_recognised(self, work_dir: Path):
        from arcade_cli.authn import check_existing_login

        _write_credentials(work_dir, _legacy_cloud())
        with patch("arcade_cli.authn.CREDENTIALS_FILE_PATH", str(work_dir / "credentials.yaml")):
            assert check_existing_login(suppress_message=True, context_name="default") is True

    def test_a_cloud_login_beside_a_self_hosted_one_is_still_redundant(self, work_dir: Path):
        from arcade_cli.authn import check_existing_login

        _write_credentials(
            work_dir,
            {
                "active_context": "acme",
                "contexts": {
                    "acme": self._signed_in(),
                    "default": {
                        "kind": "cloud",
                        "coordinator_url": "https://cloud.arcade.dev",
                        "auth": {
                            "access_token": "tok",
                            "refresh_token": "ref",
                            "expires_at": "2030-01-01T00:00:00",
                        },
                        "user": {"email": "user@example.com"},
                    },
                },
            },
        )
        with patch("arcade_cli.authn.CREDENTIALS_FILE_PATH", str(work_dir / "credentials.yaml")):
            assert check_existing_login(suppress_message=True, context_name="default") is True

    def test_a_context_that_is_not_active_is_not_called_active(self, work_dir: Path, capsys):
        from arcade_cli.authn import check_existing_login

        _write_credentials(
            work_dir,
            {
                "active_context": "acme",
                "contexts": {"acme": self._signed_in(), "default": self._cloud()},
            },
        )
        with patch("arcade_cli.authn.CREDENTIALS_FILE_PATH", str(work_dir / "credentials.yaml")):
            assert check_existing_login(context_name="default") is True

        printed = capsys.readouterr().out
        assert "Active:" not in printed
        assert "default" in printed
        assert "acme" in printed
        assert "context use" in printed
        assert "logout" not in printed

    def test_the_active_context_still_reads_the_way_it_did(self, work_dir: Path, capsys):
        from arcade_cli.authn import check_existing_login

        _write_credentials(work_dir, _legacy_cloud())
        with patch("arcade_cli.authn.CREDENTIALS_FILE_PATH", str(work_dir / "credentials.yaml")):
            assert check_existing_login(context_name="default") is True

        printed = capsys.readouterr().out
        assert "Active:" in printed
        assert "logout" in printed
        assert "context use" not in printed
