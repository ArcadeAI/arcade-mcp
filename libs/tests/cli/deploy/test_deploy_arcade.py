"""`arcade deploy` for Arcade servers: the deploy config and checks, against a fake Engine."""

import base64
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from arcade_cli import deploy, deploy_arcade, deploy_mcp
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy import (
    DeployRefusedError,
    deploy_server_logic,
    start_server_process,
    wait_for_health,
)
from arcade_cli.deploy_checks import ProjectCheckError
from arcade_cli.deploy_config import DeployConfigError
from arcade_cli.deploy_wheels import WheelCheckResult
from arcade_core.subprocess_utils import graceful_terminate_process

VALID_SERVER = Path(__file__).parent / "test_servers" / "valid_server"
SECRET_VALUE = "sk-very-secret-value-1234"
PY312 = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]

# A server whose tool reads a declared value from os.environ; it won't start without them.
ENV_SERVER = '''
import os
from arcade_mcp_server import MCPApp

REQUIRED = [os.environ["REGION"], os.environ["SNOWFLAKE_TOKEN"]]
app = MCPApp(name="envserver", version="2.0.0")


@app.tool
def region() -> str:
    """The deployment's region."""
    return os.environ["REGION"]


if __name__ == "__main__":
    app.run(transport="http", host="127.0.0.1", port=8000)
'''

DEPLOY_CONFIG = (
    '\n[tool.arcade.deploy]\nsecrets = ["SNOWFLAKE_TOKEN"]\n'
    '[tool.arcade.deploy.environment]\nREGION = "us-east"\n'
)


