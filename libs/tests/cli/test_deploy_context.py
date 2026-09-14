import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from arcade_cli.context import ARCADE_API_KEY_ENV, ARCADE_URL_ENV
from arcade_cli.deploy import deploy_server_logic
from arcade_cli.main import cli
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir()
    return tmp_path


@pytest.fixture
def project_dir(work_dir: Path) -> Path:
    proj = work_dir / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\nname = 'x'\nversion = '0.1.0'\n")
    (proj / "server.py").write_text("")
    return proj


class TestUnauthenticatedDeploy:
    def test_names_the_login_command(self, work_dir: Path):
        os.environ.pop(ARCADE_URL_ENV, None)
        os.environ.pop(ARCADE_API_KEY_ENV, None)

        result = runner.invoke(cli, ["deploy"])

        assert result.exit_code != 0
        assert "arcade login" in result.output


class TestCiDeploy:
    def test_ci_env_deploys_without_interaction(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "ci-key"
        monkeypatch.chdir(project_dir)

        with (
            patch("arcade_cli.deploy.server_already_exists", return_value=False) as mock_exists,
            patch("arcade_cli.deploy.deploy_server_to_engine") as mock_deploy,
            patch(
                "arcade_cli.deploy._monitor_deployment_with_logs",
                new=AsyncMock(return_value=("running", [])),
            ),
        ):
            deploy_server_logic(
                entrypoint="server.py",
                skip_validate=True,
                server_name="srv",
                server_version="1.0.0",
                secrets="skip",
                host=None,
                port=None,
                force_tls=False,
                force_no_tls=False,
                debug=False,
            )

        mock_exists.assert_called_once()
        assert mock_exists.call_args.args[0] == "https://engine.acme.internal"
        mock_deploy.assert_called_once()
        assert mock_deploy.call_args.args[0] == "https://engine.acme.internal"

    def test_ci_auth_headers_use_api_key(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "ci-key"

        from arcade_cli.utils import get_auth_headers

        assert get_auth_headers() == {"Authorization": "Bearer ci-key"}
