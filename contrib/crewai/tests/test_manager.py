from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from arcadepy.types import ToolDefinition
from crewai_arcade.manager import TOOL_NAME_SEPARATOR, ArcadeToolManager

# --- Custom executor ---


def custom_executor(manager: ArcadeToolManager, name: str, **tool_input: dict[str, Any]) -> Any:
    """Custom executor for testing purposes."""
    return "Tool executed"


# --- Fixtures ---


@pytest.fixture
def mock_client():
    """Create a fake Arcade client fixture."""
    return MagicMock()


@pytest.fixture
def manager_with_default_executor(mock_client):
    """Return an ArcadeToolManager with a test default_user_id and fake client."""
    return ArcadeToolManager(default_user_id="test_user", client=mock_client)


@pytest.fixture
def manager_with_custom_executor(mock_client):
    """Return an ArcadeToolManager with a test default_user_id and fake client using a custom executor."""
    return ArcadeToolManager(
        default_user_id="test_user", client=mock_client, executor=custom_executor
    )


@pytest.fixture
def fake_tool_definition():
    """Return a fake tool definition for testing purposes."""
    fake_tool = MagicMock(spec=ToolDefinition)
    fake_tool.name = "SearchGoogle"
    fake_tool.description = "Test tool description"
    fake_tool.toolkit = MagicMock()
    fake_tool.toolkit.name = "Search"
    fake_tool.requirements = None
    fake_tool.input = MagicMock()
    fake_tool.input.parameters = []
    return fake_tool


# --- Tests for _create_tool_function ---


def test_create_tool_function_success_custom(manager_with_custom_executor):
    """
    Test that the tool function executes successfully using the custom executor.
    The custom executor simply returns "Tool executed".
    """
    tool_function = manager_with_custom_executor._create_tool_function("test_tool")
    result = tool_function()
    assert result == "Tool executed"


def test_create_tool_function_forwards_kwargs_custom(manager_with_custom_executor):
    """
    Test that extra keyword arguments are forwarded correctly to the custom executor.
    The custom executor ignores the kwargs and returns "Tool executed".
    """
    tool_function = manager_with_custom_executor._create_tool_function("test_tool")
    result = tool_function(param1="value1", param2=2)
    assert result == "Tool executed"


def test_create_tool_function_unauthorized(manager_with_default_executor):
    """
    Test that the tool function raises a ValueError when authorization fails using the default executor.
    """
    # Mock an authorization failure by having authorize_tool raise ValueError.
    manager_with_default_executor.authorize_tool = MagicMock(
        side_effect=ValueError("Authorization failed for test_tool")
    )
    manager_with_default_executor.execute_tool = MagicMock()

    tool_function = manager_with_default_executor._create_tool_function("test_tool")

    with pytest.raises(ValueError, match="Authorization failed for test_tool"):
        tool_function()

    manager_with_default_executor.authorize_tool.assert_called_once_with("test_user", "test_tool")
    manager_with_default_executor.execute_tool.assert_not_called()  # auth fails before this is called


def test_create_tool_function_execution_failure(manager_with_default_executor):
    """
    Test that when tool execution returns a failing value, that value is returned.
    """
    manager_with_default_executor.authorize_tool = MagicMock()  # auth passes

    manager_with_default_executor.execute_tool = MagicMock(return_value="error")

    tool_function = manager_with_default_executor._create_tool_function("test_tool")
    result = tool_function()

    assert result == "error"
    manager_with_default_executor.authorize_tool.assert_called_once_with("test_user", "test_tool")
    manager_with_default_executor.execute_tool.assert_called_once_with("test_user", "test_tool")


# --- Test for _wrap_arcade_tool ---


def test_wrap_arcade_tool(manager_with_default_executor, fake_tool_definition):
    """
    Test that _wrap_arcade_tool correctly creates a StructuredTool.
    """
    fake_tool_definition.description = "Test tool"
    tool_name = "test_tool"

    # Patch the conversion utilities. Also, override _create_tool_function to return a dummy function.
    with (
        patch(
            "crewai_arcade.manager.tool_definition_to_pydantic_model", return_value="args_schema"
        ) as mock_to_model,
        patch(
            "crewai_arcade.structured.StructuredTool.from_function", return_value="structured_tool"
        ) as mock_from_function,
        patch.object(
            manager_with_default_executor,
            "_create_tool_function",
            return_value=lambda *a, **kw: None,
        ) as mock_create_tool,
    ):
        result = manager_with_default_executor._wrap_arcade_tool(tool_name, fake_tool_definition)

    assert result == "structured_tool"
    mock_to_model.assert_called_once_with(fake_tool_definition)
    mock_from_function.assert_called_once_with(
        func=mock_create_tool.return_value,
        name=tool_name,
        description="Test tool",
        args_schema="args_schema",
    )


