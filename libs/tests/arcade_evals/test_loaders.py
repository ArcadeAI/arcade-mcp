"""Tests for MCP server loaders (official MCP SDK wrappers)."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the loaders module directly by file path to avoid arcade_core dependency
_LOADERS_PATH = Path(__file__).parent.parent.parent / "arcade-evals" / "arcade_evals" / "loaders.py"
spec = importlib.util.spec_from_file_location("loaders", _LOADERS_PATH)
loaders = importlib.util.module_from_spec(spec)
sys.modules["arcade_evals.loaders"] = loaders
spec.loader.exec_module(loaders)


class TestLoadFromStdio:
    """Tests for load_from_stdio function."""

    @pytest.mark.asyncio
    async def test_empty_command_returns_empty_list(self):
        """Empty command should return empty list without importing MCP."""
        result = await loaders.load_from_stdio_async([])
        assert result == []

    @pytest.mark.asyncio
    async def test_env_vars_are_merged_into_stdio_server_parameters(self):
        """Env vars should be merged with current env and passed to StdioServerParameters."""
        mock_tool = MagicMock()
        mock_tool.name = "t"
        mock_tool.description = "d"
        mock_tool.inputSchema = {"type": "object", "properties": {}}

        mock_list_result = MagicMock()
        mock_list_result.tools = [mock_tool]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_list_result)

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_stdio_client = MagicMock()
        mock_stdio_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_stdio_client.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_stdio_params_cls = MagicMock()

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                mock_stdio_params_cls,
                mock_stdio_client,
                mock_sse_client,
            )

            await loaders.load_from_stdio_async(["echo"], env={"TEST_VAR": "test_value"})

            # Ensure env merged and passed into server params
            _, call_kwargs = mock_stdio_params_cls.call_args
            assert "env" in call_kwargs
            assert call_kwargs["env"]["TEST_VAR"] == "test_value"


class TestLoadFromHttp:
    """Tests for load_from_http function."""

    @pytest.mark.asyncio
    async def test_url_gets_mcp_appended(self):
        """URL without /mcp should get it appended before calling sse_client."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_from_http_async("http://localhost:8000")
            called_url = mock_sse_client.call_args[0][0]
            assert called_url.endswith("/mcp")

    @pytest.mark.asyncio
    async def test_url_with_mcp_not_duplicated(self):
        """URL with /mcp should not get duplicated."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_from_http_async("http://localhost:8000/mcp")
            called_url = mock_sse_client.call_args[0][0]
            assert "/mcp/mcp" not in called_url

    @pytest.mark.asyncio
    async def test_headers_are_passed(self):
        """Custom headers should be passed to sse_client."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_from_http_async(
                "http://localhost:8000",
                headers={"Authorization": "Bearer token123"},
            )
            _, call_kwargs = mock_sse_client.call_args
            assert call_kwargs["headers"]["Authorization"] == "Bearer token123"

    @pytest.mark.asyncio
    async def test_returns_tools_from_response(self):
        """Should convert SDK Tool objects into dicts."""
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool1"
        mock_tool1.description = "Test tool 1"
        mock_tool1.inputSchema = {"type": "object", "properties": {}}

        mock_tool2 = MagicMock()
        mock_tool2.name = "tool2"
        mock_tool2.description = None
        mock_tool2.inputSchema = {"type": "object", "properties": {}}

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool1, mock_tool2]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            result = await loaders.load_from_http_async("http://localhost:8000")
            assert result == [
                {
                    "name": "tool1",
                    "description": "Test tool 1",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "tool2",
                    "description": "",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ]


class TestLoadArcadeMcpGateway:
    """Tests for load_arcade_mcp_gateway function."""

    @pytest.mark.asyncio
    async def test_builds_correct_url_and_headers_with_slug(self):
        """Should build correct Arcade MCP URL and pass auth headers."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_arcade_mcp_gateway_async(
                "my-gateway",
                arcade_api_key="key",
                arcade_user_id="user",
            )

            called_url = mock_sse_client.call_args[0][0]
            called_headers = mock_sse_client.call_args[1]["headers"]
            assert called_url == "https://api.arcade.dev/mcp/my-gateway"
            assert called_headers["Authorization"] == "key"
            assert called_headers["arcade-user-id"] == "user"

    @pytest.mark.asyncio
    async def test_builds_correct_url_without_slug(self):
        """Should build correct Arcade MCP URL without gateway slug."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_arcade_mcp_gateway_async(arcade_api_key="key")

            called_url = mock_sse_client.call_args[0][0]
            assert called_url == "https://api.arcade.dev/mcp"

    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        """Should use custom base URL when provided."""
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_client_session_cls = MagicMock()
        mock_client_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sse_client = MagicMock()
        mock_sse_client.return_value.__aenter__ = AsyncMock(return_value=("read", "write"))
        mock_sse_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(loaders, "_require_mcp") as mock_require:
            mock_require.return_value = (
                mock_client_session_cls,
                MagicMock(),
                MagicMock(),
                mock_sse_client,
            )

            await loaders.load_arcade_mcp_gateway_async(
                "my-gateway",
                base_url="https://staging.arcade.dev",
            )

            called_url = mock_sse_client.call_args[0][0]
            assert called_url == "https://staging.arcade.dev/mcp/my-gateway"


class TestLoadStdioArcade:
    """Tests for load_stdio_arcade function."""

    @pytest.mark.asyncio
    async def test_passes_env_vars_to_stdio(self):
        """Should pass Arcade env vars to stdio loader."""
        with patch.object(loaders, "load_from_stdio_async", new_callable=AsyncMock) as mock_stdio:
            mock_stdio.return_value = []

            await loaders.load_stdio_arcade_async(
                ["python", "server.py"],
                arcade_api_key="test_key",
                arcade_user_id="test_user",
            )

            call_kwargs = mock_stdio.call_args[1]
            assert call_kwargs["env"]["ARCADE_API_KEY"] == "test_key"
            assert call_kwargs["env"]["ARCADE_USER_ID"] == "test_user"

    @pytest.mark.asyncio
    async def test_includes_tool_secrets(self):
        """Should include tool secrets in environment."""
        with patch.object(loaders, "load_from_stdio_async", new_callable=AsyncMock) as mock_stdio:
            mock_stdio.return_value = []

            await loaders.load_stdio_arcade_async(
                ["python", "server.py"],
                tool_secrets={"GITHUB_TOKEN": "gh_token", "SLACK_TOKEN": "slack_token"},
            )

            call_kwargs = mock_stdio.call_args[1]
            assert call_kwargs["env"]["GITHUB_TOKEN"] == "gh_token"
            assert call_kwargs["env"]["SLACK_TOKEN"] == "slack_token"


class TestLazyImport:
    """Tests for lazy MCP import behavior."""

    def test_require_mcp_error_message(self):
        """Should raise helpful ImportError when MCP SDK is not installed."""
        # If MCP is installed in the environment, this test isn't meaningful.
        # Force an import failure by masking the module.
        with patch.dict(sys.modules, {"mcp": None}):
            with pytest.raises(ImportError) as exc:
                loaders._require_mcp()
            assert "pip install" in str(exc.value)


class TestEnsureMcpPath:
    """Tests for _ensure_mcp_path utility function."""

    def test_appends_mcp_to_bare_url(self):
        """Should append /mcp to URL without path."""
        result = loaders._ensure_mcp_path("http://localhost:8000")
        assert result == "http://localhost:8000/mcp"

    def test_appends_mcp_to_url_with_path(self):
        """Should append /mcp to URL with existing path."""
        result = loaders._ensure_mcp_path("http://localhost:8000/api")
        assert result == "http://localhost:8000/api/mcp"

    def test_does_not_duplicate_mcp(self):
        """Should not duplicate /mcp if already present."""
        result = loaders._ensure_mcp_path("http://localhost:8000/mcp")
        assert result == "http://localhost:8000/mcp"

    def test_handles_mcp_in_path(self):
        """Should not add /mcp if 'mcp' is anywhere in path segments."""
        result = loaders._ensure_mcp_path("http://localhost:8000/mcp/my-slug")
        assert result == "http://localhost:8000/mcp/my-slug"

    def test_preserves_query_string(self):
        """Should preserve query string in URL."""
        result = loaders._ensure_mcp_path("http://localhost:8000?foo=bar")
        assert result == "http://localhost:8000/mcp?foo=bar"

    def test_preserves_fragment(self):
        """Should preserve fragment in URL."""
        result = loaders._ensure_mcp_path("http://localhost:8000#section")
        assert result == "http://localhost:8000/mcp#section"


class TestBuildArcadeMcpUrl:
    """Tests for _build_arcade_mcp_url utility function."""

    def test_builds_url_with_slug(self):
        """Should build correct URL with gateway slug."""
        result = loaders._build_arcade_mcp_url("my-gateway", "https://api.arcade.dev")
        assert result == "https://api.arcade.dev/mcp/my-gateway"

    def test_builds_url_without_slug(self):
        """Should build correct URL without gateway slug."""
        result = loaders._build_arcade_mcp_url(None, "https://api.arcade.dev")
        assert result == "https://api.arcade.dev/mcp"

    def test_strips_trailing_slash(self):
        """Should strip trailing slash from base URL."""
        result = loaders._build_arcade_mcp_url("my-gateway", "https://api.arcade.dev/")
        assert result == "https://api.arcade.dev/mcp/my-gateway"


class TestToolToDict:
    """Tests for _tool_to_dict utility function."""

    def test_converts_tool_to_dict(self):
        """Should convert MCP Tool object to dictionary."""
        mock_tool = MagicMock()
        mock_tool.name = "my_tool"
        mock_tool.description = "A description"
        mock_tool.inputSchema = {"type": "object", "properties": {"x": {"type": "string"}}}

        result = loaders._tool_to_dict(mock_tool)
        assert result == {
            "name": "my_tool",
            "description": "A description",
            "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
        }

    def test_handles_none_description(self):
        """Should handle None description."""
        mock_tool = MagicMock()
        mock_tool.name = "my_tool"
        mock_tool.description = None
        mock_tool.inputSchema = {}

        result = loaders._tool_to_dict(mock_tool)
        assert result["description"] == ""
