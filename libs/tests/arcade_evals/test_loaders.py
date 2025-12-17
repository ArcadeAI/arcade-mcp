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
        """Should build correct Arcade MCP URL and pass auth headers (official backend)."""
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


class TestInternalStdioLoader:
    """Tests for _internal_load_from_stdio_sync function."""

    def test_empty_command_returns_empty_list(self):
        """Empty command should return empty list."""
        result = loaders._internal_load_from_stdio_sync([])
        assert result == []

    def test_successful_tools_list(self):
        """Should return tools from subprocess JSON-RPC response."""
        mock_tools = [
            {"name": "TestTool", "description": "A test tool", "inputSchema": {"type": "object"}}
        ]
        mock_response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": mock_tools}}

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # First readline is init response, second is tools/list response
        mock_process.stdout.readline.side_effect = [
            '{"jsonrpc": "2.0", "id": 1, "result": {}}',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "TestTool", "description": "A test tool", "inputSchema": {"type": "object"}}]}}',
        ]

        with patch("subprocess.Popen", return_value=mock_process):
            result = loaders._internal_load_from_stdio_sync(["python", "server.py"])

        assert result == mock_tools

    def test_env_vars_are_passed_to_subprocess(self):
        """Environment variables should be passed to subprocess."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.side_effect = [
            '{"jsonrpc": "2.0", "id": 1, "result": {}}',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}',
        ]

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            loaders._internal_load_from_stdio_sync(
                ["python", "server.py"], env={"MY_VAR": "my_value"}
            )

            _, call_kwargs = mock_popen.call_args
            assert "MY_VAR" in call_kwargs["env"]
            assert call_kwargs["env"]["MY_VAR"] == "my_value"

    def test_json_decode_error_returns_empty_list(self):
        """Should return empty list and log warning on JSON decode error."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.side_effect = [
            '{"jsonrpc": "2.0", "id": 1, "result": {}}',
            "invalid json response",
        ]

        with patch("subprocess.Popen", return_value=mock_process):
            result = loaders._internal_load_from_stdio_sync(["python", "server.py"])

        assert result == []

    def test_missing_stdin_stdout_returns_empty_list(self):
        """Should return empty list when stdin/stdout not available."""
        mock_process = MagicMock()
        mock_process.stdin = None
        mock_process.stdout = None

        with patch("subprocess.Popen", return_value=mock_process):
            result = loaders._internal_load_from_stdio_sync(["python", "server.py"])

        assert result == []

    def test_process_is_terminated(self):
        """Subprocess should be terminated in finally block."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.side_effect = [
            '{"jsonrpc": "2.0", "id": 1, "result": {}}',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}',
        ]

        with patch("subprocess.Popen", return_value=mock_process):
            loaders._internal_load_from_stdio_sync(["python", "server.py"])

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()


class TestInternalHttpLoader:
    """Tests for _internal_load_from_http_sync function."""

    def test_successful_json_response(self):
        """Should return tools from HTTP JSON response."""
        mock_tools = [
            {"name": "HttpTool", "description": "HTTP tool", "inputSchema": {"type": "object"}}
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": mock_tools},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == mock_tools

    def test_url_gets_mcp_path_appended(self):
        """URL should get /mcp appended."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response) as mock_post:
            loaders._internal_load_from_http_sync("http://localhost:8000")

            called_url = mock_post.call_args[0][0]
            assert called_url == "http://localhost:8000/mcp"

    def test_custom_headers_passed(self):
        """Custom headers should be passed to httpx."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response) as mock_post:
            loaders._internal_load_from_http_sync(
                "http://localhost:8000", headers={"Authorization": "Bearer token"}
            )

            _, call_kwargs = mock_post.call_args
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer token"

    def test_missing_result_tools_returns_empty(self):
        """Should return empty list when response missing result.tools."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == []

    def test_connect_error_returns_empty(self):
        """Should return empty list on connection error."""
        import httpx

        with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
            result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == []

    def test_timeout_returns_empty(self):
        """Should return empty list on timeout."""
        import httpx

        with patch("httpx.post", side_effect=httpx.TimeoutException("Timeout")):
            result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == []

    def test_http_406_triggers_sse_fallback(self):
        """Should fallback to SSE mode on 406 status."""
        import httpx

        error_response = MagicMock()
        error_response.status_code = 406
        error_response.text = "text/event-stream required"
        error_response.reason_phrase = "Not Acceptable"

        # Create mock for SSE stream that returns tools
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            'data: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "SSETool"}]}}'
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=None)

        with patch(
            "httpx.post",
            side_effect=httpx.HTTPStatusError("406", request=MagicMock(), response=error_response),
        ):
            with patch("httpx.stream", return_value=mock_stream_response):
                result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == [{"name": "SSETool"}]

    def test_http_401_triggers_session_handshake(self):
        """Should trigger session handshake on 401 status."""
        import httpx

        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = "Unauthorized"
        error_response.reason_phrase = "Unauthorized"

        with patch(
            "httpx.post",
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=error_response),
        ):
            with patch.object(
                loaders, "_internal_load_with_session_sync", return_value=[{"name": "SessionTool"}]
            ) as mock_session:
                result = loaders._internal_load_from_http_sync("http://localhost:8000")

        assert result == [{"name": "SessionTool"}]
        mock_session.assert_called_once()


