"""Every command that talks to an installation obeys the active context.

The no-Cloud guard lives inside the URL resolvers, so a command that builds its
own base URL is not merely untargeted -- it is unguarded, and sends the
operator's bearer token to a host their context forbids.
"""

import pytest
from arcade_cli.context import NoCloudGuardError

SELF_HOSTED = {
    "cloud": {
        "active_context": "acme",
        "contexts": {
            "acme": {
                "kind": "self_hosted",
                "engine_url": "https://api.acme.internal",
                "coordinator_url": "https://cloud.acme.internal",
                "dashboard_url": "https://dash.acme.internal",
                "auth": {
                    "access_token": "tok",
                    "refresh_token": "r",
                    "expires_at": "2099-01-01T00:00:00",
                },
                "context": {
                    "org_id": "o",
                    "org_name": "O",
                    "project_id": "p",
                    "project_name": "P",
                },
            }
        },
    }
}


@pytest.fixture
def self_hosted(tmp_path, monkeypatch):
    import yaml

    (tmp_path / "credentials.yaml").write_text(yaml.dump(SELF_HOSTED))
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    monkeypatch.setattr(
        "arcade_core.config_model.Config.get_config_file_path",
        classmethod(lambda cls: tmp_path / "credentials.yaml"),
    )
    monkeypatch.delenv("ARCADE_URL", raising=False)
    monkeypatch.delenv("ARCADE_API_KEY", raising=False)


class TestTheEngineComesFromTheContext:
    def test_an_unspecified_host_resolves_to_the_context_engine(self, self_hosted):
        from arcade_cli.utils import resolve_engine_base_url

        assert resolve_engine_base_url(None, None, False, False) == "https://api.acme.internal"

    def test_an_unspecified_coordinator_resolves_to_the_context(self, self_hosted):
        from arcade_cli.utils import resolve_coordinator_base_url

        assert (
            resolve_coordinator_base_url(None, None, False, False) == "https://cloud.acme.internal"
        )

    def test_naming_a_cloud_host_explicitly_is_refused(self, self_hosted):
        from arcade_cli.utils import resolve_engine_base_url

        with pytest.raises(NoCloudGuardError):
            resolve_engine_base_url("api.arcade.dev", None, False, False)


class TestCommandsThatBuiltTheirOwnUrl:
    """Each of these reached Arcade Cloud regardless of the active context."""

    def test_server_callback_uses_the_context(self, self_hosted):
        from arcade_cli import server

        server.main(host=None, port=None, force_tls=False, force_no_tls=False)
        assert server.state["engine_url"] == "https://api.acme.internal"

    def test_show_reaches_the_context_engine(self, self_hosted, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            "arcade_cli.utils.get_arcade_client", lambda url: seen.setdefault("url", url)
        )
        from arcade_cli.utils import get_tools_from_engine

        with pytest.raises(Exception):  # noqa: B017 - the stub client cannot list tools
            get_tools_from_engine(None)
        assert seen["url"] == "https://api.acme.internal"

    def test_connect_gateway_listing_uses_the_context(self, self_hosted):
        from arcade_cli.utils import resolve_engine_base_url

        assert (
            resolve_engine_base_url(None, None, False, False, default_port=None)
            == "https://api.acme.internal"
        )


class TestKindIsInferredNotAssumed:
    def test_a_self_hosted_coordinator_is_not_labelled_cloud(self):
        from arcade_cli.context import kind_for_urls

        assert kind_for_urls("https://coordinator.acme.internal") == "self_hosted"

    def test_localhost_is_self_hosted(self):
        from arcade_cli.context import kind_for_urls

        assert kind_for_urls("http://localhost:8000") == "self_hosted"

    def test_the_cloud_default_still_reads_as_cloud(self):
        from arcade_cli.context import kind_for_urls
        from arcade_core.constants import PROD_COORDINATOR_HOST

        assert kind_for_urls(f"https://{PROD_COORDINATOR_HOST}") == "cloud"


