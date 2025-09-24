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