# --- Tests for tool registration (init_tools, add_tools, get_tools) ---


def test_init_tools_with_tool(manager_with_default_executor, fake_tool_definition):
    """
    Test that init_tools clears and initializes the tools in the manager using tool names.
    """
    manager_with_default_executor._client.tools.get.return_value = fake_tool_definition
    manager_with_default_executor.init_tools(tools=["Search.SearchGoogle"])

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager_with_default_executor._tools
    assert len(manager_with_default_executor._tools) == 1


def test_init_tools_with_toolkit(manager_with_default_executor, fake_tool_definition):
    """
    Test that init_tools correctly fetches tools using a toolkit.
    """
    # Simulate that listing a toolkit returns a list with the fake tool
    manager_with_default_executor._client.tools.list.return_value = [fake_tool_definition]
    manager_with_default_executor.init_tools(toolkits=["Search"])

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager_with_default_executor._tools
    assert len(manager_with_default_executor._tools) == 1


def test_init_tools_with_none(manager_with_default_executor, fake_tool_definition):
    """
    Test that init_tools with no arguments retrieves all tools.
    """
    manager_with_default_executor._client.tools.list.return_value = [fake_tool_definition]
    manager_with_default_executor.init_tools()

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager_with_default_executor._tools
    assert len(manager_with_default_executor._tools) == 1


def test_add_tools(manager_with_default_executor, fake_tool_definition):
    """
    Test that add_tools supplements the manager's existing tool dictionary.
    """
    # Set an initial tool in _tools.
    fake_initial_tool = MagicMock(spec=ToolDefinition)
    fake_initial_tool.name = "InitialTool"
    fake_initial_tool.toolkit = MagicMock()
    fake_initial_tool.toolkit.name = "InitialToolkit"
    initial_key = f"{fake_initial_tool.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_initial_tool.name}"
    manager_with_default_executor._tools[initial_key] = fake_initial_tool

    # Mock retrieval of a new tool.
    manager_with_default_executor._client.tools.get.return_value = fake_tool_definition
    manager_with_default_executor.add_tools(tools=["Search.SearchGoogle"])

    new_key = f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    assert initial_key in manager_with_default_executor._tools
    assert new_key in manager_with_default_executor._tools


def test_get_tools_with_existing_tools(manager_with_default_executor, fake_tool_definition):
    """
    Test that get_tools wraps existing tools if they are already registered.
    """
    manager_with_default_executor._client.tools.get.return_value = fake_tool_definition
    manager_with_default_executor.init_tools(tools=["Search.SearchGoogle"])
    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )

    # Patch _wrap_arcade_tool to verify that it is called.
    with patch.object(
        manager_with_default_executor, "_wrap_arcade_tool", side_effect=lambda name, td: (name, td)
    ) as mock_wrap:
        crewai_tools = manager_with_default_executor.get_tools()

    assert len(crewai_tools) == 1
    assert crewai_tools[0] == (expected_key, fake_tool_definition)
    mock_wrap.assert_called_once_with(expected_key, fake_tool_definition)


def test_get_tools_with_missing_tool_and_toolkit(
    manager_with_default_executor, fake_tool_definition
):
    """
    Test that get_tools adds missing tools and toolkits when not already registered.
    """
    manager_with_default_executor._tools = {}
    manager_with_default_executor._client.tools.get.return_value = fake_tool_definition
    manager_with_default_executor._client.tools.list.return_value = [fake_tool_definition]

    with patch.object(
        manager_with_default_executor, "_wrap_arcade_tool", side_effect=lambda name, td: (name, td)
    ) as mock_wrap:
        crewai_tools = manager_with_default_executor.get_tools(
            tools=["Search.SearchGoogle"], toolkits=["Search"]
        )

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager_with_default_executor._tools
    assert len(crewai_tools) == 1
    assert crewai_tools[0] == (expected_key, fake_tool_definition)
    mock_wrap.assert_called_once_with(expected_key, fake_tool_definition)
