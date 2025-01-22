from unittest.mock import MagicMock, Mock, patch

import pytest
from arcadepy.types import ToolGetResponse as ToolDefinition
from crewai_arcade.manager import CrewAIToolManager


@pytest.fixture
def mock_client():
    """Fixture to create a mock Arcade client."""
    return MagicMock()


def test_init_requires_user_id(mock_client):
    """Test that CrewAIToolManager requires user_id during initialization."""
    with pytest.raises(ValueError, match="user_id is required for CrewAIToolManager"):
        CrewAIToolManager(client=mock_client, user_id="")

    with pytest.raises(ValueError, match="user_id is required for CrewAIToolManager"):
        CrewAIToolManager(client=mock_client, user_id=None)

    # Should work with valid user_id
    manager = CrewAIToolManager(client=mock_client, user_id="test_user")
    assert manager.user_id == "test_user"


@pytest.fixture
def manager(mock_client):
    """Fixture to create a CrewAIToolManager instance with mocked client and user_id."""
    return CrewAIToolManager(client=mock_client, user_id="test_user")


@patch("crewai_arcade.manager.CrewAIToolManager.requires_auth")
@patch("crewai_arcade.manager.CrewAIToolManager.authorize")
@patch("crewai_arcade.manager.CrewAIToolManager.wait_for_completion")
@patch("crewai_arcade.manager.CrewAIToolManager.is_authorized")
def test_create_tool_function_success(
    mock_is_authorized, mock_authorize, mock_wait_for_completion, mock_requires_auth, manager
):
    """Test that the tool function executes successfully when authorized."""
    mock_requires_auth.return_value = True
    mock_authorize.return_value = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="completed"
    )
    mock_is_authorized.return_value = True
    mock_wait_for_completion.return_value = mock_authorize
    manager.client.tools.execute.return_value = MagicMock(
        success=True, output=MagicMock(value="result")
    )

    tool_function = manager.create_tool_function("test_tool")
    result = tool_function()

    assert result == "result"
    manager.client.tools.execute.assert_called_once_with(
        tool_name="test_tool", input={}, user_id="test_user"
    )


@patch("crewai_arcade.manager.CrewAIToolManager.requires_auth")
@patch("crewai_arcade.manager.CrewAIToolManager.authorize")
@patch("crewai_arcade.manager.CrewAIToolManager.wait_for_completion")
def test_create_tool_function_unauthorized(
    mock_wait_for_completion, mock_authorize, mock_requires_auth, manager
):
    """Test that the tool function returns a ValueError when authorization fails."""
    mock_requires_auth.return_value = True
    mock_authorize.return_value = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="pending"
    )
    mock_wait_for_completion.return_value = mock_authorize

    tool_function = manager.create_tool_function("test_tool")
    result = tool_function()
    assert isinstance(result, ValueError)
    assert "Authorization failed for test_tool" in str(result)


@patch("crewai_arcade.manager.CrewAIToolManager.requires_auth")
@patch("crewai_arcade.manager.CrewAIToolManager.authorize")
@patch("crewai_arcade.manager.CrewAIToolManager.wait_for_completion")
def test_create_tool_function_execution_failure(
    mock_wait_for_completion, mock_authorize, mock_requires_auth, manager
):
    """Test that the tool function returns a ValueError on execution failure."""
    mock_requires_auth.return_value = True
    mock_authorize.return_value = MagicMock(
        authorization_id="auth_id", url="http://auth.url", status="completed"
    )
    mock_wait_for_completion.return_value = mock_authorize
    manager.client.tools.execute.return_value = MagicMock(success=False, error="error")

    tool_function = manager.create_tool_function("test_tool")
    result = tool_function()
    assert isinstance(result, ValueError)


@patch("crewai_arcade.manager.StructuredTool.from_function")
@patch("crewai_arcade.manager.tool_definition_to_pydantic_model")
def test_wrap_tool(mock_tool_definition_to_pydantic_model, mock_from_function, manager):
    """Test the wrap_tool method to ensure it correctly wraps a tool function."""
    mock_tool_definition_to_pydantic_model.return_value = "args_schema"
    mock_from_function.return_value = "structured_tool"

    tool_definition = Mock(spec=ToolDefinition)
    tool_definition.description = "Test tool"
    tool_name = "test_tool"

    tool_function = manager.create_tool_function(tool_name)

    # Ensure wrap_tool uses the pre-created tool_function
    with patch.object(manager, "create_tool_function", return_value=tool_function):
        result = manager.wrap_tool(tool_name, tool_definition)
    assert result == "structured_tool"

    mock_tool_definition_to_pydantic_model.assert_called_once_with(tool_definition)
    mock_from_function.assert_called_once_with(
        func=tool_function,
        name=tool_name,
        description=tool_definition.description,
        args_schema="args_schema",
    )
