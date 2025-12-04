"""Tests for MCP server loaders."""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the loaders module directly by file path to avoid arcade_core dependency
_LOADERS_PATH = Path(__file__).parent.parent.parent / "arcade-evals" / "arcade_evals" / "loaders.py"
spec = importlib.util.spec_from_file_location("loaders", _LOADERS_PATH)
loaders = importlib.util.module_from_spec(spec)
sys.modules["arcade_evals.loaders"] = loaders
spec.loader.exec_module(loaders)


class TestLoadFromStdio:
    """Tests for load_from_stdio function."""

    def test_empty_command_returns_empty_list(self):
        """Empty command should return empty list."""
        result = loaders.load_from_stdio([])
        assert result == []

    def test_invalid_command_returns_empty_list(self):
        """Invalid command should return empty list."""
        result = loaders.load_from_stdio(["nonexistent_command_xyz"])
        assert result == []

    def test_env_vars_are_merged(self):
        """Environment variables should be merged with current env."""
        with patch.object(loaders.subprocess, "Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stdout.readline.return_value = '{"jsonrpc":"2.0","id":1,"result":{}}'
            mock_popen.return_value = mock_process

            loaders.load_from_stdio(["echo"], env={"TEST_VAR": "test_value"})

            call_kwargs = mock_popen.call_args[1]
            assert "env" in call_kwargs
            assert call_kwargs["env"]["TEST_VAR"] == "test_value"


class TestLoadFromHttp:
    """Tests for load_from_http function."""

    def test_url_gets_mcp_appended(self):
        """URL without /mcp should get it appended."""
        import httpx

        with patch.object(httpx, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": {"tools": []}}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            loaders.load_from_http("http://localhost:8000")

            call_args = mock_post.call_args
            assert "/mcp" in call_args[0][0]

    def test_url_with_mcp_not_duplicated(self):
        """URL with /mcp should not get it duplicated."""
        import httpx

        with patch.object(httpx, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": {"tools": []}}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            loaders.load_from_http("http://localhost:8000/mcp")

            call_args = mock_post.call_args
            assert "/mcp/mcp" not in call_args[0][0]

    def test_headers_are_passed(self):
        """Custom headers should be passed to request."""
        import httpx

        with patch.object(httpx, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": {"tools": []}}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            loaders.load_from_http(
                "http://localhost:8000",
                headers={"Authorization": "Bearer token123"},
            )

            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer token123"

    def test_returns_tools_from_response(self):
        """Should return tools from valid response."""
        import httpx

        mock_tools = [
            {"name": "tool1", "description": "Test tool 1"},
            {"name": "tool2", "description": "Test tool 2"},
        ]

        with patch.object(httpx, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": {"tools": mock_tools}}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = loaders.load_from_http("http://localhost:8000")

            assert result == mock_tools

    def test_timeout_returns_empty_list(self):
        """Timeout should return empty list."""
        import httpx

        with patch.object(httpx, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            result = loaders.load_from_http("http://localhost:8000")

            assert result == []


class TestLoadArcadeCloud:
    """Tests for load_arcade_cloud function."""

    def test_uses_env_vars_when_no_params(self):
        """Should use environment variables when params not provided."""
        with patch.dict(
            os.environ,
            {"ARCADE_API_KEY": "env_key", "ARCADE_USER_ID": "env_user"},
        ):
            with patch.object(loaders, "_load_with_session") as mock_load:
                mock_load.return_value = []

                loaders.load_arcade_cloud(gateway_slug="test-gateway")

                call_kwargs = mock_load.call_args[1]
                assert call_kwargs["headers"]["Authorization"] == "env_key"
                assert call_kwargs["headers"]["arcade-user-id"] == "env_user"

    def test_params_override_env_vars(self):
        """Parameters should override environment variables."""
        with patch.dict(
            os.environ,
            {"ARCADE_API_KEY": "env_key", "ARCADE_USER_ID": "env_user"},
        ):
            with patch.object(loaders, "_load_with_session") as mock_load:
                mock_load.return_value = []

                loaders.load_arcade_cloud(
                    gateway_slug="test-gateway",
                    arcade_api_key="param_key",
                    arcade_user_id="param_user",
                )

                call_kwargs = mock_load.call_args[1]
                assert call_kwargs["headers"]["Authorization"] == "param_key"
                assert call_kwargs["headers"]["arcade-user-id"] == "param_user"

    def test_builds_correct_url(self):
        """Should build correct Arcade Cloud URL."""
        with patch.object(loaders, "_load_with_session") as mock_load:
            mock_load.return_value = []

            loaders.load_arcade_cloud(gateway_slug="my-gateway", arcade_api_key="key")

            call_kwargs = mock_load.call_args[1]
            assert call_kwargs["url"] == "https://api.arcade.dev/mcp/my-gateway"


class TestLoadStdioArcade:
    """Tests for load_stdio_arcade function."""

    def test_passes_env_vars_to_stdio(self):
        """Should pass Arcade env vars to stdio loader."""
        with patch.object(loaders, "load_from_stdio") as mock_stdio:
            mock_stdio.return_value = []

            loaders.load_stdio_arcade(
                ["python", "server.py"],
                arcade_api_key="test_key",
                arcade_user_id="test_user",
            )

            call_kwargs = mock_stdio.call_args[1]
            assert call_kwargs["env"]["ARCADE_API_KEY"] == "test_key"
            assert call_kwargs["env"]["ARCADE_USER_ID"] == "test_user"

    def test_includes_tool_secrets(self):
        """Should include tool secrets in environment."""
        with patch.object(loaders, "load_from_stdio") as mock_stdio:
            mock_stdio.return_value = []

            loaders.load_stdio_arcade(
                ["python", "server.py"],
                tool_secrets={"GITHUB_TOKEN": "gh_token", "SLACK_TOKEN": "slack_token"},
            )

            call_kwargs = mock_stdio.call_args[1]
            assert call_kwargs["env"]["GITHUB_TOKEN"] == "gh_token"
            assert call_kwargs["env"]["SLACK_TOKEN"] == "slack_token"


class TestBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    def test_load_from_arcade_server_alias(self):
        """load_from_arcade_server should be alias for load_stdio_arcade."""
        assert loaders.load_from_arcade_server is loaders.load_stdio_arcade

    def test_load_from_arcade_http_alias(self):
        """load_from_arcade_http should be alias for load_arcade_cloud."""
        assert loaders.load_from_arcade_http is loaders.load_arcade_cloud
