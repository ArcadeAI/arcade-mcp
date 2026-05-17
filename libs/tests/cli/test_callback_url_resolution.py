"""Tests that each CLI command callback resolves its target URL via the
``resolve_engine_url`` / ``resolve_coordinator_url`` helpers, so the URL saved
at login is used as the default and explicit flags still override it.
"""

from datetime import datetime, timedelta

import pytest
from arcade_core.config_model import AuthConfig, Config
from typer.testing import CliRunner

from arcade_cli.org import app as org_app
from arcade_cli.project import app as project_app
from arcade_cli.secret import app as secret_app
from arcade_cli.server import app as server_app


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


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# server
# ---------------------------------------------------------------------------


def test_server_callback_uses_saved_engine_url(staged_config, runner) -> None:
    import arcade_cli.server as mod

    runner.invoke(server_app, ["list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.example.dev"


def test_server_callback_explicit_host_overrides_saved(staged_config, runner) -> None:
    import arcade_cli.server as mod

    runner.invoke(server_app, ["-h", "api.arcade.dev", "list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.arcade.dev"


def test_server_callback_no_creds_falls_back_to_prod(isolated_config_dir, runner) -> None:
    import arcade_cli.server as mod

    runner.invoke(server_app, ["list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.arcade.dev"


# ---------------------------------------------------------------------------
# secret
# ---------------------------------------------------------------------------


def test_secret_callback_uses_saved_engine_url(staged_config, runner) -> None:
    import arcade_cli.secret as mod

    runner.invoke(secret_app, ["list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.example.dev"


def test_secret_callback_explicit_host_overrides_saved(staged_config, runner) -> None:
    import arcade_cli.secret as mod

    runner.invoke(secret_app, ["-h", "api.arcade.dev", "list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.arcade.dev"


def test_secret_callback_no_creds_falls_back_to_prod(isolated_config_dir, runner) -> None:
    import arcade_cli.secret as mod

    runner.invoke(secret_app, ["list"], catch_exceptions=True)
    assert mod.state["engine_url"] == "https://api.arcade.dev"


# ---------------------------------------------------------------------------
# org
# ---------------------------------------------------------------------------


def test_org_callback_uses_saved_coordinator_url(staged_config, runner) -> None:
    import arcade_cli.org as mod

    runner.invoke(org_app, ["list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.example.dev"


def test_org_callback_explicit_host_overrides_saved(staged_config, runner) -> None:
    import arcade_cli.org as mod

    runner.invoke(org_app, ["-h", "cloud.arcade.dev", "list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.arcade.dev"


def test_org_callback_no_creds_falls_back_to_prod(isolated_config_dir, runner) -> None:
    import arcade_cli.org as mod

    runner.invoke(org_app, ["list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.arcade.dev"


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------


def test_project_callback_uses_saved_coordinator_url(staged_config, runner) -> None:
    import arcade_cli.project as mod

    runner.invoke(project_app, ["list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.example.dev"


def test_project_callback_explicit_host_overrides_saved(staged_config, runner) -> None:
    import arcade_cli.project as mod

    runner.invoke(project_app, ["-h", "cloud.arcade.dev", "list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.arcade.dev"


def test_project_callback_no_creds_falls_back_to_prod(isolated_config_dir, runner) -> None:
    import arcade_cli.project as mod

    runner.invoke(project_app, ["list"], catch_exceptions=True)
    assert mod.state["coordinator_url"] == "https://cloud.arcade.dev"


# ---------------------------------------------------------------------------
# show / deploy / dashboard (commands on the root CLI)
# ---------------------------------------------------------------------------


def test_show_uses_saved_engine_url(staged_config, runner) -> None:
    from unittest.mock import patch

    from arcade_cli.main import cli

    with patch("arcade_cli.show.get_tools_from_engine", return_value=[]) as mock_get_tools:
        runner.invoke(cli, ["show"], catch_exceptions=True)

    assert mock_get_tools.call_count == 1
    kwargs = mock_get_tools.call_args.kwargs
    args = mock_get_tools.call_args.args
    received_host = kwargs.get("host", args[0] if args else None)
    assert received_host is None or received_host == "https://api.example.dev"


def test_dashboard_uses_saved_engine_url(staged_config, runner) -> None:
    from unittest.mock import MagicMock, patch

    from arcade_cli.main import cli

    with (
        patch("arcade_cli.main._open_browser", return_value=True) as mock_open,
        patch("arcade_cli.utils.validate_and_get_config", return_value=MagicMock()),
        patch("arcade_cli.main.log_engine_health", return_value=None),
    ):
        result = runner.invoke(cli, ["dashboard"], catch_exceptions=False)

    assert result.exit_code == 0
    mock_open.assert_called_once_with("https://api.example.dev/dashboard")


def test_dashboard_explicit_host_overrides_saved(staged_config, runner) -> None:
    from unittest.mock import MagicMock, patch

    from arcade_cli.main import cli

    with (
        patch("arcade_cli.main._open_browser", return_value=True) as mock_open,
        patch("arcade_cli.utils.validate_and_get_config", return_value=MagicMock()),
        patch("arcade_cli.main.log_engine_health", return_value=None),
    ):
        result = runner.invoke(
            cli, ["dashboard", "-h", "api.arcade.dev"], catch_exceptions=False
        )

    assert result.exit_code == 0
    mock_open.assert_called_once_with("https://api.arcade.dev/dashboard")
