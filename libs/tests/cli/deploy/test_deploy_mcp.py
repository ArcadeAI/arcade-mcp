"""`arcade deploy` for MCP servers, against a fake Engine and stand-in servers."""

import base64
import io
import json
import shutil
import socket
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest
from arcade_cli import deploy_mcp
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy import DeployRefusedError
from arcade_cli.deploy_checks import ProjectCheckError
from arcade_cli.deploy_mcp import deploy_mcp_server, deploys_mcp_server

FAKES = Path(__file__).parent / "start_command_servers" / "fakes"
SECRET_VALUE = "sk-very-secret-value-1234"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FakeEngine:
    """Records what the deploy sends; hosts MCP servers unless told otherwise."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, exists: bool = False) -> None:
        self.created: list[dict[str, Any]] = []
        self.updated: list[dict[str, Any]] = []
        self.watched: list[str] = []
        runners = [DeploymentsRunner(language="python", version="3.12", platform="musllinux_1_2")]
        monkeypatch.setattr(deploy_mcp, "check_mcp_deployments", lambda url: runners)
        monkeypatch.setattr(deploy_mcp, "server_already_exists", lambda url, name: exists)
        monkeypatch.setattr(
            deploy_mcp, "deploy_server_to_engine", lambda url, body, debug: self.created.append(body)
        )
        monkeypatch.setattr(
            deploy_mcp,
            "update_deployment",
            lambda url, name, body, debug: self.updated.append(body),
        )
        monkeypatch.setattr(
            deploy_mcp, "watch_rollout", lambda url, name, debug, is_update: self.watched.append(name)
        )

    @property
    def uploaded(self) -> bool:
        return bool(self.created or self.updated)


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    return FakeEngine(monkeypatch)


@pytest.fixture(autouse=True)
def project_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # The stand-in servers run in the test interpreter's environment.
    monkeypatch.setenv("VIRTUAL_ENV", sys.prefix)


def stand_in(tmp_path: Path, *, arcade_toml: str = "", server_args: str = "") -> Path:
    """A project whose `command` starts the stand-in MCP server."""
    project = tmp_path / "srv"
    project.mkdir()
    for fake in FAKES.glob("*.py"):
        shutil.copy(fake, project / fake.name)
    (project / "requirements.txt").write_text("fastmcp==4.1.3\n")
    # The port goes last so the command never ends in a quote, which older TOML parsers
    # reject next to the closing delimiter.
    command = " ".join(filter(None, ["python fake_mcp.py", server_args, f"--port {free_port()}"]))
    # A literal string, so a command holding JSON or quotes needs no escaping.
    literal = "'''"
    (project / "arcade.toml").write_text(
        f"[deploy]\ncommand = {literal}{command}{literal}\n{arcade_toml}"
    )
    return project


def deploy(project: Path, *, secrets: str = "auto") -> None:
    deploy_mcp_server(
        project,
        "http://engine.test",
        skip_validate=False,
        server_name=None,
        server_version=None,
        secrets=secrets,
        debug=False,
        provider=None,
    )


def bundle_files(body: dict[str, Any]) -> dict[str, bytes]:
    archive = body["toolkits"]["bundles"][0]["bytes"]
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(archive)), mode="r:gz") as tar:
        return {
            m.name: tar.extractfile(m).read()  # type: ignore[union-attr]
            for m in tar.getmembers()
            if m.isfile()
        }


class TestDeploy:
    def test_an_mcp_server_deploys_with_its_command_and_declared_values(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = stand_in(
            tmp_path,
            arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n[deploy.environment]\nREGION = "us-east"\n',
        )

        deploy(project)

        [body] = engine.created
        assert body["name"] == "fake-mcp"
        bundle = body["toolkits"]["bundles"][0]
        assert bundle["protocol"] == "mcp"
        assert bundle["command"].startswith("python fake_mcp.py --port")
        assert bundle["version"] == "1.0.0"
        assert "type" not in bundle
        assert body["environment"] == {"REGION": "us-east"}
        assert body["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE}
        assert engine.watched == ["fake-mcp"]
        output = capsys.readouterr().out
        assert "SNOWFLAKE_TOKEN" in output
        assert SECRET_VALUE not in output
        assert SECRET_VALUE[-4:] not in output

    def test_a_redeploy_replaces_the_full_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        engine = FakeEngine(monkeypatch, exists=True)
        project = stand_in(tmp_path, arcade_toml="[deploy.environment]\nREGION = \"us-east\"\n")

        deploy(project)

        [body] = engine.updated
        assert body["environment"] == {"REGION": "us-east"}
        assert body["secrets"] == {}
        assert "oauth_client" not in body

    def test_the_runner_settings_ship_in_the_bundle(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(tmp_path, arcade_toml='path = "/api/mcp"\n', server_args="--path /api/mcp")
        (project / "uv.lock").write_text("version = 1\n")

        deploy(project)

        files = bundle_files(engine.created[0])
        assert json.loads(files["srv/.arcade/deploy.json"]) == {"path": "/api/mcp"}
        assert "srv/uv.lock" in files

    def test_a_server_that_needs_a_token_to_list_tools_still_deploys(
        self, tmp_path: Path, engine: FakeEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = stand_in(tmp_path, server_args="--bearer-for-tools secret")

        deploy(project)

        assert engine.created
        assert "needs a token to list its tools" in capsys.readouterr().out

class TestSecretsMode:
    def test_a_mode_other_than_auto_is_noted_and_the_declared_secrets_are_sent(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = stand_in(tmp_path, arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n')

        deploy(project, secrets="skip")

        assert engine.created[0]["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE}
        assert "--secrets skip doesn't apply to MCP servers yet" in capsys.readouterr().out


class TestRefusedBeforeUpload:
    def refused(self, project: Path, engine: FakeEngine, match: str, **kwargs: Any) -> None:
        with pytest.raises(ValueError, match=match):
            deploy(project, **kwargs)
        assert not engine.uploaded

    def test_a_declared_secret_with_no_value(self, tmp_path: Path, engine: FakeEngine) -> None:
        project = stand_in(tmp_path, arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n')

        self.refused(project, engine, r"\bSNOWFLAKE_TOKEN\b")

    @pytest.mark.parametrize("name", ["PATH", "ARCADE_RUNNER_REGION", "FASTMCP_HOME"])
    def test_a_reserved_environment_name(self, tmp_path: Path, engine: FakeEngine, name: str) -> None:
        project = stand_in(tmp_path, arcade_toml=f'[deploy.environment]\n{name} = "x"\n')

        self.refused(project, engine, rf"\b{name}\b.*reserved")

    def test_a_server_that_runs_its_own_authorization_server(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        document = json.dumps({"issuer": "https://auth.example", "authorization_endpoint": "x"})
        project = stand_in(
            tmp_path,
            server_args=f"--bearer secret --well-known 'oauth-authorization-server={document}'",
        )
        (project / "auth.py").write_text("from fastmcp.server.auth.providers.github import GitHubProvider\n")

        self.refused(project, engine, r"authorization server \(GitHubProvider\)")

    def test_an_own_sign_in_import_with_skip_validate(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(tmp_path)
        (project / "auth.py").write_text("from fastmcp.server.auth import OAuthProxy\n")

        with pytest.raises(ValueError, match="authorization server"):
            deploy_mcp_server(
                project,
                "http://engine.test",
                skip_validate=True,
                server_name="srv",
                server_version="1.0.0",
                secrets="auto",
                debug=False,
                provider=None,
            )
        assert not engine.uploaded

    def test_no_supported_framework(self, tmp_path: Path, engine: FakeEngine) -> None:
        project = tmp_path / "plain"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "plain-tools"\nversion = "0.1.0"\n')
        (project / "server.py").write_text("print('hi')\n")

        self.refused(project, engine, "`command`")

    def test_no_virtual_environment(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("VIRTUAL_ENV")
        project = stand_in(tmp_path)
        (project / "uv.lock").write_text("version = 1\n")

        self.refused(project, engine, r"no virtual environment.*`uv sync`")


class TestRouting:
    def test_an_arcade_project_takes_the_arcade_path(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = ["arcade-mcp-server>=1.23"]\n'
        )

        assert not deploys_mcp_server(tmp_path)

    def test_a_fastmcp_project_takes_the_mcp_path(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("fastmcp==4.1.3\n")

        assert deploys_mcp_server(tmp_path)

    def test_a_project_with_no_dependency_file_keeps_the_arcade_message(
        self, tmp_path: Path
    ) -> None:
        assert not deploys_mcp_server(tmp_path)

    @pytest.mark.parametrize(
        ("name", "content", "match"),
        [
            ("fastmcp.json", "{not json", "fastmcp.json couldn't be read"),
            ("pyproject.toml", "[project\n", "pyproject.toml couldn't be read"),
        ],
    )
    def test_a_dependency_file_that_cant_be_read_is_reported_not_routed_to_arcade(
        self, tmp_path: Path, name: str, content: str, match: str
    ) -> None:
        (tmp_path / name).write_text(content)

        with pytest.raises(ProjectCheckError, match=match):
            deploys_mcp_server(tmp_path)



def test_refusals_are_value_errors() -> None:
    assert issubclass(DeployRefusedError, ValueError)
