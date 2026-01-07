"""Tests for async MCP convenience methods in EvalSuite."""

from unittest.mock import patch

import pytest
from arcade_evals import EvalSuite

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestAddMcpServer:
    """Tests for add_mcp_server async convenience method."""

    @pytest.mark.asyncio
    async def test_add_mcp_server_loads_and_registers_tools(self) -> None:
        """Test that add_mcp_server loads tools and adds them to registry."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [
            {"name": "tool1", "description": "Test tool 1", "inputSchema": {}},
            {"name": "tool2", "description": "Test tool 2", "inputSchema": {}},
        ]

        with patch("arcade_evals._evalsuite._convenience.load_mcp_remote_async") as mock_load:
            mock_load.return_value = mock_tools

            result = await suite.add_mcp_server(
                "http://localhost:8000",
                headers={"Authorization": "Bearer token"},
                timeout=15,
                use_sse=True,
            )

            # Verify loader was called with correct args
            mock_load.assert_called_once_with(
                "http://localhost:8000",
                timeout=15,
                headers={"Authorization": "Bearer token"},
                use_sse=True,
            )

            # Verify tools were registered
            tools = suite._internal_registry.list_tools_for_model("openai")
            assert len(tools) == 2

            # Verify returns self for chaining
            assert result is suite

    @pytest.mark.asyncio
    async def test_add_mcp_server_with_track(self) -> None:
        """Test add_mcp_server with track parameter."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [{"name": "tool1", "description": "Test", "inputSchema": {}}]

        with patch("arcade_evals._evalsuite._convenience.load_mcp_remote_async") as mock_load:
            mock_load.return_value = mock_tools

            await suite.add_mcp_server("http://localhost:8000", track="github")

            # Verify track was created
            assert suite._track_manager.has_track("github")

            # Verify tool is in track registry
            track_registry = suite._track_manager.get_registry("github")
            assert track_registry is not None
            track_tools = track_registry.list_tools_for_model("openai")
            assert len(track_tools) == 1
            assert track_tools[0]["function"]["name"] == "tool1"

    @pytest.mark.asyncio
    async def test_add_mcp_server_warns_on_empty_tools(self) -> None:
        """Test that add_mcp_server warns when no tools are loaded."""
        suite = EvalSuite(name="test", system_message="test")

        with patch("arcade_evals._evalsuite._convenience.load_mcp_remote_async") as mock_load:
            mock_load.return_value = []  # Empty tools

            with pytest.warns(UserWarning, match="No tools loaded from"):
                await suite.add_mcp_server("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_add_mcp_server_handles_loader_exception(self) -> None:
        """Test that add_mcp_server propagates loader exceptions."""
        suite = EvalSuite(name="test", system_message="test")

        with patch("arcade_evals._evalsuite._convenience.load_mcp_remote_async") as mock_load:
            mock_load.side_effect = TimeoutError("Connection timeout")

            with pytest.raises(TimeoutError, match="Connection timeout"):
                await suite.add_mcp_server("http://localhost:8000")


class TestAddMcpStdioServer:
    """Tests for add_mcp_stdio_server async convenience method."""

    @pytest.mark.asyncio
    async def test_add_mcp_stdio_server_loads_and_registers_tools(self) -> None:
        """Test that add_mcp_stdio_server loads tools and adds them to registry."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [
            {"name": "linear_search", "description": "Search", "inputSchema": {}},
            {"name": "linear_create", "description": "Create", "inputSchema": {}},
        ]

        with patch("arcade_evals._evalsuite._convenience.load_from_stdio_async") as mock_load:
            mock_load.return_value = mock_tools

            command = ["python", "-m", "arcade_mcp_server", "stdio"]
            env = {"ARCADE_API_KEY": "test_key"}

            result = await suite.add_mcp_stdio_server(command, env=env, timeout=20)

            # Verify loader was called with correct args
            mock_load.assert_called_once_with(command, timeout=20, env=env)

            # Verify tools were registered
            tools = suite._internal_registry.list_tools_for_model("openai")
            assert len(tools) == 2

            # Verify returns self for chaining
            assert result is suite

    @pytest.mark.asyncio
    async def test_add_mcp_stdio_server_with_track(self) -> None:
        """Test add_mcp_stdio_server with track parameter."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [{"name": "tool1", "description": "Test", "inputSchema": {}}]

        with patch("arcade_evals._evalsuite._convenience.load_from_stdio_async") as mock_load:
            mock_load.return_value = mock_tools

            await suite.add_mcp_stdio_server(["python", "server.py"], track="linear")

            # Verify track was created
            assert suite._track_manager.has_track("linear")

    @pytest.mark.asyncio
    async def test_add_mcp_stdio_server_warns_on_empty_tools(self) -> None:
        """Test that add_mcp_stdio_server warns when no tools are loaded."""
        suite = EvalSuite(name="test", system_message="test")

        with patch("arcade_evals._evalsuite._convenience.load_from_stdio_async") as mock_load:
            mock_load.return_value = []

            with pytest.warns(UserWarning, match="No tools loaded from stdio"):
                await suite.add_mcp_stdio_server(["python", "server.py"])

    @pytest.mark.asyncio
    async def test_add_mcp_stdio_server_handles_loader_exception(self) -> None:
        """Test that add_mcp_stdio_server propagates loader exceptions."""
        suite = EvalSuite(name="test", system_message="test")

        with patch("arcade_evals._evalsuite._convenience.load_from_stdio_async") as mock_load:
            mock_load.side_effect = TimeoutError("Stdio timeout")

            with pytest.raises(TimeoutError, match="Stdio timeout"):
                await suite.add_mcp_stdio_server(["python", "server.py"])


class TestAddArcadeGateway:
    """Tests for add_arcade_gateway async convenience method."""

    @pytest.mark.asyncio
    async def test_add_arcade_gateway_loads_and_registers_tools(self) -> None:
        """Test that add_arcade_gateway loads tools and adds them to registry."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [
            {"name": "Github_CreateIssue", "description": "Create issue", "inputSchema": {}},
            {"name": "Github_GetIssue", "description": "Get issue", "inputSchema": {}},
        ]

        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async"
        ) as mock_load:
            mock_load.return_value = mock_tools

            result = await suite.add_arcade_gateway(
                "my-gateway",
                arcade_api_key="test_key",
                arcade_user_id="test@example.com",
                base_url="https://api.arcade.dev",
                timeout=10,
            )

            # Verify loader was called with correct args
            mock_load.assert_called_once_with(
                "my-gateway",
                arcade_api_key="test_key",
                arcade_user_id="test@example.com",
                base_url="https://api.arcade.dev",
                timeout=10,
            )

            # Verify tools were registered
            tools = suite._internal_registry.list_tools_for_model("openai")
            assert len(tools) == 2

            # Verify returns self for chaining
            assert result is suite

    @pytest.mark.asyncio
    async def test_add_arcade_gateway_with_track(self) -> None:
        """Test add_arcade_gateway with track parameter."""
        suite = EvalSuite(name="test", system_message="test")

        mock_tools = [{"name": "tool1", "description": "Test", "inputSchema": {}}]

        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async"
        ) as mock_load:
            mock_load.return_value = mock_tools

            await suite.add_arcade_gateway("my-gateway", track="arcade")

            # Verify track was created
            assert suite._track_manager.has_track("arcade")

    @pytest.mark.asyncio
    async def test_add_arcade_gateway_warns_on_empty_tools(self) -> None:
        """Test that add_arcade_gateway warns when no tools are loaded."""
        suite = EvalSuite(name="test", system_message="test")

        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async"
        ) as mock_load:
            mock_load.return_value = []

            with pytest.warns(UserWarning, match="No tools loaded from Arcade gateway"):
                await suite.add_arcade_gateway("my-gateway")

    @pytest.mark.asyncio
    async def test_add_arcade_gateway_handles_loader_exception(self) -> None:
        """Test that add_arcade_gateway propagates loader exceptions."""
        suite = EvalSuite(name="test", system_message="test")

        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async"
        ) as mock_load:
            mock_load.side_effect = Exception("Gateway connection failed")

            with pytest.raises(Exception, match="Gateway connection failed"):
                await suite.add_arcade_gateway("my-gateway")


class TestAsyncConvenienceMethodChaining:
    """Tests for method chaining with async MCP methods."""

    @pytest.mark.asyncio
    async def test_chaining_multiple_mcp_sources(self) -> None:
        """Test that async methods can be chained together."""
        suite = EvalSuite(name="test", system_message="test")

        mock_http_tools = [{"name": "http_tool", "description": "HTTP", "inputSchema": {}}]
        mock_stdio_tools = [{"name": "stdio_tool", "description": "Stdio", "inputSchema": {}}]
        mock_gateway_tools = [
            {"name": "gateway_tool", "description": "Gateway", "inputSchema": {}}
        ]

        with (
            patch(
                "arcade_evals._evalsuite._convenience.load_mcp_remote_async"
            ) as mock_http,
            patch(
                "arcade_evals._evalsuite._convenience.load_from_stdio_async"
            ) as mock_stdio,
            patch(
                "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async"
            ) as mock_gateway,
        ):
            mock_http.return_value = mock_http_tools
            mock_stdio.return_value = mock_stdio_tools
            mock_gateway.return_value = mock_gateway_tools

            # Chain all three methods
            result = await suite.add_mcp_server("http://localhost:8000")
            result = await result.add_mcp_stdio_server(["python", "server.py"])
            result = await result.add_arcade_gateway("my-gateway")

            # Verify all tools were registered
            tools = suite._internal_registry.list_tools_for_model("openai")
            assert len(tools) == 3
            tool_names = [t["function"]["name"] for t in tools]
            assert "http_tool" in tool_names
            assert "stdio_tool" in tool_names
            assert "gateway_tool" in tool_names

            # Verify final result is still the suite
            assert result is suite
