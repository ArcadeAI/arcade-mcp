"""Tests for EvalSuite convenience methods (TICKET-003)."""

from typing import Annotated, Any
from unittest.mock import AsyncMock, patch

import pytest
from arcade_core import ToolCatalog
from arcade_evals import EvalSuite, ExpectedToolCall, MCPToolDefinition
from arcade_tdk import tool

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


def sample_tool_def(name: str = "test_tool") -> dict[str, Any]:
    return {
        "name": name,
        "description": "A test tool",
        "inputSchema": {
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        },
    }


@tool
def py_add(a: Annotated[int, "Left operand"], b: Annotated[int, "Right operand"] = 0) -> int:
    """Add two integers."""
    return a + b


class TestAddToolDefinitions:
    def test_add_single_tool(self) -> None:
        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([sample_tool_def()])
        assert suite.get_tool_count() == 1
        assert "test_tool" in suite.list_tool_names()

    def test_method_chaining(self) -> None:
        suite = EvalSuite(name="Test", system_message="Test")
        assert suite.add_tool_definitions([sample_tool_def()]) is suite

    def test_add_empty_list(self) -> None:
        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([])
        assert suite.get_tool_count() == 0

    def test_invalid_tool_raises(self) -> None:
        suite = EvalSuite(name="Test", system_message="Test")
        with pytest.raises(ValueError, match="name"):
            suite.add_tool_definitions([{"description": "No name"}])


class TestAddMcpServer:
    @pytest.mark.asyncio
    async def test_calls_loader_with_correct_params(self) -> None:
        with patch(
            "arcade_evals._evalsuite._convenience.load_mcp_remote_async", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = [sample_tool_def()]
            suite = EvalSuite(name="Test", system_message="Test")
            await suite.add_mcp_server("http://localhost:8000", headers={"Auth": "t"}, timeout=30)
            mock_load.assert_called_once_with(
                "http://localhost:8000",
                timeout=30,
                headers={"Auth": "t"},
                use_sse=False,
            )

    @pytest.mark.asyncio
    async def test_empty_response_warns(self) -> None:
        with patch(
            "arcade_evals._evalsuite._convenience.load_mcp_remote_async", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = []
            suite = EvalSuite(name="Test", system_message="Test")
            with pytest.warns(UserWarning, match="No tools loaded"):
                await suite.add_mcp_server("http://localhost:8000")


class TestAddMcpStdioServer:
    @pytest.mark.asyncio
    async def test_calls_loader_with_correct_params(self) -> None:
        with patch(
            "arcade_evals._evalsuite._convenience.load_from_stdio_async", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = [sample_tool_def()]
            suite = EvalSuite(name="Test", system_message="Test")
            await suite.add_mcp_stdio_server(["python", "server.py"], env={"K": "V"}, timeout=20)
            mock_load.assert_called_once_with(
                ["python", "server.py"],
                timeout=20,
                env={"K": "V"},
            )


class TestAddArcadeGateway:
    @pytest.mark.asyncio
    async def test_calls_loader_with_correct_params(self) -> None:
        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = [sample_tool_def()]
            suite = EvalSuite(name="Test", system_message="Test")
            await suite.add_arcade_gateway(
                "my-gateway",
                arcade_api_key="k",
                arcade_user_id="u",
                timeout=15,
            )

            # base_url defaults to None, loader handles the default
            mock_load.assert_called_once_with(
                "my-gateway",
                arcade_api_key="k",
                arcade_user_id="u",
                base_url=None,
                timeout=15,
            )


class TestAddToolCatalog:
    def test_add_tool_catalog_registers_python_tool_and_allows_callable_in_case(self) -> None:
        catalog = ToolCatalog()
        catalog.add_tool(py_add, "sample_toolkit")

        suite = EvalSuite(name="Test", system_message="Test").add_tool_catalog(catalog)
        names = suite.list_tool_names()
        assert suite.get_tool_count() == 1
        assert len(names) == 1

        suite.add_case(
            name="Case",
            user_message="Add 1 and 2",
            expected_tool_calls=[ExpectedToolCall(func=py_add, args={"a": 1, "b": 2})],
        )
        assert suite.cases[0].expected_tool_calls[0].name in names


class TestMCPToolDefinition:
    """Tests for MCPToolDefinition TypedDict."""

    def test_typedict_is_importable(self) -> None:
        """MCPToolDefinition should be importable from arcade_evals."""
        from arcade_evals import MCPToolDefinition

        assert MCPToolDefinition is not None

    def test_typedict_has_expected_keys(self) -> None:
        """MCPToolDefinition should have name, description, and inputSchema keys."""
        annotations = MCPToolDefinition.__annotations__
        # Check all expected keys are present (from both base and child TypedDict)
        all_keys = set(annotations.keys())
        # The parent class _MCPToolDefinitionRequired adds 'name'
        assert "description" in all_keys
        assert "inputSchema" in all_keys

    def test_tool_with_only_required_fields(self) -> None:
        """Tool definition with only 'name' should work (other fields default)."""
        tool_def: MCPToolDefinition = {"name": "minimal_tool"}

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([tool_def])

        assert suite.get_tool_count() == 1
        assert "minimal_tool" in suite.list_tool_names()

    def test_tool_with_all_fields(self) -> None:
        """Tool definition with all fields should work."""
        tool_def: MCPToolDefinition = {
            "name": "full_tool",
            "description": "A fully specified tool",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        }

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([tool_def])

        assert suite.get_tool_count() == 1
        assert "full_tool" in suite.list_tool_names()

    def test_multiple_tools_with_typed_list(self) -> None:
        """A list[MCPToolDefinition] should work with add_tool_definitions."""
        tools: list[MCPToolDefinition] = [
            {"name": "tool_a", "description": "Tool A"},
            {"name": "tool_b"},
            {"name": "tool_c", "inputSchema": {"type": "object", "properties": {}}},
        ]

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions(tools)

        assert suite.get_tool_count() == 3
        assert set(suite.list_tool_names()) == {"tool_a", "tool_b", "tool_c"}

    def test_duplicate_tool_name_raises_error(self) -> None:
        """Registering a tool with a duplicate name should raise ValueError."""
        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "my_tool"}])

        with pytest.raises(ValueError, match="already registered"):
            suite.add_tool_definitions([{"name": "my_tool"}])


