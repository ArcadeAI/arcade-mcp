"""Tests for how MCPServer resolves the Arcade engine URL for tool authorization.

When credentials come from ``arcade login``, the engine URL must follow the
environment the user logged into (the coordinator) instead of defaulting to the
production engine. Otherwise a non-production login sends its token to the
production engine and authorization fails with a 401.
"""

import sys
import types
from unittest.mock import patch

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server.server import MCPServer, _engine_url_from_coordinator
from arcade_mcp_server.settings import MCPSettings

PROD_ENGINE_URL = "https://api.arcade.dev"


@pytest.fixture(autouse=True)
def _clear_arcade_env(monkeypatch):
    """Ensure the server does not pick up ambient Arcade credentials/URLs."""
    monkeypatch.delenv("ARCADE_API_KEY", raising=False)
    monkeypatch.delenv("ARCADE_API_URL", raising=False)


def _fake_config_module(coordinator_url: str | None) -> types.ModuleType:
    """A stand-in for ``arcade_core.config`` exposing a ``config.coordinator_url``.

    Injecting this via ``sys.modules`` lets the real ``_coordinator_url_from_config``
    run without depending on a real ``~/.arcade/credentials.yaml`` (importing the
    genuine module raises when logged out).
    """
    module = types.ModuleType("arcade_core.config")
    module.config = types.SimpleNamespace(coordinator_url=coordinator_url)
    return module


def _build_server(
    *,
    coordinator_url: str | None,
    arcade_api_key: str | None = None,
    arcade_api_url: str | None = None,
    org_project: tuple[str, str] | None = None,
) -> MCPServer:
    """Construct a server with the login config mocked out.

    ``_load_config_values`` returns a non-``arc_`` value to mimic the OAuth
    access token that ``arcade login`` stores, so the login-derivation path is
    exercised. The coordinator is supplied through a fake ``arcade_core.config``
    module so the real coordinator-to-engine resolution runs.
    """
    with (
        patch.object(
            MCPServer,
            "_load_config_values",
            return_value=("login-access-stub", "user@example.com"),
        ),
        patch.object(MCPServer, "_load_org_project_context", return_value=org_project),
        patch.dict(sys.modules, {"arcade_core.config": _fake_config_module(coordinator_url)}),
    ):
        return MCPServer(
            catalog=ToolCatalog(),
            settings=MCPSettings(),
            arcade_api_key=arcade_api_key,
            arcade_api_url=arcade_api_url,
        )


def _base_url(server: MCPServer) -> str:
    assert server.arcade is not None
    return str(server.arcade.base_url).rstrip("/")


class TestEngineUrlFromCoordinator:
    """The pure coordinator -> engine host mapping."""

    @pytest.mark.parametrize(
        ("coordinator", "expected"),
        [
            ("https://cloud.arcade.dev", "https://api.arcade.dev"),
            ("https://cloud.example.dev", "https://api.example.dev"),
            ("https://cloud.staging.example.com", "https://api.staging.example.com"),
            ("https://cloud.example.dev:8443", "https://api.example.dev:8443"),
        ],
    )
    def test_maps_cloud_host_to_api_host(self, coordinator, expected):
        assert _engine_url_from_coordinator(coordinator) == expected

    @pytest.mark.parametrize(
        "coordinator",
        [
            None,
            "",
            "http://localhost:8000",
            "https://gateway.example.dev",  # first label is not "cloud"
            "https://",  # truthy but no host
        ],
    )
    def test_returns_none_for_unrecognized_hosts(self, coordinator):
        assert _engine_url_from_coordinator(coordinator) is None


class TestArcadeClientUrlResolution:
    """End-to-end resolution through MCPServer construction."""

    def test_login_into_non_prod_targets_matching_engine(self):
        """The reported bug: a non-prod login must not hit the prod engine."""
        server = _build_server(coordinator_url="https://cloud.example.dev")
        assert _base_url(server) == "https://api.example.dev"

    def test_prod_login_targets_prod_engine(self):
        server = _build_server(coordinator_url="https://cloud.arcade.dev")
        assert _base_url(server) == PROD_ENGINE_URL

    def test_missing_coordinator_falls_back_to_prod(self):
        server = _build_server(coordinator_url=None)
        assert _base_url(server) == PROD_ENGINE_URL

    def test_localhost_coordinator_falls_back_to_prod(self):
        server = _build_server(coordinator_url="http://localhost:8000")
        assert _base_url(server) == PROD_ENGINE_URL

    def test_explicit_api_url_arg_wins_over_derivation(self):
        server = _build_server(
            coordinator_url="https://cloud.example.dev",
            arcade_api_url="https://api.override.dev",
        )
        assert _base_url(server) == "https://api.override.dev"

    def test_env_api_url_wins_over_derivation(self, monkeypatch):
        monkeypatch.setenv("ARCADE_API_URL", "https://api.fromenv.dev")
        server = _build_server(coordinator_url="https://cloud.example.dev")
        assert _base_url(server) == "https://api.fromenv.dev"

    def test_explicit_service_key_does_not_derive_from_login_config(self):
        """An explicit API key means the caller owns the key/URL pairing.

        A stale login coordinator in the config must not silently redirect a
        server that was handed its own service key.
        """
        server = _build_server(
            coordinator_url="https://cloud.example.dev",
            arcade_api_key="arc_service_key",
        )
        assert _base_url(server) == PROD_ENGINE_URL

    def test_coordinator_url_read_from_config(self):
        server = _build_server(coordinator_url="https://cloud.example.dev")
        with patch.dict(
            sys.modules,
            {"arcade_core.config": _fake_config_module("https://cloud.example.dev")},
        ):
            assert server._coordinator_url_from_config() == "https://cloud.example.dev"

    def test_coordinator_url_returns_none_when_config_unavailable(self):
        """A missing/broken config must degrade to ``None``, not raise."""
        server = _build_server(coordinator_url="https://cloud.example.dev")
        # A module with no ``config`` attribute makes the import inside the
        # method raise, which must be swallowed.
        broken = types.ModuleType("arcade_core.config")
        with patch.dict(sys.modules, {"arcade_core.config": broken}):
            assert server._coordinator_url_from_config() is None

    def test_derived_url_applies_with_org_scoped_client(self):
        """A login token carries org/project context; the org-scoped client
        rewrites paths but the derived engine host must still be the base URL."""
        server = _build_server(
            coordinator_url="https://cloud.example.dev",
            org_project=("org_1", "project_1"),
        )
        assert _base_url(server) == "https://api.example.dev"
