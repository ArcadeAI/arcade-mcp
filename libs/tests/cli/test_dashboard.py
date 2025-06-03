from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.constants import PROD_ENGINE_HOST
from arcade_cli.main import cli
from typer.testing import CliRunner

runner = CliRunner()


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
        patch("webbrowser.open") as mock_open,
        patch("arcade_cli.main.validate_and_get_config") as mock_validate,
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
    """Test fallback message when browser.open fails."""
    with (
        patch("webbrowser.open") as mock_open,
        patch("arcade_cli.main.validate_and_get_config") as mock_validate,
        patch("arcade_cli.main.log_engine_health") as mock_health_check,
        patch("arcade_cli.main.console.print") as mock_print,
    ):
        mock_open.return_value = False  # Failed to open browser
        mock_validate.return_value = MagicMock()
        mock_health_check.return_value = None

        result = runner.invoke(cli, ["dashboard"])

        assert result.exit_code == 0
        mock_print.assert_any_call(
            f"If a browser doesn't open automatically, copy this URL and paste it into your browser: https://{PROD_ENGINE_HOST}/dashboard",
            style="dim",
        )


def test_health_check_success():
    """Test successful health check."""
    with (
        patch("webbrowser.open") as mock_open,
        patch("arcade_cli.main.validate_and_get_config") as mock_validate,
        patch("arcade_cli.main.log_engine_health") as mock_health_check,
    ):
        mock_open.return_value = True
        mock_validate.return_value = MagicMock()
        mock_health_check.return_value = None  # Successful health check

        result = runner.invoke(cli, ["dashboard"])

        assert result.exit_code == 0
        mock_health_check.assert_called_once()
        mock_open.assert_called_once()
