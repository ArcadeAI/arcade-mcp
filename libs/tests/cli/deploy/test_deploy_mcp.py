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
from arcade_cli.deploy_mcp import (
    deploy_mcp_server,
    deploys_mcp_server,
    engine_toolkit_name,
    framework_warning,
)
from arcade_cli.deploy_wheels import WheelCheckResult

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
        self.wheel_result = WheelCheckResult()
        monkeypatch.setattr(deploy_mcp, "check_wheels", lambda *a, **k: self.wheel_result)
        monkeypatch.setattr(deploy_mcp, "server_already_exists", lambda url, name: exists)
        monkeypatch.setattr(
            deploy_mcp,
            "deploy_server_to_engine",
            lambda url, body, debug: self.created.append(body),
        )
        monkeypatch.setattr(
            deploy_mcp,
            "update_deployment",
            lambda url, name, body, debug: self.updated.append(body),
        )
        monkeypatch.setattr(
            deploy_mcp,
            "watch_rollout",
            lambda url, name, debug, is_update: self.watched.append(name),
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


def deploy(
    project: Path,
    *,
    secrets: str = "auto",
    env_file: Path | None = None,
    skip_validate: bool = False,
) -> None:
    deploy_mcp_server(
        project,
        "http://engine.test",
        skip_validate=skip_validate,
        server_name="srv" if skip_validate else None,
        server_version="1.0.0" if skip_validate else None,
        secrets=secrets,
        debug=False,
        provider=None,
        env_file=env_file,
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
        project = stand_in(tmp_path, arcade_toml='[deploy.environment]\nREGION = "us-east"\n')

        deploy(project)

        [body] = engine.updated
        assert body["environment"] == {"REGION": "us-east"}
        assert body["secrets"] == {}
        assert "oauth_client" not in body

    def test_the_runner_settings_ship_in_the_bundle(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(
            tmp_path, arcade_toml='path = "/api/mcp"\n', server_args="--path /api/mcp"
        )
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

    def test_packages_without_wheels_are_a_warning_not_a_refusal(
        self, tmp_path: Path, engine: FakeEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        engine.wheel_result = WheelCheckResult(
            warnings=["These packages have no prebuilt wheel for the runner: mysqlclient 2.3.0."],
            notes=["The wheel check for the runner (musllinux_1_2, Python 3.12, aarch64) didn't"],
        )
        project = stand_in(tmp_path)

        deploy(project)

        assert engine.created
        output = capsys.readouterr().out
        assert "[!] These packages have no prebuilt wheel for the runner: mysqlclient" in output
        assert "[!] The wheel check for the runner" in output


class TestSecretsMode:
    def test_all_sends_every_env_file_entry_and_the_declared_secrets(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = stand_in(
            tmp_path,
            arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n[deploy.environment]\nREGION = "us-east"\n',
        )
        env_file = project / ".env"
        env_file.write_text("EXTRA_TOKEN=extra-value\nREGION=eu-west\n")

        deploy(project, secrets="all", env_file=env_file)

        [body] = engine.created
        assert body["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE, "EXTRA_TOKEN": "extra-value"}
        # A name declared as an environment value stays one.
        assert body["environment"] == {"REGION": "us-east"}

    def test_all_refuses_a_reserved_name_in_env_file(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(tmp_path)
        env_file = project / ".env"
        env_file.write_text("EXTRA_TOKEN=x\nARCADE_WORKER_SECRET=y\n")

        with pytest.raises(DeployRefusedError, match=r"ARCADE_WORKER_SECRET.*reserves"):
            deploy(project, secrets="all", env_file=env_file)
        assert not engine.uploaded

    def test_skip_with_declared_secrets_is_refused(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = stand_in(tmp_path, arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n')

        with pytest.raises(DeployRefusedError, match=r"--secrets skip.*SNOWFLAKE_TOKEN"):
            deploy(project, secrets="skip")
        assert not engine.uploaded

    def test_skip_without_declared_secrets_deploys(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(tmp_path)

        deploy(project, secrets="skip")

        assert engine.created[0]["secrets"] == {}

    def test_skip_validate_keeps_auto_sending_the_declared_secrets(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SNOWFLAKE_TOKEN", SECRET_VALUE)
        project = stand_in(tmp_path, arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n')

        deploy(project, skip_validate=True)

        assert engine.created[0]["secrets"] == {"SNOWFLAKE_TOKEN": SECRET_VALUE}


class TestApiKey:
    def test_a_key_declared_as_a_secret_reaches_the_server_in_its_header(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("SERVER_KEY", SECRET_VALUE)
        project = stand_in(
            tmp_path,
            arcade_toml=(
                'secrets = ["SERVER_KEY"]\n'
                '[deploy.api_key]\nenv = "SERVER_KEY"\nheader = "X-API-Key"\n'
            ),
            # The server checks the header against a fixed key, not its environment.
            server_args=f"--key-header X-API-Key --key {SECRET_VALUE}",
        )

        deploy(project)

        assert engine.created[0]["secrets"] == {"SERVER_KEY": SECRET_VALUE}
        assert "Found 1 tool(s)" in capsys.readouterr().out

    def test_the_key_is_sent_after_its_scheme(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SERVER_KEY", SECRET_VALUE)
        project = stand_in(
            tmp_path,
            arcade_toml=(
                'secrets = ["SERVER_KEY"]\n[deploy.api_key]\nenv = "SERVER_KEY"\n'
                'header = "Authorization"\nscheme = "Bearer"\n'
            ),
            server_args="--key-header Authorization --key-env SERVER_KEY --key-scheme Bearer",
        )

        deploy(project)

        assert engine.created

    def test_an_undeclared_key_is_generated_and_put_in_the_servers_environment(
        self, tmp_path: Path, engine: FakeEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = stand_in(
            tmp_path,
            arcade_toml='[deploy.api_key]\nenv = "SERVER_KEY"\nheader = "X-API-Key"\n',
            server_args="--key-header X-API-Key --key-env SERVER_KEY",
        )

        deploy(project)

        assert engine.created[0]["secrets"] == {}
        assert "Found 1 tool(s)" in capsys.readouterr().out

    @pytest.mark.parametrize("oauth", ["--bearer user-token", "--bearer-for-tools user-token"])
    def test_a_server_that_takes_the_key_and_wants_a_user_token_still_deploys(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        capsys: pytest.CaptureFixture[str],
        oauth: str,
    ) -> None:
        project = stand_in(
            tmp_path,
            arcade_toml='[deploy.api_key]\nenv = "SERVER_KEY"\nheader = "X-API-Key"\n',
            server_args=f"--key-header X-API-Key --key-env SERVER_KEY {oauth}",
        )

        deploy(project)

        assert engine.created
        assert "needs a token to list its tools" in capsys.readouterr().out

    def test_a_bearer_challenge_to_a_key_in_authorization_is_a_refused_key(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(
            tmp_path,
            arcade_toml=(
                '[deploy.api_key]\nenv = "SERVER_KEY"\n'
                'header = "Authorization"\nscheme = "Bearer"\n'
            ),
            server_args="--bearer the-fixed-key",
        )

        with pytest.raises(DeployRefusedError, match=r"declare SERVER_KEY under `secrets`"):
            deploy(project)
        assert not engine.uploaded

    def test_a_refused_declared_key_is_refused_before_upload(
        self, tmp_path: Path, engine: FakeEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SERVER_KEY", "not-the-key")
        project = stand_in(
            tmp_path,
            arcade_toml=(
                'secrets = ["SERVER_KEY"]\n'
                '[deploy.api_key]\nenv = "SERVER_KEY"\nheader = "X-API-Key"\n'
            ),
            server_args="--key-header X-API-Key --key the-fixed-key",
        )

        with pytest.raises(DeployRefusedError, match=r"refused the API key from the secret SERVER_KEY"):
            deploy(project)
        assert not engine.uploaded

    def test_a_fixed_key_the_server_wont_take_suggests_declaring_it(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(
            tmp_path,
            arcade_toml='[deploy.api_key]\nenv = "SERVER_KEY"\nheader = "X-API-Key"\n',
            server_args="--key-header X-API-Key --key the-fixed-key",
        )

        with pytest.raises(DeployRefusedError, match=r"declare SERVER_KEY under `secrets`"):
            deploy(project)
        assert not engine.uploaded


class TestRefusedBeforeUpload:
    def refused(self, project: Path, engine: FakeEngine, match: str, **kwargs: Any) -> None:
        with pytest.raises(ValueError, match=match):
            deploy(project, **kwargs)
        assert not engine.uploaded

    def test_a_declared_secret_with_no_value(self, tmp_path: Path, engine: FakeEngine) -> None:
        project = stand_in(tmp_path, arcade_toml='secrets = ["SNOWFLAKE_TOKEN"]\n')

        self.refused(project, engine, r"\bSNOWFLAKE_TOKEN\b")

    @pytest.mark.parametrize("name", ["PATH", "ARCADE_RUNNER_REGION", "FASTMCP_HOME"])
    def test_a_reserved_environment_name(
        self, tmp_path: Path, engine: FakeEngine, name: str
    ) -> None:
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
        (project / "auth.py").write_text(
            "from fastmcp.server.auth.providers.github import GitHubProvider\n"
        )

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

    def test_an_arcade_server_missing_its_arcade_mcp_dependency(
        self, tmp_path: Path, engine: FakeEngine
    ) -> None:
        project = stand_in(tmp_path, server_args="--worker-health")

        self.refused(project, engine, r"/worker/health.*arcade-mcp")

    def test_no_supported_framework(self, tmp_path: Path, engine: FakeEngine) -> None:
        project = tmp_path / "plain"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "plain-tools"\nversion = "0.1.0"\n'
        )
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

class TestToolkitName:
    @pytest.mark.parametrize(
        ("server_name", "toolkit"),
        [
            ("Expense Tools", "ExpenseTools"),
            ("echo-server", "Echo"),
            ("fake-mcp", "Fake"),
            ("my_MCP_Server", "My"),
            ("snowflake analytics 2", "SnowflakeAnalytics2"),
            ("mcp-server", "Tools"),
            ("", "Tools"),
        ],
    )
    def test_mirrors_the_engine(self, server_name: str, toolkit: str) -> None:
        assert engine_toolkit_name(server_name) == toolkit

    def test_the_deploy_prints_it(
        self, tmp_path: Path, engine: FakeEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        deploy(stand_in(tmp_path))

        assert "listed under the toolkit Fake" in capsys.readouterr().out


class TestFrameworkWarning:
    @pytest.mark.parametrize(
        "versions",
        [
            {"fastmcp": "4.1.3", "mcp": "1.30.0"},
            {"fastmcp": "2.14.0", "mcp": "1.9.0"},
            {"fastmcp": None, "mcp": "2.0.1"},
        ],
    )
    def test_tested_versions_have_no_warning(self, versions: dict[str, str | None]) -> None:
        assert framework_warning(versions) is None

    @pytest.mark.parametrize(
        ("versions", "named"),
        [
            ({"fastmcp": "5.0.0", "mcp": "1.30.0"}, "fastmcp 5.0.0"),
            ({"fastmcp": None, "mcp": "3.0.0"}, "the MCP SDK (mcp) 3.0.0"),
        ],
    )
    def test_a_newer_major_is_warned(self, versions: dict[str, str | None], named: str) -> None:
        warning = framework_warning(versions)
        assert warning is not None
        assert named in warning

    def test_neither_framework_is_warned(self) -> None:
        warning = framework_warning({"fastmcp": None, "mcp": None})
        assert warning is not None
        assert "Neither fastmcp nor the MCP SDK" in warning

    def test_the_warning_never_refuses_the_deploy(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            deploy_mcp, "_framework_versions", lambda python: {"fastmcp": "5.0.0", "mcp": None}
        )

        deploy(stand_in(tmp_path))

        assert engine.created
        assert "hasn't been tested with fastmcp 5.0.0" in capsys.readouterr().out

    def test_an_interpreter_that_cant_be_asked_gives_no_warning(
        self,
        tmp_path: Path,
        engine: FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(deploy_mcp, "_framework_versions", lambda python: {})

        deploy(stand_in(tmp_path))

        assert "Neither fastmcp" not in capsys.readouterr().out

    def test_versions_are_read_with_the_projects_interpreter(self) -> None:
        versions = deploy_mcp._framework_versions(Path(sys.executable))

        assert versions["mcp"]  # the test environment has the MCP SDK
        assert set(versions) == {"fastmcp", "mcp"}

def test_refusals_are_value_errors() -> None:
    assert issubclass(DeployRefusedError, ValueError)