class FakeEngine:
    """Records what the deploy sends and which project secrets it uploads."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, exists: bool = False) -> None:
        self.created: list[dict[str, Any]] = []
        self.updated: list[dict[str, Any]] = []
        self.project_secrets: list[set[str]] = []
        self.wheel_result = WheelCheckResult()
        monkeypatch.setattr(deploy, "resolve_active_context", lambda: SimpleNamespace(is_ci=True))
        monkeypatch.setattr(deploy, "resolve_engine_base_url", lambda *a: "http://engine.test")
        monkeypatch.setattr(deploy_arcade, "deployment_runners", lambda url: PY312)
        monkeypatch.setattr(deploy_mcp, "check_wheels", lambda *a, **k: self.wheel_result)
        monkeypatch.setattr(deploy, "server_already_exists", lambda url, name: exists)
        monkeypatch.setattr(
            deploy, "deploy_server_to_engine", lambda url, body, debug: self.created.append(body)
        )
        monkeypatch.setattr(
            deploy,
            "update_deployment",
            lambda url, name, body, debug: self.updated.append(body),
        )
        monkeypatch.setattr(deploy, "watch_rollout", lambda *a: None)
        monkeypatch.setattr(
            deploy,
            "upsert_secrets_to_engine",
            lambda url, names, debug: self.project_secrets.append(set(names)),
        )

    @property
    def uploaded(self) -> bool:
        return bool(self.created or self.updated)


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    return FakeEngine(monkeypatch)


@pytest.fixture(autouse=True)
def project_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # The servers run in the test interpreter's environment.
    monkeypatch.setenv("VIRTUAL_ENV", sys.prefix)


def arcade_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, pyproject_extra: str = ""
) -> Path:
    """The valid Arcade server, pinned, run from its directory."""
    project = tmp_path / "srv"
    project.mkdir()
    shutil.copy(VALID_SERVER / "server.py", project / "server.py")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "srv"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n'
        'dependencies = ["arcade-mcp-server==1.23.0"]\n' + pyproject_extra
    )
    monkeypatch.chdir(project)
    return project


def run_deploy(*, secrets: str = "auto", skip_validate: bool = False) -> None:
    deploy_server_logic(
        entrypoint="server.py",
        skip_validate=skip_validate,
        server_name="srv" if skip_validate else None,
        server_version="1.0.0" if skip_validate else None,
        secrets=secrets,
        host=None,
        port=None,
        force_tls=False,
        force_no_tls=False,
        debug=False,
    )


def bundle_files(body: dict[str, Any]) -> dict[str, bytes]:
    archive = body["toolkits"]["bundles"][0]["bytes"]
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(archive)), mode="r:gz") as tar:
        return {
            m.name: tar.extractfile(m).read()  # type: ignore[union-attr]
            for m in tar.getmembers()
            if m.isfile()
        }


class TestDeployConfig:
    def test_declared_environment_and_secrets_reach_the_server(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = arcade_project(tmp_path, monkeypatch, pyproject_extra=DEPLOY_CONFIG)
        (project / "server.py").write_text(ENV_SERVER)

        run_deploy()

        [body] = engine.created
        assert body["name"] == "envserver"
        assert body["environment"] == {"REGION": "us-east"}
        assert body["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE}
        bundle = body["toolkits"]["bundles"][0]
        assert bundle["type"] == "mcp"
        assert bundle["entrypoint"] == "server.py"
        output = capsys.readouterr().out
        assert "Deploy settings from pyproject.toml" in output
        assert SECRET_VALUE not in output

    def test_the_tool_reads_the_declared_values_from_os_environ(self, tmp_path: Path) -> None:
        project = tmp_path / "srv"
        project.mkdir()
        (project / "server.py").write_text(ENV_SERVER)
        env = {"REGION": "us-east", "SNOWFLAKE_TOKEN": SECRET_VALUE}

        process, port = start_server_process(
            str(project / "server.py"), python=Path(sys.executable), env=env
        )
        try:
            base_url = f"http://127.0.0.1:{port}"
            wait_for_health(base_url, process, timeout=20)
            response = httpx.post(
                f"{base_url}/worker/tools/invoke",
                json={
                    "execution_id": "test",
                    "tool": {"name": "Region", "toolkit": "Envserver"},
                    "inputs": {},
                },
                timeout=10,
            )
        finally:
            # On Windows the graceful stop may not end the server; kill it then.
            graceful_terminate_process(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        assert response.status_code == 200, response.text
        assert response.json()["output"]["value"] == "us-east"

    def test_a_declared_secret_isnt_also_uploaded_as_a_project_secret(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The valid server's tool requires MY_SECRET_KEY as a per-call project secret.
        monkeypatch.setenv("MY_SECRET_KEY", SECRET_VALUE)
        arcade_project(
            tmp_path, monkeypatch, pyproject_extra='\n[tool.arcade.deploy]\nsecrets = ["MY_SECRET_KEY"]\n'
        )

        run_deploy()

        assert engine.project_secrets == []
        assert engine.created[0]["secrets"] == {"MY_SECRET_KEY": SECRET_VALUE}

    def test_project_secrets_still_upload_beside_deployment_secrets(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MY_SECRET_KEY", "project-secret")
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        arcade_project(
            tmp_path,
            monkeypatch,
            pyproject_extra='\n[tool.arcade.deploy]\nsecrets = ["SNOWFLAKE_TOKEN"]\n',
        )

        run_deploy()

        assert engine.project_secrets == [{"MY_SECRET_KEY"}]
        assert engine.created[0]["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE}

    def test_a_redeploy_sends_the_full_declared_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        engine = FakeEngine(monkeypatch, exists=True)
        arcade_project(
            tmp_path,
            monkeypatch,
            pyproject_extra='\n[tool.arcade.deploy.environment]\nREGION = "us-east"\n',
        )

        run_deploy(skip_validate=True)

        [body] = engine.updated
        assert body["environment"] == {"REGION": "us-east"}
        assert body["secrets"] == {}

    def test_apt_packages_ship_in_the_bundle(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        arcade_project(
            tmp_path,
            monkeypatch,
            pyproject_extra='\n[tool.arcade.deploy]\napt_packages = ["unixodbc", "libaio1t64"]\n',
        )
        (tmp_path / "srv" / ".arcade").mkdir()
        (tmp_path / "srv" / ".arcade" / "deploy.json").write_text('{"stale": true}')

        run_deploy(skip_validate=True)

        files = bundle_files(engine.created[0])
        assert json.loads(files["srv/.arcade/deploy.json"]) == {
            "apt_packages": ["unixodbc", "libaio1t64"]
        }

    @pytest.mark.parametrize(
        "pyproject_extra",
        ["", "\n[tool.arcade.deploy]\napt_packages = []\n"],
        ids=["omitted", "empty"],
    )
    def test_no_apt_packages_ship_no_runner_settings(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        pyproject_extra: str,
    ) -> None:
        arcade_project(tmp_path, monkeypatch, pyproject_extra=pyproject_extra)

        run_deploy(skip_validate=True)

        assert "srv/.arcade/deploy.json" not in bundle_files(engine.created[0])


class TestRefusals:
    @pytest.mark.parametrize(
        ("packages", "named"),
        [
            ('["UnixODBC"]', "UnixODBC"),
            ('["./debs/unixodbc.deb"]', "./debs/unixodbc.deb"),
            ('["unixodbc=2.3.12-2"]', "unixodbc=2.3.12-2"),
            ('["unixodbc", "unixodbc"]', "unixodbc"),
        ],
        ids=["uppercase", "path", "version pin", "duplicate"],
    )
    def test_an_invalid_apt_package_is_refused_before_upload(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        packages: str,
        named: str,
    ) -> None:
        arcade_project(
            tmp_path,
            monkeypatch,
            pyproject_extra=f"\n[tool.arcade.deploy]\napt_packages = {packages}\n",
        )

        with pytest.raises(DeployConfigError, match=f"apt_packages: {re.escape(repr(named))}"):
            run_deploy(skip_validate=True)

        assert not engine.uploaded

    def test_a_reserved_name_is_refused_before_upload(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        arcade_project(
            tmp_path,
            monkeypatch,
            pyproject_extra='\n[tool.arcade.deploy.environment]\nARCADE_WORKER_SECRET = "x"\n',
        )

        with pytest.raises(DeployConfigError, match="ARCADE_WORKER_SECRET is reserved"):
            run_deploy()

        assert not engine.uploaded

    def test_requires_python_excluding_the_runner_is_refused_before_upload(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = arcade_project(tmp_path, monkeypatch)
        pyproject = (project / "pyproject.toml").read_text()
        (project / "pyproject.toml").write_text(pyproject.replace(">=3.10", ">=3.13"))

        with pytest.raises(ProjectCheckError, match=r"'>=3\.13'.*Python 3\.12"):
            run_deploy()

        assert not engine.uploaded

    def test_a_poetry_project_without_an_export_is_refused_before_upload(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = arcade_project(tmp_path, monkeypatch)
        (project / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "srv"\n[tool.poetry.dependencies]\n'
            'python = "^3.11"\narcade-mcp-server = "^1.23"\n'
        )

        with pytest.raises(ProjectCheckError, match="poetry export"):
            run_deploy()

        assert not engine.uploaded

    @pytest.mark.parametrize(
        "setting",
        [
            'command = "python server.py"',
            'path = "/mcp"',
            "api_key = { env = 'KEY', header = 'X-Key' }",
            "oauth_client = { client_id = 'id', client_secret_env = 'SECRET' }",
        ],
    )
    def test_mcp_only_settings_are_refused(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch, setting: str
    ) -> None:
        monkeypatch.setenv("SECRET", "value")
        arcade_project(tmp_path, monkeypatch, pyproject_extra=f"\n[tool.arcade.deploy]\n{setting}\n")

        with pytest.raises(DeployRefusedError, match="apply only to MCP servers"):
            run_deploy()

        assert not engine.uploaded

    def test_secrets_skip_with_declared_secrets_is_refused(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        arcade_project(tmp_path, monkeypatch, pyproject_extra=DEPLOY_CONFIG)

        with pytest.raises(DeployRefusedError, match="--secrets skip"):
            run_deploy(secrets="skip")

        assert not engine.uploaded

    def test_a_declared_secret_with_no_value_is_refused(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SNOWFLAKE_TOKEN", raising=False)
        arcade_project(tmp_path, monkeypatch, pyproject_extra=DEPLOY_CONFIG)

        with pytest.raises(DeployConfigError, match="SNOWFLAKE_TOKEN"):
            run_deploy()

        assert not engine.uploaded

    def test_a_project_without_a_virtual_environment_is_refused(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("VIRTUAL_ENV")
        arcade_project(tmp_path, monkeypatch)

        with pytest.raises(DeployRefusedError, match="no virtual environment"):
            run_deploy()

        assert not engine.uploaded

    def test_skip_validate_needs_no_virtual_environment(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("VIRTUAL_ENV")
        arcade_project(tmp_path, monkeypatch)

        run_deploy(skip_validate=True)

        assert engine.uploaded


class TestWarnings:
    def test_unpinned_uv_sources_and_missing_wheels_warn(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        engine.wheel_result = WheelCheckResult(warnings=["pyodbc has no prebuilt wheel"])
        project = arcade_project(tmp_path, monkeypatch)
        (project / "pyproject.toml").write_text(
            '[project]\nname = "srv"\nversion = "0.1.0"\n'
            'dependencies = ["arcade-mcp-server>=1.23", "example-sdk==0.2.0"]\n'
            '[tool.uv.sources]\nexample-sdk = { path = "../sdk" }\n'
        )

        run_deploy(skip_validate=True)

        output = " ".join(capsys.readouterr().out.split())
        assert "aren't pinned" in output
        assert "arcade-mcp-server" in output
        assert "[tool.uv.sources]" in output
        assert "pyodbc has no prebuilt wheel" in output
        assert engine.uploaded


class TestWithoutDeployConfig:
    def test_an_existing_project_deploys_unchanged(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("MY_SECRET_KEY", SECRET_VALUE)
        arcade_project(tmp_path, monkeypatch)

        run_deploy()

        [body] = engine.created
        assert set(body) == {"name", "description", "toolkits"}
        assert body["name"] == "simpleserver"
        [bundle] = body["toolkits"]["bundles"]
        assert {k: v for k, v in bundle.items() if k != "bytes"} == {
            "name": "simpleserver",
            "version": "1.0.0",
            "type": "mcp",
            "entrypoint": "server.py",
        }
        assert set(bundle_files(body)) == {"srv/pyproject.toml", "srv/server.py"}
        assert engine.project_secrets == [{"MY_SECRET_KEY"}]

    def test_an_update_carries_no_environment_or_secrets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        engine = FakeEngine(monkeypatch, exists=True)
        arcade_project(tmp_path, monkeypatch)

        run_deploy(skip_validate=True)

        [body] = engine.updated
        assert set(body) == {"description", "toolkits"}
        assert engine.project_secrets == []

    def test_an_engine_without_runners_skips_the_runner_checks(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(deploy_arcade, "deployment_runners", lambda url: [])
        project = arcade_project(tmp_path, monkeypatch)
        pyproject = (project / "pyproject.toml").read_text()
        (project / "pyproject.toml").write_text(pyproject.replace(">=3.10", ">=3.99"))

        run_deploy(skip_validate=True)

        assert engine.uploaded


class TestDeploymentRunners:
    def test_an_engine_without_discovery_has_no_runners(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from arcade_cli.context import DiscoveryNotFoundError

        def missing(url: str) -> None:
            raise DiscoveryNotFoundError("no discovery")

        monkeypatch.setattr(deploy, "fetch_discovery", missing)

        assert deploy.deployment_runners("http://engine.test") == []

    def test_only_python_runners_are_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from arcade_cli.context import DiscoveryDocument

        document = DiscoveryDocument.model_validate({
            "deployments": {
                "enabled": True,
                "protocols": ["arcade"],
                "runners": [
                    {"language": "python", "version": "3.12", "platform": "musllinux_1_2"},
                    {"language": "node", "version": "22"},
                ],
            }
        })
        monkeypatch.setattr(deploy, "fetch_discovery", lambda url: document)

        assert deploy.deployment_runners("http://engine.test") == PY312
