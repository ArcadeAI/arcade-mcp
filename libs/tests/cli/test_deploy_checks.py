from pathlib import Path

import pytest
from arcade_cli.deploy_checks import detect_unsupported_input

ARCADE_SERVER = """
from arcade_mcp_server import MCPApp

app = MCPApp(name="expense", version="1.0.0")

if __name__ == "__main__":
    app.run()
"""

FASTMCP_SERVER = """
from mcp.server.fastmcp import FastMCP

app = FastMCP("expense")

if __name__ == "__main__":
    app.run()
"""


def _pyproject(project_dir: Path) -> None:
    (project_dir / "pyproject.toml").write_text("[project]\nname = 'x'\nversion = '1.0.0'\n")


class TestSupportedInput:
    def test_arcade_mcp_server_is_accepted(self, tmp_path: Path):
        _pyproject(tmp_path)
        (tmp_path / "server.py").write_text(ARCADE_SERVER)

        assert detect_unsupported_input(tmp_path, "server.py") is None

    def test_missing_entrypoint_is_not_flagged_here(self, tmp_path: Path):
        _pyproject(tmp_path)

        assert detect_unsupported_input(tmp_path, "server.py") is None


class TestUnsupportedFramework:
    def test_fastmcp_server_is_rejected(self, tmp_path: Path):
        _pyproject(tmp_path)
        (tmp_path / "server.py").write_text(FASTMCP_SERVER)

        message = detect_unsupported_input(tmp_path, "server.py")

        assert message is not None
        assert "FastMCP" in message
        assert "Arcade MCP" in message

    def test_arcade_marker_in_comment_or_string_does_not_hide_fastmcp(self, tmp_path: Path):
        _pyproject(tmp_path)
        (tmp_path / "server.py").write_text(
            "# migrated from arcade_mcp\nNOTE = 'MCPApp'\n" + FASTMCP_SERVER
        )

        message = detect_unsupported_input(tmp_path, "server.py")

        assert message is not None
        assert "FastMCP" in message

    def test_typescript_sdk_server_is_rejected(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"dependencies": {"@modelcontextprotocol/sdk": "1"}}')
        (tmp_path / "index.ts").write_text("// server")

        message = detect_unsupported_input(tmp_path, "server.py")

        assert message is not None
        assert "TypeScript" in message


class TestInfrastructureOnly:
    def test_dockerfile_only_is_rejected(self, tmp_path: Path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")

        message = detect_unsupported_input(tmp_path, "server.py")

        assert message is not None
        assert "Dockerfile" in message

    def test_kubernetes_manifest_only_is_rejected(self, tmp_path: Path):
        (tmp_path / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: x\n"
        )

        message = detect_unsupported_input(tmp_path, "server.py")

        assert message is not None
        assert "Kubernetes" in message

    def test_plain_missing_pyproject_defers(self, tmp_path: Path):
        (tmp_path / "notes.txt").write_text("hello")

        assert detect_unsupported_input(tmp_path, "server.py") is None
