from unittest.mock import patch

from arcade_cli import org, project
from arcade_core.config_model import Config, ContextConfig
from typer.testing import CliRunner

runner = CliRunner()


@patch("arcade_cli.org.fetch_organizations", return_value=[])
@patch(
    "arcade_core.config_model.Config.load_from_file",
    return_value=Config(coordinator_url="https://coordinator.example.com"),
)
def test_org_uses_saved_coordinator_url(_load_config, fetch_organizations):
    result = runner.invoke(org.app, ["list"])

    assert result.exit_code == 0
    fetch_organizations.assert_called_once_with("https://coordinator.example.com")


@patch("arcade_cli.project.fetch_projects", return_value=[])
@patch(
    "arcade_core.config_model.Config.load_from_file",
    return_value=Config(
        coordinator_url="https://coordinator.example.com",
        context=ContextConfig(
            org_id="org-id",
            org_name="Example",
            project_id="project-id",
            project_name="Default",
        ),
    ),
)
def test_project_uses_saved_coordinator_url(_load_config, fetch_projects):
    result = runner.invoke(project.app, ["list"])

    assert result.exit_code == 0
    fetch_projects.assert_called_once_with("https://coordinator.example.com", "org-id")


@patch("arcade_cli.org.fetch_organizations", return_value=[])
@patch(
    "arcade_core.config_model.Config.load_from_file",
    return_value=Config(coordinator_url="https://coordinator.example.com"),
)
def test_explicit_host_overrides_saved_coordinator_url(_load_config, fetch_organizations):
    result = runner.invoke(org.app, ["--host", "override.example.com", "list"])

    assert result.exit_code == 0
    fetch_organizations.assert_called_once_with("https://override.example.com")
