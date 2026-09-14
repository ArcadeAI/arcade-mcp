import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

        requested_urls: list[str] = []

        def fake_client(*args, **kwargs):
            client = MagicMock()

            def _get(url, *a, **kw):
                requested_urls.append(url)
                resp = MagicMock()
                resp.status_code = 404
                return resp

            def _post(url, *a, **kw):
                requested_urls.append(url)
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {}
                resp.raise_for_status.return_value = None
                return resp

            client.get.side_effect = _get
            client.post.side_effect = _post
            client.close.return_value = None
            return client

        with (
            patch("arcade_cli.deploy.httpx.Client", side_effect=fake_client),
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

        assert "https://engine.acme.internal/v1/workers/srv" in requested_urls
        assert "https://engine.acme.internal/v1/deployments" in requested_urls

    def test_ci_auth_headers_use_api_key(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "ci-key"

        from arcade_cli.utils import get_auth_headers

        assert get_auth_headers() == {"Authorization": "Bearer ci-key"}


class TestApiKeyScopedUrl:
    def test_ci_mode_builds_non_scoped_urls_without_config(self, work_dir: Path):
        os.environ[ARCADE_URL_ENV] = "https://engine.acme.internal"
        os.environ[ARCADE_API_KEY_ENV] = "ci-key"

        from arcade_cli.utils import get_org_scoped_url

        assert (
            get_org_scoped_url("https://engine.acme.internal", "/deployments")
            == "https://engine.acme.internal/v1/deployments"
        )
        assert (
            get_org_scoped_url("https://engine.acme.internal", "/workers/srv")
            == "https://engine.acme.internal/v1/workers/srv"
        )
        assert (
            get_org_scoped_url("https://engine.acme.internal", "/secrets/KEY")
            == "https://engine.acme.internal/v1/admin/secrets/KEY"
        )
