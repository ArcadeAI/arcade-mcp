from unittest.mock import MagicMock

import pytest
from arcadepy.pagination import SyncOffsetPage
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse
from langchain_arcade.manager import ArcadeToolManager


@pytest.fixture
def mock_arcade_client():
    """
    A fixture to mock the Arcade client object for testing the ArcadeToolManager.

    This mocks all relevant methods used by the manager, including:
    - tools.get
    - tools.list
    - tools.authorize
    - auth.status
    """
    mock_client = MagicMock()
    # Mock the "tools" sub-client
    mock_client.tools.get = MagicMock()
    mock_client.tools.list = MagicMock()
    mock_client.tools.authorize = MagicMock()
    # Mock the "auth" sub-client
    mock_client.auth.status = MagicMock()

    return mock_client


@pytest.fixture
def manager(mock_arcade_client):
    """
    A fixture that creates an ArcadeToolManager with the mocked Arcade client.
    """
    return ArcadeToolManager(client=mock_arcade_client)


@pytest.fixture
def make_tool():
    """
    A factory fixture for creating a valid ToolDefinition with a given
    fully qualified name. Because the underlying ToolDefinition model
    expects "toolkit" to be a dictionary with at least one field (for example "slug"),
    and "requirements.authorization" to be a valid dictionary if present, we set them up
    accordingly.
    """

    def _make_tool(fully_qualified_name="Search_SearchGoogle", **kwargs):
        # Split on the first dot to derive a 'toolkit' slug and a tool 'name'
        if "." in fully_qualified_name:
            raw_toolkit, raw_tool_name = fully_qualified_name.split(".", 1)
        elif "_" in fully_qualified_name:
            # Convert from "_" to "." to match the expected format of tool name when
            # using Langchain models for LLM inference.
            raw_toolkit, raw_tool_name = fully_qualified_name.split("_", 1)

        else:
            raw_toolkit, raw_tool_name = fully_qualified_name, fully_qualified_name

        # Provide a default toolkit dict unless one already exists in kwargs
        toolkit = kwargs.pop("toolkit", {"name": raw_toolkit})

        # Provide a default input
        # arcadepy.types.ToolDefinition expects "input" to be a valid structure (dict).
        tool_input = kwargs.pop("input", {"parameters": []})

        # Convert MagicMock-based requirements (with authorization) to an appropriate dict,
        # or use what's passed. If none is passed, default to None.
        requirements = kwargs.pop("requirements", None)
        if requirements is not None and not isinstance(requirements, dict):
            # If it's e.g. a MagicMock(authorization="xyz"), convert it to a dict
            req_auth = getattr(requirements, "authorization", None)
            # If the test expects an authorization presence, represent it as a dict
            # that Pydantic can parse
            if req_auth is not None:
                requirements = {"authorization": {"type": req_auth}}
            else:
                requirements = {"authorization": None}

        # Provide a default description if none is supplied
        description = kwargs.pop("description", "Mock tool for testing")

        # Build the pydantic fields
        data = {
            "fully_qualified_name": fully_qualified_name,
            "name": raw_tool_name,
            "toolkit": toolkit,
            "input": tool_input,
            "description": description,
            "requirements": requirements,
        }
        data.update(kwargs)  # merge any extras

        return ToolDefinition(**data)

    return _make_tool


def test_init_tools(manager, mock_arcade_client, make_tool):
    """
    Test that init_tools clears any existing tools and retrieves new ones
    from either an explicit list of tools or an entire toolkit.
    """
    # Arrange
    mock_tool = make_tool("Search_SearchGoogle")
    mock_arcade_client.tools.get.return_value = mock_tool
    mock_arcade_client.tools.list.return_value = SyncOffsetPage(items=[mock_tool])
    # Act
    manager.init_tools(tools=["Search_SearchGoogle"])

    # Assert
    assert "Search_SearchGoogle" in manager.tools
    assert manager._tools["Search_SearchGoogle"] == mock_tool
    mock_arcade_client.tools.get.assert_called_once_with(name="Search_SearchGoogle")


def test_get_tools_no_init(manager, mock_arcade_client, make_tool):
    """
    If get_tools is called without init_tools and no tools are specified,
    it should call init_tools internally and fetch all available tools.
    """
    # Arrange
    mock_tool = make_tool("Search_SearchGoogle")
    mock_arcade_client.tools.list.return_value = SyncOffsetPage(items=[mock_tool])

    # Act
    tools = manager.get_tools()  # no param means manager auto-inits

    # Assert
    assert len(tools) == 1
    assert "Search_SearchGoogle" in manager.tools
    assert manager._tools["Search_SearchGoogle"] == mock_tool
    mock_arcade_client.tools.list.assert_called_once()


def test_get_tools_with_explicit(manager, mock_arcade_client, make_tool):
    """
    If tools or toolkits are provided to get_tools, the manager should
    retrieve or update the internal _tools dictionary accordingly,
    then return them as StructuredTool objects.
    """
    # Arrange
    mock_tool_google = make_tool("Search_SearchGoogle")
    mock_tool_bing = make_tool("Search_SearchBing")
    mock_arcade_client.tools.get.side_effect = [mock_tool_google, mock_tool_bing]

    # Act
    retrieved_tools = manager.get_tools(tools=["Search_SearchGoogle", "Search_SearchBing"])

    # Assert
    assert len(retrieved_tools) == 2
    assert set(manager.tools) == {"Search_SearchGoogle", "Search_SearchBing"}
    mock_arcade_client.tools.get.assert_any_call(name="Search_SearchGoogle")
    mock_arcade_client.tools.get.assert_any_call(name="Search_SearchBing")