class TestInstallUrlNormalisation:
    """A host and port is not a scheme.

    ``urlparse`` reads "engine.internal:8443" as scheme "engine.internal", so a
    check on its ``scheme`` leaves such a value bare and it is later called as
    though it were a URL.
    """

    def test_a_host_and_port_gains_a_scheme(self):
        from arcade_cli.context import _normalize_install_url

        assert _normalize_install_url("engine.internal:8443") == "https://engine.internal:8443"

    def test_a_localhost_port_gains_a_scheme(self):
        from arcade_cli.context import _normalize_install_url

        assert _normalize_install_url("localhost:9099") == "https://localhost:9099"

    def test_an_explicit_scheme_is_left_alone(self):
        from arcade_cli.context import _normalize_install_url

        assert _normalize_install_url("http://engine.internal:8443") == (
            "http://engine.internal:8443"
        )

    def test_a_bare_host_still_gains_one(self):
        from arcade_cli.context import _normalize_install_url

        assert _normalize_install_url("engine.internal") == "https://engine.internal"


class TestLoginReadsThePinnedEnvironment:
    """Importing the CLI loads a project env file before any command body runs.

    A repo that sets ARCADE_URL for its own server would otherwise divert a
    plain Cloud login onto the discovery path.
    """

    def test_login_uses_the_startup_snapshot_not_the_live_value(self, monkeypatch):
        from arcade_cli import _startup_environment

        monkeypatch.delenv("ARCADE_URL", raising=False)
        _startup_environment.forget()
        _startup_environment.capture()

        # What a project .env does part-way through the process.
        monkeypatch.setenv("ARCADE_URL", "https://someone-elses-installation.example")

        assert _startup_environment.value("ARCADE_URL") is None


class TestDashboardWithoutAnEngine:
    """A discovery document need not name an engine.

    Only the coordinator is required at login, so a context can carry a
    dashboard URL and no engine. Resolving an engine there would fall back to
    Arcade Cloud, which the guard refuses -- taking the dashboard down with it.
    """

    @pytest.fixture
    def dashboard_only(self, tmp_path, monkeypatch):
        import yaml

        doc = {
            "cloud": {
                "active_context": "acme",
                "contexts": {
                    "acme": {
                        "kind": "self_hosted",
                        "coordinator_url": "https://cloud.acme.internal",
                        "dashboard_url": "https://dash.acme.internal",
                        "auth": {
                            "access_token": "tok",
                            "refresh_token": "r",
                            "expires_at": "2099-01-01T00:00:00",
                        },
                    }
                },
            }
        }
        (tmp_path / "credentials.yaml").write_text(yaml.dump(doc))
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
        monkeypatch.setattr(
            "arcade_core.config_model.Config.get_config_file_path",
            classmethod(lambda cls: tmp_path / "credentials.yaml"),
        )
        monkeypatch.delenv("ARCADE_URL", raising=False)
        monkeypatch.delenv("ARCADE_API_KEY", raising=False)

    def test_the_context_really_has_no_engine(self, dashboard_only):
        from arcade_cli.context import resolve_active_context

        ctx = resolve_active_context()
        assert ctx.dashboard_url == "https://dash.acme.internal"
        assert ctx.engine_url is None

    def test_resolving_an_engine_there_would_be_refused(self, dashboard_only):
        from arcade_cli.context import NoCloudGuardError
        from arcade_cli.utils import resolve_engine_base_url

        with pytest.raises(NoCloudGuardError):
            resolve_engine_base_url(None, None, False, False)

    def test_the_dashboard_still_opens(self, dashboard_only, monkeypatch):
        opened = {}
        monkeypatch.setattr("arcade_cli.main._open_browser", lambda u: opened.setdefault("url", u) or True)
        from arcade_cli.main import dashboard

        dashboard(host=None, port=None, local=False, force_tls=False, force_no_tls=False, debug=False)
        assert opened["url"] == "https://dash.acme.internal"
