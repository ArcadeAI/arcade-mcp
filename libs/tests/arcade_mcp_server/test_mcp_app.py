"""Tests for MCPApp initialization and basic functionality."""

from typing import Annotated

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
        return MCPApp(name="TestMCPApp", version="1.0.0")

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
        assert len(mcp_app._catalog) == 2

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