def test_authorize(manager, mock_arcade_client):
    """
    Test the authorize method to ensure it calls the Arcade client's
    tools.authorize method correctly.
    """
    # Arrange
    mock_arcade_client.tools.authorize.return_value = AuthorizationResponse(
        id="auth_123", status="pending", tool_fully_qualified_name="Search_SearchGoogle"
    )

    # Act
    response = manager.authorize(tool_name="Search_SearchGoogle", user_id="user_123")

    # Assert
    assert response.id == "auth_123"
    assert response.status == "pending"
    mock_arcade_client.tools.authorize.assert_called_once_with(
        tool_name="Search_SearchGoogle", user_id="user_123"
    )


def test_is_authorized(manager, mock_arcade_client):
    """
    Test the is_authorized method which checks if authorization
    has completed for a given authorization ID.
    """
    # Arrange
    mock_arcade_client.auth.status.return_value = MagicMock(status="completed")

    # Act
    status_result = manager.is_authorized("auth_abc")

    # Assert
    assert status_result is True
    mock_arcade_client.auth.status.assert_called_once_with(id="auth_abc")


def test_requires_auth_true(manager, make_tool):
    """
    Test the requires_auth method returning True if
    the stored tool definition's requirements contain an authorization entry.
    """
    # Arrange
    tool_name = "Search_SearchGoogle"
    # Pass a MagicMock with 'authorization' to ensure it gets converted
    mock_tool_def = make_tool(tool_name, requirements=MagicMock(authorization="some_required_auth"))
    manager._tools[tool_name] = mock_tool_def

    # Act
    result = manager.requires_auth(tool_name)

    # Assert
    assert result is True


def test_requires_auth_false(manager, make_tool):
    """
    Test the requires_auth method returning False if authorization
    is not required in the tool definition.
    """
    # Arrange
    tool_name = "Search_SearchGoogle"
    mock_tool_def = make_tool(tool_name, requirements=MagicMock(authorization=None))
    manager._tools[tool_name] = mock_tool_def

    # Act
    result = manager.requires_auth(tool_name)

    # Assert
    assert result is False


def test_get_tool_definition_existing(manager, make_tool):
    """
    Test the internal _get_tool_definition method retrieving
    an existing tool definition by name.
    """
    # Arrange
    tool_name = "Search_SearchGoogle"
    mock_tool_def = make_tool(tool_name)
    manager._tools[tool_name] = mock_tool_def

    # Act
    definition = manager._get_tool_definition(tool_name)

    # Assert
    assert definition == mock_tool_def


def test_get_tool_definition_missing(manager):
    """
    Test the internal _get_tool_definition method raising a ValueError
    if the tool is not in the manager.
    """
    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        manager._get_tool_definition("Nonexistent.Tool")

    assert "Tool 'Nonexistent.Tool' not found" in str(excinfo.value)


def test_retrieve_tool_definitions_tools_only(manager, mock_arcade_client, make_tool):
    """
    Test the internal _retrieve_tool_definitions method by specifying tools only.
    """
    # Arrange
    mock_tool = make_tool("Search_SearchGoogle")
    mock_arcade_client.tools.get.return_value = mock_tool

    # Act
    results = manager._retrieve_tool_definitions(tools=["Search_SearchGoogle"], toolkits=None)

    # Assert
    assert len(results) == 1
    assert "Search_SearchGoogle" in results
    mock_arcade_client.tools.get.assert_called_once_with(name="Search_SearchGoogle")


def test_retrieve_tool_definitions_toolkits_only(manager, mock_arcade_client, make_tool):
    """
    Test the internal _retrieve_tool_definitions method by specifying toolkits.
    """
    # Arrange
    mock_tool = make_tool("Search_SearchBing")
    mock_arcade_client.tools.list.return_value = SyncOffsetPage(items=[mock_tool])

    # Act
    results = manager._retrieve_tool_definitions(tools=None, toolkits=["Search"])

    # Assert
    assert len(results) == 1
    assert "Search_SearchBing" in results
    mock_arcade_client.tools.list.assert_called_once_with(toolkit="Search")


def test_retrieve_tool_definitions_no_args(manager, mock_arcade_client, make_tool):
    """
    Test the internal _retrieve_tool_definitions method when no
    arguments are provided, retrieving all available tools.
    """
    # Arrange
    mock_tool1 = make_tool("Search_SearchGoogle")
    mock_tool2 = make_tool("Search_SearchBing")
    mock_arcade_client.tools.list.return_value = SyncOffsetPage(items=[mock_tool1, mock_tool2])

    # Act
    results = manager._retrieve_tool_definitions()

    # Assert
    assert len(results) == 2
    assert "Search_SearchGoogle" in results
    assert "Search_SearchBing" in results
    mock_arcade_client.tools.list.assert_called_once()
