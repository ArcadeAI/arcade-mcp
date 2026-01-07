"""Tests for MCPApp initialization and basic functionality."""

import subprocess
import sys
from typing import Annotated
from unittest.mock import Mock, patch

import pytest
from arcade_core.catalog import MaterializedTool
from arcade_mcp_server import tool
from arcade_mcp_server.mcp_app import MCPApp
from arcade_mcp_server.server import MCPServer


class TestMCPApp:
    """Test MCPApp class."""

    @pytest.fixture
    def mcp_app(self) -> MCPApp:
        """Create an MCP app."""
        app = MCPApp(name="TestMCPApp", version="1.0.0")

        # Add a sample tool so the app doesn't exit when run() is called
        @app.tool
        def sample_tool(message: Annotated[str, "A message"]) -> str:
            """A sample tool for testing."""
            return f"Response: {message}"

        return app

    def test_mcp_app_initialization(self):
        """Test MCPApp initialization creates proper settings."""
        app = MCPApp(
            name="TestApp",
            version="1.5.0",
            title="Test Title",
            instructions="Test instructions",
        )

        assert app.name == "TestApp"
        assert app.version == "1.5.0"
        assert app.title == "Test Title"
        assert app.instructions == "Test instructions"

        assert app._mcp_settings is not None
        assert app._mcp_settings.server.name == "TestApp"
        assert app._mcp_settings.server.version == "1.5.0"
        assert app._mcp_settings.server.title == "Test Title"
        assert app._mcp_settings.server.instructions == "Test instructions"

    def test_mcp_app_initialization_defaults(self):
        """Test MCPApp initialization with default values."""
        app = MCPApp()

        assert app.name == "ArcadeMCP"
        assert app.version == "0.1.0"

        assert app._mcp_settings.server.name == "ArcadeMCP"
        assert app._mcp_settings.server.version == "0.1.0"

    def test_mcp_app_initialization_partial_values(self):
        """Test MCPApp initialization with partial values."""
        app = MCPApp(name="PartialApp")

        assert app.name == "PartialApp"
        assert app.version == "0.1.0"  # Default value

        assert app._mcp_settings.server.name == "PartialApp"
        assert app._mcp_settings.server.version == "0.1.0"

    def test_add_tool(self, mcp_app: MCPApp):
        """Test adding a tool to the MCP app."""

        def undecorated_sample_tool(
            text: Annotated[str, "Input text"],
        ) -> Annotated[str, "Echoed text"]:
            """Echo input text back to the caller."""
            return f"Echo: {text}"

        @tool
        def decorated_sample_tool(
            text: Annotated[str, "Input text"],
        ) -> Annotated[str, "Echoed text"]:
            """Echo input text back to the caller."""
            return f"Echo: {text}"

        previous_tools = len(mcp_app._catalog)

        undecorated_tool = mcp_app.add_tool(undecorated_sample_tool)
        decorated_tool = mcp_app.add_tool(decorated_sample_tool)

        assert len(mcp_app._catalog) == previous_tools + 2

        # Verify tool has the @tool decorator applied
        assert hasattr(undecorated_tool, "__tool_name__")
        assert undecorated_tool.__tool_name__ == "UndecoratedSampleTool"
        assert hasattr(decorated_tool, "__tool_name__")
        assert decorated_tool.__tool_name__ == "DecoratedSampleTool"

    def test_tool(self, mcp_app: MCPApp):
        """Test the MCPApp tool decorator."""

        initial_tool_count = len(mcp_app._catalog)

        # Test decorator without parameters
        @mcp_app.tool
        def simple_tool(message: Annotated[str, "A message"]) -> str:
            """A simple tool."""
            return f"Response: {message}"

        # Test decorator with parameters
        @mcp_app.tool(name="SimpleTool2")
        def simple_tool2(message: Annotated[str, "A message"]) -> str:
            """A simple tool."""
            return f"Response: {message}"

        # Verify both tools were added
        assert len(mcp_app._catalog) == initial_tool_count + 2

        # Verify decorator attributes
        assert hasattr(simple_tool, "__tool_name__")
        assert simple_tool.__tool_name__ == "SimpleTool"
        assert hasattr(simple_tool2, "__tool_name__")
        assert simple_tool2.__tool_name__ == "SimpleTool2"
        # Verify tools can still be called
        assert simple_tool("test") == "Response: test"
        assert simple_tool2("test") == "Response: test"

    @pytest.mark.asyncio
    async def test_tools_api(
        self, mcp_app: MCPApp, mcp_server: MCPServer, materialized_tool: MaterializedTool
    ):
        """Test the tools API."""
        # Test that tools API requires server binding
        with pytest.raises(Exception):  # noqa: B017
            await mcp_app.tools.add(materialized_tool)

        # Bind server to app (instead of calling mcp_app.run())
        mcp_app.server = mcp_server

        # Test removing a tool at runtime
        removed_tool = await mcp_app.tools.remove(materialized_tool.definition.fully_qualified_name)
        assert (
            removed_tool.definition.fully_qualified_name
            == materialized_tool.definition.fully_qualified_name
        )

        num_tools_before_add = len(await mcp_app.tools.list())

        # Test adding a tool at runtime
        await mcp_app.tools.add(materialized_tool)

        # Test listing tools at runtime
        tools = await mcp_app.tools.list()
        assert len(tools) == num_tools_before_add + 1

        # Test updating a tool at runtime
        await mcp_app.tools.update(materialized_tool)

    @pytest.mark.asyncio
    async def test_prompts_api(self, mcp_app: MCPApp, mcp_server):
        """Test the prompts API."""
        from arcade_mcp_server.types import Prompt, PromptArgument, PromptMessage

        # Test that prompts API requires server binding
        sample_prompt = Prompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[PromptArgument(name="input", description="Test input", required=True)],
        )

        with pytest.raises(Exception) as exc_info:
            await mcp_app.prompts.add(sample_prompt)
        assert "No server bound to app" in str(exc_info.value)

        # Bind server to app
        mcp_app.server = mcp_server

        # Create a prompt handler
        async def test_handler(args: dict[str, str]) -> list[PromptMessage]:
            return [
                PromptMessage(
                    role="user",
                    content={"type": "text", "text": f"Hello {args.get('input', 'world')}"},
                )
            ]

        # Test adding a prompt at runtime
        await mcp_app.prompts.add(sample_prompt, test_handler)

        # Test listing prompts at runtime
        prompts = await mcp_app.prompts.list()
        assert len(prompts) == 1
        assert any(p.name == "test_prompt" for p in prompts)

        # Test removing a prompt at runtime
        removed_prompt = await mcp_app.prompts.remove("test_prompt")
        assert removed_prompt.name == "test_prompt"

    @pytest.mark.asyncio
    async def test_resources_api(self, mcp_app: MCPApp, mcp_server):
        """Test the resources API."""
        from arcade_mcp_server.types import Resource

        # Test that resources API requires server binding
        sample_resource = Resource(
            uri="file:///test.txt",
            name="test.txt",
            description="A test text file",
            mimeType="text/plain",
        )

        with pytest.raises(Exception) as exc_info:
            await mcp_app.resources.add(sample_resource)
        assert "No server bound to app" in str(exc_info.value)

        # Bind server to app
        mcp_app.server = mcp_server

        # Create a resource handler
        def test_handler(uri: str):
            return {"content": f"Content for {uri}", "mimeType": "text/plain"}

        # Test adding a resource at runtime
        await mcp_app.resources.add(sample_resource, test_handler)

        # Test listing resources at runtime
        resources = await mcp_app.resources.list()
        assert len(resources) >= 1
        assert any(r.uri == "file:///test.txt" for r in resources)

        # Test removing a resource at runtime
        removed_resource = await mcp_app.resources.remove("file:///test.txt")
        assert removed_resource.uri == "file:///test.txt"

    def test_get_configuration_overrides(self, monkeypatch):
        """Test configuration overrides from environment variables."""
        # Ensure environment variables are clear at the start
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT", raising=False)
        monkeypatch.delenv("ARCADE_SERVER_HOST", raising=False)
        monkeypatch.delenv("ARCADE_SERVER_PORT", raising=False)
        monkeypatch.delenv("ARCADE_SERVER_RELOAD", raising=False)

        # Test default values (no environment variables)
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert host == "127.0.0.1"
        assert port == 8000
        assert transport == "http"
        assert not reload

        # Test transport override
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "stdio")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert transport == "stdio"
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

        # Test host override (only works with HTTP transport)
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "http")
        monkeypatch.setenv("ARCADE_SERVER_HOST", "192.168.1.1")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert host == "192.168.1.1"
        assert transport == "http"
        monkeypatch.delenv("ARCADE_SERVER_HOST")
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

        # Test port override (only works with HTTP transport)
        monkeypatch.setenv("ARCADE_SERVER_PORT", "9000")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert port == 9000
        monkeypatch.delenv("ARCADE_SERVER_PORT")

        # Test invalid port value
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "http")
        monkeypatch.setenv("ARCADE_SERVER_PORT", "invalid_port")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert port == 8000  # Should keep the default value
        monkeypatch.delenv("ARCADE_SERVER_PORT")
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

        # Test valid reload value
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "http")
        monkeypatch.setenv("ARCADE_SERVER_RELOAD", "1")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert reload
        monkeypatch.delenv("ARCADE_SERVER_RELOAD")
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

        # Test invalid reload value
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "http")
        monkeypatch.setenv("ARCADE_SERVER_RELOAD", "invalid_reload")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        assert not reload  # Should keep the default value
        monkeypatch.delenv("ARCADE_SERVER_RELOAD")
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

        # Test host/port/reload with stdio transport
        monkeypatch.setenv("ARCADE_SERVER_TRANSPORT", "stdio")
        monkeypatch.setenv("ARCADE_SERVER_HOST", "192.168.1.1")
        monkeypatch.setenv("ARCADE_SERVER_PORT", "9000")
        monkeypatch.setenv("ARCADE_SERVER_RELOAD", "true")
        host, port, transport, reload = MCPApp._get_configuration_overrides(
            "127.0.0.1", 8000, "http", False
        )
        # For stdio, host, port, and reload are still returned but not used by the server
        assert host == "127.0.0.1"  # Host should remain unchanged for stdio transport
        assert port == 8000  # Port should remain unchanged for stdio transport
        assert transport == "stdio"
        assert not reload
        monkeypatch.delenv("ARCADE_SERVER_RELOAD")
        monkeypatch.delenv("ARCADE_SERVER_HOST")
        monkeypatch.delenv("ARCADE_SERVER_PORT")
        monkeypatch.delenv("ARCADE_SERVER_TRANSPORT")

    def test_create_and_run_server(self, mcp_app: MCPApp):
        """Test _create_and_run_server method with mocked dependencies."""
        with (
            patch("arcade_mcp_server.mcp_app.create_arcade_mcp") as mock_create,
            patch("arcade_mcp_server.mcp_app.serve_with_force_quit") as mock_serve,
        ):
            mock_fastapi_app = Mock()
            mock_create.return_value = mock_fastapi_app

            # Test with INFO log level
            mcp_app.log_level = "INFO"
            mcp_app._create_and_run_server("127.0.0.1", 8000)

            mock_create.assert_called_once_with(
                catalog=mcp_app._catalog,
                mcp_settings=mcp_app._mcp_settings,
                debug=False,
                resource_server_validator=mcp_app.resource_server_validator,
            )
            mock_serve.assert_called_once_with(
                app=mock_fastapi_app,
                host="127.0.0.1",
                port=8000,
                log_level="info",
            )

        # Test with DEBUG log level
        with (
            patch("arcade_mcp_server.mcp_app.create_arcade_mcp") as mock_create,
            patch("arcade_mcp_server.mcp_app.serve_with_force_quit") as mock_serve,
        ):
            mock_fastapi_app = Mock()
            mock_create.return_value = mock_fastapi_app

            mcp_app.log_level = "DEBUG"
            mcp_app._create_and_run_server("192.168.1.1", 9000)

            mock_create.assert_called_once_with(
                catalog=mcp_app._catalog,
                mcp_settings=mcp_app._mcp_settings,
                debug=True,
                resource_server_validator=mcp_app.resource_server_validator,
            )
            mock_serve.assert_called_once_with(
                app=mock_fastapi_app,
                host="192.168.1.1",
                port=9000,
                log_level="debug",
            )

    def test_run_with_reload_spawns_child_process(self, mcp_app: MCPApp):
        """Test _run_with_reload spawns child process with correct environment."""
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()

        with (
            patch("arcade_mcp_server.mcp_app.subprocess.Popen") as mock_popen,
            patch("arcade_mcp_server.mcp_app.watch") as mock_watch,
        ):
            mock_popen.return_value = mock_process
            # Return empty iterator to exit immediately
            mock_watch.return_value = iter([])

            mcp_app._run_with_reload("127.0.0.1", 8000)

            # Verify Popen was called with correct args
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            assert call_args[0][0] == [sys.executable, *sys.argv]
            assert call_args[1]["env"]["ARCADE_MCP_CHILD_PROCESS"] == "1"

    def test_run_with_reload_restarts_on_changes(self, mcp_app: MCPApp):
        """Test _run_with_reload restarts server when file changes detected."""
        mock_process1 = Mock()
        mock_process2 = Mock()

        with (
            patch("arcade_mcp_server.mcp_app.subprocess.Popen") as mock_popen,
            patch("arcade_mcp_server.mcp_app.watch") as mock_watch,
        ):
            mock_popen.side_effect = [mock_process1, mock_process2]
            # Yield one set of changes then stop
            mock_watch.return_value = iter([{("change", "test.py")}])

            mcp_app._run_with_reload("127.0.0.1", 8000)

            # Verify both processes were created
            assert mock_popen.call_count == 2

            # Verify first process was terminated
            mock_process1.terminate.assert_called_once()
            mock_process1.wait.assert_called()

    def test_run_with_reload_graceful_shutdown(self, mcp_app: MCPApp):
        """Test _run_with_reload gracefully shuts down process."""
        mock_process = Mock()
        mock_process.wait = Mock()  # Succeeds without timeout

        with (
            patch("arcade_mcp_server.mcp_app.subprocess.Popen") as mock_popen,
            patch("arcade_mcp_server.mcp_app.watch") as mock_watch,
        ):
            mock_popen.return_value = mock_process
            mock_watch.return_value = iter([{("change", "test.py")}])

            mcp_app._run_with_reload("127.0.0.1", 8000)

            # Verify graceful shutdown
            mock_process.terminate.assert_called()
            mock_process.wait.assert_called()
            mock_process.kill.assert_not_called()

    def test_run_with_reload_force_kill_on_timeout(self, mcp_app: MCPApp):
        """Test _run_with_reload force kills process on timeout."""
        mock_process = Mock()
        # First wait times out, second succeeds
        mock_process.wait = Mock(side_effect=[subprocess.TimeoutExpired("cmd", 5), None])

        with (
            patch("arcade_mcp_server.mcp_app.subprocess.Popen") as mock_popen,
            patch("arcade_mcp_server.mcp_app.watch") as mock_watch,
        ):
            mock_popen.return_value = mock_process
            mock_watch.return_value = iter([{("change", "test.py")}])

            mcp_app._run_with_reload("127.0.0.1", 8000)

            # Verify terminate -> wait -> kill -> wait sequence
            mock_process.terminate.assert_called()
            assert mock_process.wait.call_count == 2
            mock_process.kill.assert_called_once()

    def test_run_with_reload_keyboard_interrupt(self, mcp_app: MCPApp):
        """Test _run_with_reload handles KeyboardInterrupt gracefully."""
        mock_process = Mock()

        with (
            patch("arcade_mcp_server.mcp_app.subprocess.Popen") as mock_popen,
            patch("arcade_mcp_server.mcp_app.watch") as mock_watch,
        ):
            mock_popen.return_value = mock_process
            mock_watch.side_effect = KeyboardInterrupt()

            # Should not raise exception
            mcp_app._run_with_reload("127.0.0.1", 8000)

            # Verify process was shut down
            mock_process.terminate.assert_called_once()

    def test_run_routes_to_reload_method(self, mcp_app: MCPApp):
        """Test run() routes to _run_with_reload when reload=True."""
        with (
            patch.object(mcp_app, "_run_with_reload") as mock_reload,
            patch.object(mcp_app, "_create_and_run_server") as mock_direct,
        ):
            mcp_app.run(reload=True, transport="http", host="127.0.0.1", port=8000)

            mock_reload.assert_called_once_with("127.0.0.1", 8000)
            mock_direct.assert_not_called()

    def test_run_routes_to_direct_method(self, mcp_app: MCPApp):
        """Test run() routes to _create_and_run_server when reload=False."""
        with (
            patch.object(mcp_app, "_run_with_reload") as mock_reload,
            patch.object(mcp_app, "_create_and_run_server") as mock_direct,
        ):
            mcp_app.run(reload=False, transport="http", host="127.0.0.1", port=8000)

            mock_direct.assert_called_once_with("127.0.0.1", 8000)
            mock_reload.assert_not_called()

    def test_run_child_process_disables_reload(self, mcp_app: MCPApp, monkeypatch):
        """Test run() disables reload when ARCADE_MCP_CHILD_PROCESS is set."""
        monkeypatch.setenv("ARCADE_MCP_CHILD_PROCESS", "1")

        with (
            patch.object(mcp_app, "_run_with_reload") as mock_reload,
            patch.object(mcp_app, "_create_and_run_server") as mock_direct,
        ):
            mcp_app.run(reload=True, transport="http", host="127.0.0.1", port=8000)

            # Should route to direct method even though reload=True
            mock_direct.assert_called_once_with("127.0.0.1", 8000)
            mock_reload.assert_not_called()

    def test_run_stdio_unaffected_by_reload(self, mcp_app: MCPApp):
        """Test run() with stdio transport is unaffected by reload flag."""
        with patch("arcade_mcp_server.__main__.run_stdio_server") as mock_stdio:
            # Test with reload=True
            mcp_app.run(reload=True, transport="stdio")
            mock_stdio.assert_called_once()

            mock_stdio.reset_mock()

            # Test with reload=False
            mcp_app.run(reload=False, transport="stdio")
            mock_stdio.assert_called_once()

    @pytest.mark.parametrize(
        "name,expected_result",
        [
            # Valid names
            ("ValidName", "ValidName"),
            ("valid_name", "valid_name"),
            ("ValidName123", "ValidName123"),
            ("valid_name_123", "valid_name_123"),
            ("a", "a"),
            ("A", "A"),
            ("1", "1"),
            ("name1", "name1"),
            ("Name1", "Name1"),
            ("validName", "validName"),
            ("Valid_Name", "Valid_Name"),
            ("valid_name_test", "valid_name_test"),
            ("Test123Name", "Test123Name"),
            ("a1b2c3", "a1b2c3"),
            ("A1B2C3", "A1B2C3"),
        ],
    )
    def test_validate_name_valid_names(self, name: str, expected_result: str):
        """Test _validate_name with valid names."""
        app = MCPApp()
        result = app._validate_name(name)
        assert result == expected_result

    @pytest.mark.parametrize(
        "name,expected_error",
        [
            # Empty name
            ("", ValueError),
            # Non-string types
            (None, TypeError),
            (123, TypeError),
            ([], TypeError),
            ({}, TypeError),
            # Names starting with underscore
            ("_invalid", ValueError),
            ("_name", ValueError),
            ("_123", ValueError),
            ("_", ValueError),
            # Names with consecutive underscores
            ("name__test", ValueError),
            ("test__name", ValueError),
            ("__name", ValueError),
            ("name__", ValueError),
            ("__", ValueError),
            # Names ending with underscore
            ("name_", ValueError),
            ("test_", ValueError),
            ("_", ValueError),
            # Names with invalid characters
            ("name-test", ValueError),
            ("name.test", ValueError),
            ("name test", ValueError),
            ("name@test", ValueError),
            ("name#test", ValueError),
            ("name$test", ValueError),
            ("name%test", ValueError),
            ("name^test", ValueError),
            ("name&test", ValueError),
            ("name*test", ValueError),
            ("name+test", ValueError),
            ("name=test", ValueError),
            ("name[test", ValueError),
            ("name]test", ValueError),
            ("name{test", ValueError),
            ("name}test", ValueError),
            ("name|test", ValueError),
            ("name\\test", ValueError),
            ("name:test", ValueError),
            ("name;test", ValueError),
            ("name'test", ValueError),
            ('name"test', ValueError),
            ("name<test", ValueError),
            ("name>test", ValueError),
            ("name,test", ValueError),
            ("name.test", ValueError),
            ("name?test", ValueError),
            ("name/test", ValueError),
            ("name!test", ValueError),
            ("name~test", ValueError),
            ("name`test", ValueError),
            # Names with spaces
            ("name test", ValueError),
            (" name", ValueError),
            ("name ", ValueError),
            (" name ", ValueError),
            # Names with special unicode characters
            ("nameñ", ValueError),
            ("nameé", ValueError),
            ("name中", ValueError),
            ("name🚀", ValueError),
        ],
    )
    def test_validate_name_invalid_names(self, name, expected_error):
        """Test _validate_name with invalid names."""
        app = MCPApp()
        with pytest.raises(expected_error):
            app._validate_name(name)