class TestAddToolDefinitionsEdgeCases:
    """Additional edge case tests for add_tool_definitions."""

    def test_invalid_type_raises_typeerror(self) -> None:
        """Non-dict tool definitions should raise TypeError."""
        suite = EvalSuite(name="Test", system_message="Test")
        with pytest.raises(TypeError, match="must be dictionaries"):
            suite.add_tool_definitions(["not_a_dict"])  # type: ignore

    def test_does_not_mutate_input(self) -> None:
        """add_tool_definitions should not mutate the input dicts."""
        original_tool = {"name": "my_tool"}
        original_copy = dict(original_tool)

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([original_tool])

        # Original dict should be unchanged (no defaults added)
        assert original_tool == original_copy
        assert "description" not in original_tool
        assert "inputSchema" not in original_tool


class TestAddMcpStdioServerWarnings:
    """Tests for add_mcp_stdio_server warning paths."""

    @pytest.mark.asyncio
    async def test_empty_response_warns(self) -> None:
        """Empty response from stdio server should warn."""
        with patch(
            "arcade_evals._evalsuite._convenience.load_from_stdio_async", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = []
            suite = EvalSuite(name="Test", system_message="Test")
            with pytest.warns(UserWarning, match="No tools loaded"):
                await suite.add_mcp_stdio_server(["python", "server.py"])


class TestAddArcadeGatewayWarnings:
    """Tests for add_arcade_gateway warning paths."""

    @pytest.mark.asyncio
    async def test_empty_response_warns(self) -> None:
        """Empty response from arcade gateway should warn."""
        with patch(
            "arcade_evals._evalsuite._convenience.load_arcade_mcp_gateway_async",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = []
            suite = EvalSuite(name="Test", system_message="Test")
            with pytest.warns(UserWarning, match="No tools loaded"):
                await suite.add_arcade_gateway("my-gateway")
