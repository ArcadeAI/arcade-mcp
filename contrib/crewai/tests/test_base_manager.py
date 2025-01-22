from typing import Optional
from unittest.mock import Mock, patch

import pytest
from arcadepy._exceptions import ArcadeError

from .conftest import MockManager


def test_init_with_client(mock_arcade: Mock) -> None:
    """Test manager initialization with a client."""
    manager = MockManager(client=mock_arcade)
    assert manager.client == mock_arcade
    assert manager._tools == {}
    assert manager.wrapped_tools == {}  # Test the new wrapped_tools dict
    assert manager.user_id is None  # Test default user_id is None


def test_init_with_client_and_user_id(mock_arcade: Mock) -> None:
    """Test manager initialization with a client and user_id."""
    test_user_id = "test_user_123"
    manager = MockManager(client=mock_arcade, user_id=test_user_id)
    assert manager.client == mock_arcade
    assert manager._tools == {}
    assert manager.wrapped_tools == {}
    assert manager.user_id == test_user_id


@pytest.mark.parametrize(
    "api_key", [pytest.param("test_key", id="with_key"), pytest.param(None, id="without_key")]
)
def test_init_without_client(api_key: Optional[str], mock_arcade: Mock) -> None:
    """Test initialization without a client using different API key scenarios."""
    with patch.dict("os.environ", {"ARCADE_API_KEY": api_key} if api_key else {}, clear=True):
        if api_key is None:
            with pytest.raises(ArcadeError):
                MockManager()
        else:
            manager = MockManager(client=mock_arcade)
            assert isinstance(manager.client, Mock)
            assert manager._tools == {}
            assert manager.wrapped_tools == {}


def test_tools_property(manager: MockManager) -> None:
    """Test the tools property returns correct tool names."""
    manager._tools = {"tool1": Mock(), "tool2": Mock()}
    assert sorted(manager.tools) == ["tool1", "tool2"]


def test_iterator(manager: MockManager) -> None:
    """Test manager iteration returns correct tool pairs."""
    tool1, tool2 = Mock(), Mock()
    manager._tools = {"tool1": tool1, "tool2": tool2}
    assert sorted(manager) == [("tool1", tool1), ("tool2", tool2)]


def test_len(manager: MockManager) -> None:
    """Test manager length returns correct tool count."""
    manager._tools = {"tool1": Mock(), "tool2": Mock()}
    assert len(manager) == 2


@pytest.mark.parametrize("tool_name,exists", [("tool1", True), ("nonexistent", False)])
def test_getitem(manager: MockManager, tool_name: str, exists: bool) -> None:
    """Test dictionary-style access to tools."""
    tool = Mock()
    manager._tools = {"tool1": tool}

    if exists:
        assert manager[tool_name] == tool
    else:
        with pytest.raises(KeyError):
            manager[tool_name]


def test_init(manager: MockManager, mock_arcade: Mock) -> None:
    """Test tools initialization"""
    manager.init_tools()
    mock_arcade.tools.list.assert_called_once_with()
    assert len(manager.tools) == 2


def test_init_toolkits(manager: MockManager, mock_arcade: Mock) -> None:
    """Test toolkit initialization with specific toolkits."""
    toolkits = ["Google"]
    manager.init_tools(toolkits=toolkits)
    mock_arcade.tools.list.assert_called_once_with(toolkit=toolkits[0])
    assert len(manager.tools) == 2


def test_init_tools(manager: MockManager, mock_arcade: Mock) -> None:
    """Test tool initialization with specific tool IDs."""
    tools = ["Google.CreateEvent@0.1.2"]
    manager.init_tools(tools=tools)
    mock_arcade.tools.get.assert_called_once_with(tool_id=tools[0])
    assert len(manager.tools) == 1


def test_wrapped_tool_definition_single_tool(manager: MockManager, mock_arcade: Mock) -> None:
    """Test storage and retrieval of a single wrapped tool definition."""
    result = manager.get_tools(tools=["Google.CreateEvent@0.1.2"])
    wrapped_name = result[0]
    tool_def = manager.wrapped_tools[wrapped_name]

    assert tool_def is not None
    assert tool_def.name == "CreateEvent"
    assert tool_def.toolkit.name == "Google"


def test_wrapped_tool_definition_all_tools(manager: MockManager) -> None:
    """Test retrieval of all wrapped tool definitions."""
    manager.get_tools()
    assert len(manager.wrapped_tools) == 2  # Assuming mock returns 2 tools


def test_wrapped_tool_definition_init_tools(
    manager: MockManager,
) -> None:
    """Test wrapped tools after initializing with specific tool."""
    manager.init_tools(tools=["Google.CreateEvent@0.1.2"])
    manager.get_tools()
    assert len(manager.wrapped_tools) == 1
