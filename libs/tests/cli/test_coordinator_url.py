"""Tests for how the ``org`` and ``project`` command groups resolve the Coordinator URL.

``arcade login -h <coordinator-host>`` stores both the Coordinator it
authenticated against and a token that is only valid for that Coordinator. The
command groups used to build their request URL from ``PROD_COORDINATOR_HOST``
while the token was resolved from the saved Coordinator, so a user logged in to
a dedicated instance had the two disagree and every call answered 401.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli import org as org_module
from arcade_cli import project as project_module
from arcade_cli.utils import get_saved_coordinator_url, resolve_coordinator_url
from typer.testing import CliRunner

PROD_COORDINATOR_URL = "https://cloud.arcade.dev"
DEDICATED_COORDINATOR_URL = "https://coordinator.tenant.example.com"


@pytest.fixture(autouse=True)
def _isolate_command_group_state():
    """The group ``state`` dicts are module-level; keep tests independent."""
    project_module.state.clear()
    org_module.state.clear()
    yield
    project_module.state.clear()
    org_module.state.clear()


@pytest.fixture(autouse=True)
def _disable_usage_tracking(monkeypatch):
    """Keep CLI invocations from emitting usage telemetry."""
    monkeypatch.setenv("ARCADE_USAGE_TRACKING", "0")


def _fake_config_module(coordinator_url):
    """A stand-in for ``arcade_core.config`` exposing ``config.coordinator_url``.

    Injecting this through ``sys.modules`` lets the real ``get_saved_coordinator_url``
    run without a ``~/.arcade/credentials.yaml``; importing the genuine module
    raises when logged out.
    """
    module = types.ModuleType("arcade_core.config")
    module.config = types.SimpleNamespace(coordinator_url=coordinator_url)
    return module


class TestGetSavedCoordinatorUrl:
    """Reading the Coordinator recorded by ``arcade login``."""

    def test_returns_saved_url(self):
        with patch.dict(
            sys.modules, {"arcade_core.config": _fake_config_module(DEDICATED_COORDINATOR_URL)}
        ):
            assert get_saved_coordinator_url() == DEDICATED_COORDINATOR_URL

    @pytest.mark.parametrize("saved", [None, ""])
    def test_unset_coordinator_returns_none(self, saved):
        with patch.dict(sys.modules, {"arcade_core.config": _fake_config_module(saved)}):
            assert get_saved_coordinator_url() is None

    def test_unreadable_config_returns_none(self):
        """Logged out, importing the config raises; that must degrade to None."""
        broken = types.ModuleType("arcade_core.config")  # no ``config`` attribute
        with patch.dict(sys.modules, {"arcade_core.config": broken}):
            assert get_saved_coordinator_url() is None


class TestResolveCoordinatorUrl:
    """The resolution precedence itself."""

    def test_uses_saved_coordinator_when_no_flags(self):
        """The reported bug: a dedicated-instance login must not target Arcade Cloud."""
        with patch(
            "arcade_cli.utils.get_saved_coordinator_url", return_value=DEDICATED_COORDINATOR_URL
        ):
            assert resolve_coordinator_url(None, None, False, False) == DEDICATED_COORDINATOR_URL

    def test_falls_back_to_prod_when_nothing_saved(self):
        with patch("arcade_cli.utils.get_saved_coordinator_url", return_value=None):
            assert resolve_coordinator_url(None, None, False, False) == PROD_COORDINATOR_URL

    def test_saved_url_is_used_verbatim(self):
        """Scheme and port of the saved Coordinator must survive resolution."""
        saved = "http://coordinator.internal:8443"
        with patch("arcade_cli.utils.get_saved_coordinator_url", return_value=saved):
            assert resolve_coordinator_url(None, None, False, False) == saved

    def test_explicit_host_wins_over_saved(self):
        with patch(
            "arcade_cli.utils.get_saved_coordinator_url", return_value=DEDICATED_COORDINATOR_URL
        ):
            assert (
                resolve_coordinator_url("other.example.com", None, False, False)
                == "https://other.example.com"
            )

    @pytest.mark.parametrize(
        ("port", "force_tls", "force_no_tls", "expected"),
        [
            (9099, False, False, "https://cloud.arcade.dev:9099"),
            (None, True, False, "https://cloud.arcade.dev"),
            (None, False, True, "http://cloud.arcade.dev"),
        ],
    )
    def test_other_explicit_flags_are_authoritative(self, port, force_tls, force_no_tls, expected):
        """Naming a port or TLS mode means the caller is describing the target.

        The saved Coordinator is a full URL, so honoring it while also applying a
        partial override would have to guess which half wins; the flags win
        instead, preserving the pre-existing behavior for anyone passing them.
        """
        with patch(
            "arcade_cli.utils.get_saved_coordinator_url", return_value=DEDICATED_COORDINATOR_URL
        ):
            assert resolve_coordinator_url(None, port, force_tls, force_no_tls) == expected

    def test_unreadable_config_still_resolves_to_prod(self):
        """Resolution must not raise when the credentials file is unreadable."""
        broken = types.ModuleType("arcade_core.config")
        with patch.dict(sys.modules, {"arcade_core.config": broken}):
            assert resolve_coordinator_url(None, None, False, False) == PROD_COORDINATOR_URL


def _mock_config():
    config = MagicMock()
    config.context.org_id = "org_1"
    config.context.org_name = "Acme"
    config.get_active_org_id.return_value = "org_1"
    config.get_active_project_id.return_value = "proj_1"
    return config


class TestCommandGroupsTargetLoggedInCoordinator:
    """End-to-end through the Typer groups, which is where the bug lived."""

    def test_project_list_uses_saved_coordinator(self):
        with (
            patch(
                "arcade_cli.utils.get_saved_coordinator_url",
                return_value=DEDICATED_COORDINATOR_URL,
            ),
            patch("arcade_cli.project.fetch_projects", return_value=[]) as fetch,
            patch("arcade_core.config_model.Config.load_from_file", return_value=_mock_config()),
        ):
            result = CliRunner().invoke(project_module.app, ["list"])

        assert result.exit_code == 0, result.output
        fetch.assert_called_once_with(DEDICATED_COORDINATOR_URL, "org_1")

    def test_org_list_uses_saved_coordinator(self):
        with (
            patch(
                "arcade_cli.utils.get_saved_coordinator_url",
                return_value=DEDICATED_COORDINATOR_URL,
            ),
            patch("arcade_cli.org.fetch_organizations", return_value=[]) as fetch,
            patch("arcade_core.config_model.Config.load_from_file", return_value=_mock_config()),
        ):
            result = CliRunner().invoke(org_module.app, ["list"])

        assert result.exit_code == 0, result.output
        fetch.assert_called_once_with(DEDICATED_COORDINATOR_URL)

    def test_project_list_host_flag_still_overrides(self):
        """The documented workaround must keep working."""
        with (
            patch(
                "arcade_cli.utils.get_saved_coordinator_url",
                return_value=DEDICATED_COORDINATOR_URL,
            ),
            patch("arcade_cli.project.fetch_projects", return_value=[]) as fetch,
            patch("arcade_core.config_model.Config.load_from_file", return_value=_mock_config()),
        ):
            result = CliRunner().invoke(project_module.app, ["-h", "other.example.com", "list"])

        assert result.exit_code == 0, result.output
        fetch.assert_called_once_with("https://other.example.com", "org_1")

    def test_project_list_falls_back_to_prod_without_login(self):
        with (
            patch("arcade_cli.utils.get_saved_coordinator_url", return_value=None),
            patch("arcade_cli.project.fetch_projects", return_value=[]) as fetch,
            patch("arcade_core.config_model.Config.load_from_file", return_value=_mock_config()),
        ):
            result = CliRunner().invoke(project_module.app, ["list"])

        assert result.exit_code == 0, result.output
        fetch.assert_called_once_with(PROD_COORDINATOR_URL, "org_1")


class TestLazyAccessorFallback:
    """Calling a command function without the group callback must still resolve."""

    @pytest.mark.parametrize("module", [project_module, org_module])
    def test_accessor_resolves_when_state_unset(self, module):
        assert module.state == {}
        with patch(
            "arcade_cli.utils.get_saved_coordinator_url", return_value=DEDICATED_COORDINATOR_URL
        ):
            assert module._coordinator_url() == DEDICATED_COORDINATOR_URL
