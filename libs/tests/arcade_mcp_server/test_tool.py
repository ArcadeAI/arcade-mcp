"""Tests for Tool Manager implementation."""

import pytest
import pytest_asyncio
from arcade_mcp_server.exceptions import NotFoundError
from arcade_mcp_server.managers.tool import ToolManager
from arcade_mcp_server.types import MCPTool


class TestToolManager:
    """Test ToolManager class."""

    @pytest_asyncio.fixture
    async def tool_manager(self, materialized_tool):
        """Create a tool manager instance with one tool added."""
        manager = ToolManager()
        await manager.add_tool(materialized_tool)
        return manager

    def test_manager_initialization(self):
        """Test tool manager initialization."""
        manager = ToolManager()
        assert isinstance(manager, ToolManager)

    @pytest.mark.asyncio
    async def test_list_tools(self, tool_manager):
        """Test listing tools."""
        tools = await tool_manager.list_tools()

        assert isinstance(tools, list)
        assert all(isinstance(t, MCPTool) for t in tools)

        if tools:
            tool = tools[0]
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")

    @pytest.mark.asyncio
    async def test_get_tool(self, tool_manager, materialized_tool):
        """Test getting a specific tool."""
        # Get tool by name
        tool_name = materialized_tool.definition.fully_qualified_name
        tool = await tool_manager.get_tool(tool_name)
        assert tool.definition.fully_qualified_name == tool_name

        # Try to get non-existent tool
        with pytest.raises(NotFoundError):
            await tool_manager.get_tool("NonExistent_tool")

    @pytest.mark.asyncio
    async def test_remove_tool(self, tool_manager, materialized_tool):
        """Test removing tools."""
        name = materialized_tool.definition.fully_qualified_name
        _ = await tool_manager.get_tool(name)

        removed = await tool_manager.remove_tool(name)
        assert removed.definition.fully_qualified_name == name

        with pytest.raises(NotFoundError):
            await tool_manager.get_tool(name)

    @pytest.mark.asyncio
    async def test_remove_nonexistent_tool(self, tool_manager):
        """Test removing non-existent tool."""
        with pytest.raises(NotFoundError):
            await tool_manager.remove_tool("NonExistent_tool")

    @pytest.mark.asyncio
    async def test_tool_conversion(self, tool_manager):
        """Test conversion of MaterializedTool to MCP Tool format."""
        tools = await tool_manager.list_tools()
        if not tools:
            pytest.skip("No tools in manager to validate conversion")
        tool = tools[0]

        # Check required fields
        assert isinstance(tool.name, str)
        assert isinstance(tool.description, str) or tool.description is None
        assert "inputSchema" in tool.model_dump()

        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "properties" in schema
