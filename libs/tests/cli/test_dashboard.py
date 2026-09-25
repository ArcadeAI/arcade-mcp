from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.context import ARCADE_API_KEY_ENV, ARCADE_URL_ENV
from arcade_cli.main import cli
from arcade_core.config_model import Config, ContextConfig
from arcade_core.constants import PROD_ENGINE_HOST
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
    monkeypatch.delenv(ARCADE_URL_ENV, raising=False)
    monkeypatch.delenv(ARCADE_API_KEY_ENV, raising=False)
    return tmp_path


def _write_config(context: ContextConfig | None) -> None:
    Config(context=context).save_to_file()


@pytest.mark.parametrize(
    "args, expected_url",
    [
        ([], f"https://{PROD_ENGINE_HOST}/dashboard"),
        (["--local"], "http://localhost:9099/dashboard"),
        (["--host", "custom.host.com"], "https://custom.host.com/dashboard"),
        (["-h", "api.arcade.dev", "-p", "9099"], "https://api.arcade.dev:9099/dashboard"),
        (["--local", "--port", "9099"], "http://localhost:9099/dashboard"),
        (["--local", "--tls"], "https://localhost:9099/dashboard"),
        (["--no-tls"], f"http://{PROD_ENGINE_HOST}/dashboard"),
    ],
)
def test_dashboard_url_construction(args, expected_url):
    """Test that the dashboard command constructs the correct URL with various args."""
    with (
        patch("arcade_cli.main._open_browser") as mock_open,
        patch("arcade_cli.utils.validate_and_get_config") as mock_validate,
        patch("arcade_cli.main.log_engine_health") as mock_health_check,
    ):
        # Setup mocks
        mock_open.return_value = True  # Successfully opened browser
        mock_validate.return_value = MagicMock()
        mock_health_check.return_value = None  # Successful health check

        # Run command
        result = runner.invoke(cli, ["dashboard", *args])

        assert result.exit_code == 0
        mock_open.assert_called_once_with(expected_url)
        mock_health_check.assert_called_once()


def test_fallback_when_browser_fails():
    """Test fallback message when _open_browser fails."""
    with (
        patch("arcade_cli.main._open_browser") as mock_open,
        patch("arcade_cli.utils.validate_and_get_config") as mock_validate,
        patch("arcade_cli.main.log_engine_health") as mock_health_check,
        patch("arcade_cli.main.console.print") as mock_print,
    ):
        mock_open.return_value = False  # Failed to open browser
        mock_validate.return_value = MagicMock()
        mock_health_check.return_value = None

        result = runner.invoke(cli, ["dashboard"])

        assert result.exit_code == 0
        # The fallback message should mention the URL and hint about manual paste.
        fallback_calls = [
            call for call in mock_print.call_args_list
            if "browser" in str(call).lower() and "dashboard" in str(call).lower()
        ]
        assert len(fallback_calls) >= 1, (
            f"Expected a fallback message about browser. Got calls: {mock_print.call_args_list}"
        )


def test_health_check_success():
    """Test successful health check."""
    with (
        patch("arcade_cli.main._open_browser") as mock_open,
        patch("arcade_cli.utils.validate_and_get_config") as mock_validate,
        patch("arcade_cli.main.log_engine_health") as mock_health_check,
    ):
        mock_open.return_value = True
        mock_validate.return_value = MagicMock()
        mock_health_check.return_value = None  # Successful health check

        result = runner.invoke(cli, ["dashboard"])

        assert result.exit_code == 0
        mock_health_check.assert_called_once()
        mock_open.assert_called_once()


ACTIVE_CONTEXT = ContextConfig(
    org_id="org_123",
    org_name="Acme",
    project_id="proj_456",
    project_name="Default",
)


def _open_dashboard(*args: str) -> MagicMock:
    with (
        patch("arcade_cli.main._open_browser", return_value=True) as mock_open,
        patch("arcade_cli.main.log_engine_health"),
    ):
        result = runner.invoke(cli, ["dashboard", *args])

    assert result.exit_code == 0, result.output
    return mock_open


def test_dashboard_opens_active_org_and_project():
    _write_config(ACTIVE_CONTEXT)

    mock_open = _open_dashboard()

    mock_open.assert_called_once_with(
        f"https://{PROD_ENGINE_HOST}/dashboard/orgs/org_123/projects/proj_456"
    )


def test_dashboard_appends_active_org_and_project_to_discovered_dashboard():
    Config(
        context=ACTIVE_CONTEXT,
        kind="self_hosted",
        dashboard_url="https://dashboard.acme.internal/",
    ).save_to_file()

    mock_open = _open_dashboard()

    mock_open.assert_called_once_with(
        "https://dashboard.acme.internal/orgs/org_123/projects/proj_456"
    )


@pytest.mark.parametrize(
    "args, expected_url",
    [
        (["--local"], "http://localhost:9099/dashboard"),
        (["--host", "custom.host.com"], "https://custom.host.com/dashboard"),
    ],
)
def test_dashboard_on_an_explicit_host_ignores_active_context(args, expected_url):
    _write_config(ACTIVE_CONTEXT)

    mock_open = _open_dashboard(*args)

    mock_open.assert_called_once_with(expected_url)


def test_dashboard_in_ci_mode_ignores_saved_context(monkeypatch):
    _write_config(ACTIVE_CONTEXT)
    monkeypatch.setenv(ARCADE_URL_ENV, "https://engine.acme.internal")
    monkeypatch.setenv(ARCADE_API_KEY_ENV, "the-ci-key")

    mock_open = _open_dashboard()

    mock_open.assert_called_once_with("https://engine.acme.internal/dashboard")


def test_dashboard_without_active_context_opens_default():
    _write_config(None)

    with (
        patch("arcade_cli.main._open_browser", return_value=True) as mock_open,
        patch("arcade_cli.main.log_engine_health"),
    ):
        result = runner.invoke(cli, ["dashboard"])

    assert result.exit_code == 0
    mock_open.assert_called_once_with(f"https://{PROD_ENGINE_HOST}/dashboard")
