import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.context import (
    ARCADE_URL_ENV,
    DiscoveryDocument,
    DiscoveryNotFoundError,
)
from arcade_cli.main import cli
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    return tmp_path


def _enabled_discovery() -> DiscoveryDocument:
    return DiscoveryDocument.model_validate({
        "engine": "https://engine.acme.internal",
        "coordinator": "https://coord.acme.internal",
        "dashboard": "https://dash.acme.internal",
        "version": "1.0.0",
        "deployments": {"enabled": True},
    })


def _login_result() -> MagicMock:
    result = MagicMock()
    result.email = "user@acme.internal"
    result.selected_org = MagicMock(name="Org")
    result.selected_org.name = "Org"
    result.selected_project = MagicMock()
    result.selected_project.name = "Proj"
    return result


class TestLoginByUrl:
    def test_login_url_saves_self_hosted_context(self, work_dir: Path):
        with (
            patch("arcade_cli.context.fetch_discovery", return_value=_enabled_discovery()),
            patch("arcade_cli.main.perform_oauth_login", return_value=_login_result()),
            patch("arcade_cli.main.save_credentials_from_whoami") as mock_save,
        ):
            result = runner.invoke(cli, ["login", "--url", "https://engine.acme.internal"])

        assert result.exit_code == 0, result.output
        mock_save.assert_called_once()
        kwargs = mock_save.call_args.kwargs
        assert kwargs["kind"] == "self_hosted"
        assert kwargs["engine_url"] == "https://engine.acme.internal"
        assert kwargs["context_name"] == "engine.acme.internal"

    def test_login_url_from_env(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        with (
            patch("arcade_cli.context.fetch_discovery", return_value=_enabled_discovery()),
            patch("arcade_cli.main.perform_oauth_login", return_value=_login_result()),
            patch("arcade_cli.main.save_credentials_from_whoami") as mock_save,
        ):
            result = runner.invoke(cli, ["login"])

        assert result.exit_code == 0, result.output
        mock_save.assert_called_once()

    def test_login_url_custom_context_name(self, work_dir: Path):
        with (
            patch("arcade_cli.context.fetch_discovery", return_value=_enabled_discovery()),
            patch("arcade_cli.main.perform_oauth_login", return_value=_login_result()),
            patch("arcade_cli.main.save_credentials_from_whoami") as mock_save,
        ):
            result = runner.invoke(
                cli,
                ["login", "--url", "https://engine.acme.internal", "--context", "prod"],
            )

        assert result.exit_code == 0, result.output
        assert mock_save.call_args.kwargs["context_name"] == "prod"

    def test_disabled_deployments_exit_nonzero_with_reason(self, work_dir: Path):
        doc = DiscoveryDocument.model_validate({
            "engine": "https://engine.acme.internal",
            "coordinator": "https://coord.acme.internal",
            "deployments": {"enabled": False, "reason": "deployments are not enabled"},
        })
        with (
            patch("arcade_cli.context.fetch_discovery", return_value=doc),
            patch("arcade_cli.main.perform_oauth_login") as mock_login,
            patch("arcade_cli.main.save_credentials_from_whoami") as mock_save,
        ):
            result = runner.invoke(cli, ["login", "--url", "https://engine.acme.internal"])

        assert result.exit_code != 0
        assert "deployments are not enabled" in result.output
        mock_login.assert_not_called()
        mock_save.assert_not_called()

    def test_missing_discovery_refuses_before_oauth(self, work_dir: Path):
        with (
            patch(
                "arcade_cli.context.fetch_discovery",
                side_effect=DiscoveryNotFoundError("This installation predates discovery."),
            ),
            patch("arcade_cli.main.perform_oauth_login") as mock_login,
        ):
            result = runner.invoke(cli, ["login", "--url", "https://engine.acme.internal"])

        assert result.exit_code != 0
        assert "predates discovery" in result.output
        mock_login.assert_not_called()
