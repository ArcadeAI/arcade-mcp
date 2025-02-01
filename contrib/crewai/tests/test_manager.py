from unittest.mock import MagicMock, patch

import pytest
from arcadepy.pagination import SyncOffsetPage
from arcadepy.types import ToolDefinition
from crewai_arcade.manager import TOOL_NAME_SEPARATOR, ArcadeToolManager

# --- Fixtures ---


@pytest.fixture
def mock_client():
    """Create a fake Arcade client fixture."""
    return MagicMock()


@pytest.fixture
def manager(mock_client):
    """Return an ArcadeToolManager with a test user and fake client."""
    return ArcadeToolManager(user_id="test_user", client=mock_client)


@pytest.fixture
def fake_tool_definition():
    """Return a fake tool definition for testing purposes."""
    fake_tool = MagicMock(spec=ToolDefinition)
    fake_tool.name = "SearchGoogle"
    fake_tool.description = "Test tool description"
    fake_tool.toolkit = MagicMock()
    fake_tool.toolkit.name = "Search"
    fake_tool.requirements = None
    return fake_tool


# --- Tests for create_tool_function ---


def test_create_tool_function_success(manager):
    """
    Test that the tool function executes successfully when authorization passes.
    """
    # Override authorization-related methods to simulate a completed auth
    manager.requires_auth = lambda tool: True
    fake_auth_response = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="completed"
    )
    manager.authorize = lambda tool, user_id: fake_auth_response
    manager.wait_for_completion = lambda auth: fake_auth_response
    manager.is_authorized = lambda auth_id: True

    # Setup execute to return a successful response
    fake_output = MagicMock(value="result", error=None)
    fake_response = MagicMock(success=True, output=fake_output)
    manager._client.tools.execute.return_value = fake_response

    tool_function = manager._create_tool_function("test_tool")
    result = tool_function()  # Call without args

    assert result == "result"
    manager._client.tools.execute.assert_called_once_with(
        tool_name="test_tool", input={}, user_id="test_user"
    )


def test_create_tool_function_unauthorized(manager):
    """
    Test that a tool function returns a ValueError when authorization fails.
    """
    manager.requires_auth = lambda tool: True
    fake_auth_response = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="pending"
    )
    manager.authorize = lambda tool, user_id: fake_auth_response
    manager.wait_for_completion = lambda auth: fake_auth_response
    manager.is_authorized = lambda auth_id: False  # Simulate failing auth

    tool_function = manager._create_tool_function("test_tool")
    result = tool_function()

    assert isinstance(result, ValueError)
    assert "Authorization failed for test_tool" in str(result)


def test_create_tool_function_execution_failure(manager):
    """
    Test that a tool function returns an error string when tool execution fails.
    """
    manager.requires_auth = lambda tool: True
    fake_auth_response = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="completed"
    )
    manager.authorize = lambda tool, user_id: fake_auth_response
    manager.wait_for_completion = lambda auth: fake_auth_response
    manager.is_authorized = lambda auth_id: True

    # Simulate unsuccessful execution with a provided error message.
    fake_response = MagicMock(success=False, output=MagicMock(error="error"))
    manager._client.tools.execute.return_value = fake_response

    tool_function = manager._create_tool_function("test_tool")
    result = tool_function()

    # In our wrapped function, when an error is reported we simply return the error string.
    assert result == "error"


# --- Test for wrap_tool ---


def test_wrap_tool(manager, fake_tool_definition):
    """
    Test that wrap_tool correctly creates a StructuredTool.
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
            manager, "_create_tool_function", return_value=lambda *a, **kw: None
        ) as mock_create_tool,
    ):
        result = manager.wrap_tool(tool_name, fake_tool_definition)

    assert result == "structured_tool"
    mock_to_model.assert_called_once_with(fake_tool_definition)
    mock_from_function.assert_called_once_with(
        func=mock_create_tool.return_value,
        name=tool_name,
        description="Test tool",
        args_schema="args_schema",
    )


# --- Tests for tool registration (init_tools, add_tools, get_tools) ---


def test_init_tools_with_tool(manager, fake_tool_definition):
    """
    Test that init_tools clears and initializes the manager's tool dictionary.
    """
    manager._client.tools.get.return_value = fake_tool_definition

    manager.init_tools(tools=["Search.SearchGoogle"])

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager.tools
    assert len(manager.tools) == 1


def test_init_tools_with_toolkit(manager, fake_tool_definition):
    """
    Test that init_tools clears and initializes the manager's tool dictionary.
    """
    manager._client.tools.list.return_value = SyncOffsetPage(items=[fake_tool_definition])

    manager.init_tools(toolkits=["Search"])

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager.tools
    assert len(manager.tools) == 1


def test_init_tools_with_none(manager, fake_tool_definition):
    """
    Test that init_tools clears and initializes the manager's tool dictionary.
    """
    manager._client.tools.list.return_value = SyncOffsetPage(items=[fake_tool_definition])

    manager.init_tools()

    expected_key = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )
    assert expected_key in manager.tools
    assert len(manager.tools) == 1


def test_add_tools(manager, fake_tool_definition):
    """
    Test that add_tools supplements the existing tool list.
    """
    # Setup an already added tool
    fake_initial_tool = MagicMock()
    fake_initial_tool.name = "InitialTool"
    fake_initial_tool.toolkit = MagicMock()
    fake_initial_tool.toolkit.name = "InitialToolkit"
    initial_key = f"{fake_initial_tool.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_initial_tool.name}"
    manager._tools[initial_key] = fake_initial_tool

    # Simulate new tool retrieval.
    manager._client.tools.get.return_value = fake_tool_definition
    manager.add_tools(tools=["Search.SearchGoogle"])

    new_key = f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    assert initial_key in manager._tools
    assert new_key in manager._tools


def test_get_tools_with_existing_tools(manager, fake_tool_definition):
    """
    Test that get_tools wraps existing tools if present in the manager.
    """
    manager._client.tools.get.return_value = fake_tool_definition
    manager.init_tools(tools=["Search.SearchGoogle"])

    with patch.object(manager, "wrap_tool", side_effect=lambda name, td: (name, td)) as mock_wrap:
        result = manager.get_tools()

    key_expected = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )

    assert len(result) == 1
    assert result[0][0] == key_expected
    assert result[0][1] == fake_tool_definition
    assert mock_wrap.call_count == 1


def test_get_tools_with_missing_tool_and_toolkit(manager, fake_tool_definition):
    """
    Test that get_tools adds missing tools and toolkits if they are not already registered.
    """
    manager._tools = {}

    manager._client.tools.get.return_value = fake_tool_definition
    manager._client.tools.list.return_value = [fake_tool_definition]

    with patch.object(manager, "wrap_tool", side_effect=lambda name, td: (name, td)) as mock_wrap:
        result = manager.get_tools(tools=["Search.SearchGoogle"], toolkits=["Search"])

    key_expected = (
        f"{fake_tool_definition.toolkit.name}{TOOL_NAME_SEPARATOR}{fake_tool_definition.name}"
    )

    assert len(result) == 1
    assert result[0][0] == key_expected
    assert result[0][1] == fake_tool_definition
    assert key_expected in manager._tools
    assert mock_wrap.call_count == 1
