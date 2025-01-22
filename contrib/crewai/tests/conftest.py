from typing import Optional
from unittest.mock import Mock

import pytest
from arcadepy import Arcade
from arcadepy.types import ToolGetResponse as ToolDefinition
from common_arcade.manager import BaseArcadeManager


def create_mock_tool(name: str = "TestTool", toolkit_name: str = "TestKit") -> Mock:
    # Create value schema mock for parameter
    param_value_schema = Mock()
    param_value_schema.val_type = "string"
    param_value_schema.enum = None
    param_value_schema.inner_val_type = None

    # Create parameter mock
    parameter = Mock()
    parameter.name = "title"
    parameter.value_schema = param_value_schema
    parameter.description = "Test parameter"
    parameter.inferrable = True
    parameter.required = True

    # Create input mock
    mock_input = Mock()
    mock_input.parameters = [parameter]

    # Create toolkit mock
    toolkit = Mock()
    toolkit.name = toolkit_name
    toolkit.description = "Test toolkit"
    toolkit.version = "0.1.2"

    # Create output value schema mock
    output_value_schema = Mock()
    output_value_schema.val_type = "json"
    output_value_schema.enum = None
    output_value_schema.inner_val_type = None

    # Create output mock
    output = Mock()
    output.available_modes = ["value", "error"]
    output.description = "Test output"
    output.value_schema = output_value_schema

    # Create authorization mocks
    oauth2 = Mock()
    oauth2.scopes = ["https://www.googleapis.com/auth/test"]

    authorization = Mock()
    authorization.oauth2 = oauth2
    authorization.provider_id = "google"
    authorization.provider_type = "oauth2"

    # Create requirements mock
    requirements = Mock()
    requirements.authorization = authorization

    # Create the main tool definition mock
    tool_definition = Mock(spec=ToolDefinition)
    tool_definition.input = mock_input
    tool_definition.name = name
    tool_definition.toolkit = toolkit
    tool_definition.description = "Test tool description"
    tool_definition.output = output
    tool_definition.requirements = requirements
    tool_definition.fully_qualified_name = f"{toolkit_name}.{name}@0.1.2"

    return tool_definition


@pytest.fixture
def mock_arcade() -> Mock:
    """Creates a mock Arcade client with predefined tools"""
    mock = Mock(spec=Arcade)
    tools_mock = Mock()

    # Create sample tools
    tools = [create_mock_tool("CreateEvent", "Google"), create_mock_tool("ListEvents", "Google")]

    # Setup mock responses
    tools_mock.list.return_value = tools
    tools_mock.get.side_effect = lambda name: next(
        (t for t in tools if t.fully_qualified_name == name), None
    )

    mock.tools = tools_mock
    return mock


class MockManager(BaseArcadeManager):
    """Test implementation of BaseArcadeManager for testing purposes."""

    def __init__(self, client: Optional[Arcade] = None, user_id: Optional[str] = None) -> None:
        super().__init__(client, user_id)
        self.wrapped_tools: dict[str, ToolDefinition] = {}

    def wrap_tool(self, name: str, tool_def: ToolDefinition, **kwargs) -> str:
        """Wraps a tool definition with a new name.

        Args:
            name: Original tool name
            tool_def: Tool definition to wrap
            **kwargs: Additional wrapping parameters

        Returns:
            str: The wrapped tool name
        """
        wrapped_name = f"wrapped_{name}"
        self.wrapped_tools[wrapped_name] = tool_def
        return wrapped_name


@pytest.fixture
def manager(mock_arcade: Mock) -> MockManager:
    """Creates a TestManager instance with a mock Arcade client.

    Args:
        mock_arcade: The mock Arcade client fixture

    Returns:
        MockManager: Configured test manager instance
    """
    return MockManager(client=mock_arcade)