class TestInternalHttpSseMode:
    """Tests for SSE streaming mode in _internal_load_from_http_sync."""

    def test_sse_mode_parses_data_lines(self):
        """Should parse tools from SSE data lines."""
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            'data: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "Tool1"}, {"name": "Tool2"}]}}'
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=None)

        with patch("httpx.stream", return_value=mock_stream_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000", use_sse=True)

        assert result == [{"name": "Tool1"}, {"name": "Tool2"}]

    def test_sse_mode_ignores_non_data_lines(self):
        """Should ignore lines not starting with 'data: '."""
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            "event: message",
            "id: 1",
            'data: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "Tool1"}]}}',
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=None)

        with patch("httpx.stream", return_value=mock_stream_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000", use_sse=True)

        assert result == [{"name": "Tool1"}]

    def test_sse_mode_empty_stream_returns_empty(self):
        """Should return empty list when SSE stream has no tools."""
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            'data: {"jsonrpc": "2.0", "id": 1, "result": {}}',
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=None)

        with patch("httpx.stream", return_value=mock_stream_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000", use_sse=True)

        assert result == []

    def test_sse_mode_invalid_json_skipped(self):
        """Should skip invalid JSON in SSE stream and continue."""
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            "data: invalid json",
            'data: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "ValidTool"}]}}',
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=None)

        with patch("httpx.stream", return_value=mock_stream_response):
            result = loaders._internal_load_from_http_sync("http://localhost:8000", use_sse=True)

        assert result == [{"name": "ValidTool"}]


class TestInternalSessionLoader:
    """Tests for _internal_load_with_session_sync function."""

    def test_successful_session_handshake(self):
        """Should establish session and return tools."""
        mock_init_response = MagicMock()
        mock_init_response.headers = {"Mcp-Session-Id": "session-123"}
        mock_init_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}
        mock_init_response.raise_for_status = MagicMock()

        mock_tools_response = MagicMock()
        mock_tools_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "SessionTool"}]},
        }
        mock_tools_response.raise_for_status = MagicMock()

        with patch("httpx.post", side_effect=[mock_init_response, mock_tools_response]):
            result = loaders._internal_load_with_session_sync(
                url="http://localhost:8000/mcp",
                headers={},
            )

        assert result == [{"name": "SessionTool"}]

    def test_session_headers_passed_to_tools_request(self):
        """Session ID should be passed to internal_load_from_http_sync."""
        mock_init_response = MagicMock()
        mock_init_response.headers = {
            "mcp-session-id": "server-session-456"
        }  # lowercase as returned by server
        mock_init_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}
        mock_init_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_init_response):
            with patch.object(
                loaders, "_internal_load_from_http_sync", return_value=[]
            ) as mock_http_load:
                loaders._internal_load_with_session_sync(
                    url="http://localhost:8000/mcp",
                    headers={"Authorization": "Bearer token"},
                )

                # Verify session ID from server response is used
                call_kwargs = mock_http_load.call_args[1]
                assert call_kwargs["headers"]["Mcp-Session-Id"] == "server-session-456"
                assert call_kwargs["headers"]["Authorization"] == "Bearer token"


class TestBackendSwitching:
    """Tests for set_mcp_loader_backend function."""

    def test_set_backend_to_internal(self):
        """Should be able to switch to internal backend."""
        loaders.set_mcp_loader_backend("internal")
        # Verify internal loader is active by checking its type
        assert isinstance(loaders._MCP_TOOL_LOADER, loaders.InternalMCPToolLoader)

    def test_set_backend_to_official(self):
        """Should be able to switch to official backend."""
        loaders.set_mcp_loader_backend("official")
        assert isinstance(loaders._MCP_TOOL_LOADER, loaders.OfficialMCPToolLoader)
        # Reset to internal
        loaders.set_mcp_loader_backend("internal")

    def test_invalid_backend_raises_error(self):
        """Should raise error for invalid backend name."""
        with pytest.raises(ValueError, match="Unknown"):
            loaders.set_mcp_loader_backend("invalid_backend")  # type: ignore


class TestInternalLoaderClass:
    """Tests for InternalMCPToolLoader class."""

    def test_loader_is_instantiable(self):
        """Should be able to instantiate InternalMCPToolLoader."""
        loader = loaders.InternalMCPToolLoader()
        assert loader is not None

    @pytest.mark.asyncio
    async def test_load_from_stdio_calls_internal_function(self):
        """Should delegate to _internal_load_from_stdio_sync."""
        with patch.object(
            loaders, "_internal_load_from_stdio_sync", return_value=[{"name": "Tool"}]
        ) as mock_sync:
            loader = loaders.InternalMCPToolLoader()
            result = await loader.load_from_stdio(["python", "server.py"], timeout=5)

            mock_sync.assert_called_once()
            assert result == [{"name": "Tool"}]

    @pytest.mark.asyncio
    async def test_load_from_http_calls_internal_function(self):
        """Should delegate to _internal_load_from_http_sync."""
        with patch.object(
            loaders, "_internal_load_from_http_sync", return_value=[{"name": "HttpTool"}]
        ) as mock_sync:
            loader = loaders.InternalMCPToolLoader()
            result = await loader.load_from_http("http://localhost:8000", timeout=10)

            mock_sync.assert_called_once()
            assert result == [{"name": "HttpTool"}]
