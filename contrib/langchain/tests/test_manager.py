from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcadepy import NOT_GIVEN
from arcadepy.pagination import AsyncOffsetPage, SyncOffsetPage
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse
from langchain_arcade.manager import ArcadeToolManager, AsyncToolManager, ToolManager


@pytest.fixture
def mock_arcade_client():
    """
    A fixture to mock the Arcade client object for testing the ToolManager.

    This mocks all relevant methods used by the manager, including:
    - tools.get
    - tools.list
    - tools.authorize
    - auth.status
    - auth.wait_for_completion
    """
    mock_client = MagicMock()
    # Mock the "tools" sub-client
    mock_client.tools.get = MagicMock()
    mock_client.tools.list = MagicMock()
    mock_client.tools.authorize = MagicMock()
    # Mock the "auth" sub-client
    mock_client.auth.status = MagicMock()
    mock_client.auth.wait_for_completion = MagicMock()

    return mock_client


@pytest.fixture
def async_mock_arcade_client():
    """
    A fixture to mock the Arcade client object for testing the AsyncToolManager.
    """
    mock_client = AsyncMock()
    mock_client.tools.get = AsyncMock()
    mock_client.tools.list = AsyncMock()
    mock_client.tools.authorize = AsyncMock()
    mock_client.auth.status = AsyncMock()
    mock_client.auth.wait_for_completion = AsyncMock()
    return mock_client


@pytest.fixture
def manager(mock_arcade_client):
    """
    A fixture that creates a ToolManager with the mocked Arcade client.
    """
    return ToolManager(client=mock_arcade_client)


@pytest.fixture
def async_manager(async_mock_arcade_client):
    """
    A fixture that creates an AsyncToolManager with the mocked Arcade client.
    """
    return AsyncToolManager(client=async_mock_arcade_client)


@pytest.fixture(params=[("sync", False), ("async", True)])
def manager_fixture(request, manager, async_manager):
    """
    A parameterized fixture that returns a tuple with:
    - The appropriate manager (sync or async)
    - A boolean indicating if it's async
    - The appropriate mock client
    """
    param_name, is_async = request.param
    if is_async:
        return async_manager, True
    else:
        return manager, False


@pytest.fixture
def make_tool():
    """
    A factory fixture for creating a valid ToolDefinition with a given
    fully qualified name. Because the underlying ToolDefinition model
    expects "toolkit" to be a dictionary with at least one field (for example "slug"),
    and "requirements.authorization" to be a valid dictionary if present, we set them up
    accordingly.
    """

    def _make_tool(fully_qualified_name="GoogleSearch_Search", **kwargs):
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
            "qualified_name": fully_qualified_name,
            "name": raw_tool_name,
            "toolkit": toolkit,
            "input": tool_input,
            "description": description,
            "requirements": requirements,
        }
        data.update(kwargs)  # merge any extras

        return ToolDefinition(**data)

    return _make_tool


async def maybe_await(obj, is_async):
    """Helper to handle both sync and async return values"""
    if is_async:
        return await obj
    return obj


@pytest.mark.asyncio
async def test_init_tools_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that init_tools clears any existing tools and retrieves new ones
    from either an explicit list of tools or an entire toolkit.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_tool = make_tool("GoogleSearch_Search")
    client.tools.get.return_value = mock_tool

    page_cls = AsyncOffsetPage if is_async else SyncOffsetPage
    client.tools.list.return_value = page_cls(items=[mock_tool])

    # Act
    result = await maybe_await(
        manager.init_tools(tools=["GoogleSearch_Search"]), is_async
    )

    # Assert
    assert "GoogleSearch_Search" in manager.tools
    assert manager._tools["GoogleSearch_Search"] == mock_tool
    client.tools.get.assert_called_once_with(name="GoogleSearch_Search")
    # Verify the result is a list of StructuredTool objects
    assert len(result) == 1


@pytest.mark.asyncio
async def test_to_langchain_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that to_langchain returns the tools as StructuredTool objects.
    """
    # Arrange
    manager, is_async = manager_fixture

    mock_tool = make_tool("GoogleSearch_Search")
    manager._tools = {"GoogleSearch_Search": mock_tool}

    # Act - with default parameters
    result = await maybe_await(manager.to_langchain(), is_async)

    # Assert
    assert len(result) == 1
    assert result[0].name == "GoogleSearch_Search"

    # Act - with underscores=False
    result = await maybe_await(manager.to_langchain(use_underscores=False), is_async)

    # Assert
    assert len(result) == 1
    assert result[0].name == "GoogleSearch.Search"


@pytest.mark.asyncio
async def test_deprecated_get_tools_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that the deprecated get_tools method still works but issues a warning.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_tool = make_tool("GoogleSearch_Search")
    client.tools.get.return_value = mock_tool
    manager._tools = {}  # Ensure no tools are already loaded

    # Act - Check for deprecation warning
    with pytest.warns(DeprecationWarning):
        result = await maybe_await(
            manager.get_tools(tools=["GoogleSearch_Search"]), is_async
        )

    # Assert - Method should still work
    assert len(result) == 1
    assert "GoogleSearch_Search" in manager.tools
    client.tools.get.assert_called_once_with(name="GoogleSearch_Search")


@pytest.mark.asyncio
async def test_add_tool_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that add_tool adds a single tool to the manager without clearing existing tools.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    # Set up two different mock tools
    mock_tool_google = make_tool("GoogleSearch_Search")
    mock_tool_bing = make_tool("BingSearch_Search")

    # First tool already exists in manager
    manager._tools = {"GoogleSearch_Search": mock_tool_google}

    # Second tool will be added
    client.tools.get.return_value = mock_tool_bing

    # Act
    await maybe_await(manager.add_tool("BingSearch_Search"), is_async)

    # Assert - Both tools should now be in the manager
    assert "GoogleSearch_Search" in manager.tools
    assert "BingSearch_Search" in manager.tools
    assert len(manager.tools) == 2
    client.tools.get.assert_called_once_with(name="BingSearch_Search")


@pytest.mark.asyncio
async def test_add_toolkit_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that add_toolkit adds all tools from a toolkit without clearing existing tools.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    # Create a tool that's already in the manager
    mock_tool_send_email = make_tool("Gmail_SendEmail")
    manager._tools = {"Gmail_SendEmail": mock_tool_send_email}

    # Create tools to be added from the toolkit
    mock_tool_list_emails = make_tool("Gmail_ListEmails")
    mock_tool_trash_email = make_tool("Gmail_TrashEmail")

    # Mock the response for toolkit listing
    page_cls = AsyncOffsetPage if is_async else SyncOffsetPage
    client.tools.list.return_value = page_cls(
        items=[mock_tool_list_emails, mock_tool_trash_email]
    )

    # Act
    await maybe_await(manager.add_toolkit("Search"), is_async)

    # Assert - All tools should now be in the manager
    assert len(manager.tools) == 3
    assert "Gmail_SendEmail" in manager.tools
    assert "Gmail_ListEmails" in manager.tools
    assert "Gmail_TrashEmail" in manager.tools
    client.tools.list.assert_called_once_with(
        toolkit="Search", limit=NOT_GIVEN, offset=NOT_GIVEN
    )


@pytest.mark.asyncio
async def test_is_authorized_with_response_object_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client
):
    """
    Test the is_authorized method accepting both authorization ID string and AuthorizationResponse.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_type = AsyncMock if is_async else MagicMock
    client.auth.status.return_value = mock_type(status="completed")

    # Create an auth response object
    auth_response = AuthorizationResponse(
        id="auth_abc", status="pending", tool_fully_qualified_name="GoogleSearch_Search"
    )

    # Act - Test with string ID
    status_result1 = await maybe_await(manager.is_authorized("auth_abc"), is_async)

    # Act - Test with response object
    status_result2 = await maybe_await(manager.is_authorized(auth_response), is_async)

    # Assert
    assert status_result1 is True
    assert status_result2 is True
    client.auth.status.assert_any_call(id="auth_abc")
    client.auth.status.assert_any_call(
        id="auth_abc"
    )  # Should be called with the same ID both times


@pytest.mark.asyncio
async def test_wait_for_auth_with_response_object_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client
):
    """
    Test the wait_for_auth method accepting both authorization ID string and AuthorizationResponse.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    completed_response = AuthorizationResponse(
        id="auth_abc",
        status="completed",
        tool_fully_qualified_name="GoogleSearch_Search",
    )
    client.auth.wait_for_completion.return_value = completed_response

    # Create an auth response object
    auth_response = AuthorizationResponse(
        id="auth_abc", status="pending", tool_fully_qualified_name="GoogleSearch_Search"
    )

    # Act - Test with string ID
    result1 = await maybe_await(manager.wait_for_auth("auth_abc"), is_async)

    # Act - Test with response object
    result2 = await maybe_await(manager.wait_for_auth(auth_response), is_async)

    # Assert
    assert result1 == completed_response
    assert result2 == completed_response
    client.auth.wait_for_completion.assert_any_call("auth_abc")
    client.auth.wait_for_completion.assert_any_call(
        "auth_abc"
    )  # Should be called with the same ID both times


@pytest.mark.asyncio
async def test_get_tools_no_init_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that the deprecated get_tools method without previous initialization
    issues a warning and fetches tools.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_tool = make_tool("GoogleSearch_Search")
    page_cls = AsyncOffsetPage if is_async else SyncOffsetPage
    client.tools.list.return_value = page_cls(items=[mock_tool])

    # Act - Check for deprecation warning
    with pytest.warns(DeprecationWarning):
        tools = await maybe_await(
            manager.get_tools(), is_async
        )  # No param means manager calls list

    # Assert
    assert len(tools) == 0
    assert "GoogleSearch_Search" not in manager.tools


@pytest.mark.asyncio
async def test_get_tools_with_explicit_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that the deprecated get_tools method with explicitly specified tools
    issues a warning and fetches the requested tools.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_tool_google = make_tool("GoogleSearch_Search")
    mock_tool_bing = make_tool("BingSearch_Search")
    client.tools.get.side_effect = [mock_tool_google, mock_tool_bing]

    # Act - Check for deprecation warning
    with pytest.warns(DeprecationWarning):
        retrieved_tools = await maybe_await(
            manager.get_tools(tools=["GoogleSearch_Search", "BingSearch_Search"]),
            is_async,
        )

    # Assert
    assert len(retrieved_tools) == 2
    assert set(manager.tools) == {"GoogleSearch_Search", "BingSearch_Search"}
    client.tools.get.assert_any_call(name="GoogleSearch_Search")
    client.tools.get.assert_any_call(name="BingSearch_Search")


def test_arcade_tool_manager_deprecation_warning():
    """
    Test that the ArcadeToolManager class issues a deprecation warning.
    """
    # Act - Check for deprecation warning
    with pytest.warns(DeprecationWarning) as warnings_record:
        ArcadeToolManager(client=MagicMock())
    # Assert
    assert any(
        "ArcadeToolManager is deprecated" in str(w.message) for w in warnings_record
    )


@pytest.mark.asyncio
async def test_authorize_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client
):
    """
    Test the authorize method to ensure it calls the Arcade client's
    tools.authorize method correctly.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    auth_response = AuthorizationResponse(
        id="auth_123", status="pending", tool_fully_qualified_name="GoogleSearch_Search"
    )
    client.tools.authorize.return_value = auth_response

    # Act
    response = await maybe_await(
        manager.authorize(tool_name="GoogleSearch_Search", user_id="user_123"), is_async
    )

    # Assert
    assert response.id == "auth_123"
    assert response.status == "pending"
    client.tools.authorize.assert_called_once_with(
        tool_name="GoogleSearch_Search", user_id="user_123"
    )


def test_requires_auth_true(manager, make_tool):
    """
    Test the requires_auth method returning True if
    the stored tool definition's requirements contain an authorization entry.
    """
    # Arrange
    tool_name = "GoogleSearch_Search"
    # Pass a MagicMock with 'authorization' to ensure it gets converted
    mock_tool_def = make_tool(
        tool_name, requirements=MagicMock(authorization="some_required_auth")
    )
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
    tool_name = "GoogleSearch_Search"
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
    tool_name = "GoogleSearch_Search"
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
    mock_tool = make_tool("GoogleSearch_Search")
    mock_arcade_client.tools.get.return_value = mock_tool

    # Act
    results = manager._retrieve_tool_definitions(
        tools=["GoogleSearch_Search"], toolkits=None
    )

    # Assert
    assert len(results) == 1
    assert results[0].fully_qualified_name == "GoogleSearch_Search"
    mock_arcade_client.tools.get.assert_called_once_with(name="GoogleSearch_Search")


def test_retrieve_tool_definitions_toolkits_only(
    manager, mock_arcade_client, make_tool
):
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
    assert results[0].fully_qualified_name == "Search_SearchBing"
    mock_arcade_client.tools.list.assert_called_once_with(
        toolkit="Search", limit=NOT_GIVEN, offset=NOT_GIVEN
    )


def test_retrieve_tool_definitions_raise_on_empty(manager):
    """
    Test that _retrieve_tool_definitions raises ValueError when no tools or toolkits
    are provided and raise_on_empty is True.
    """
    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        manager._retrieve_tool_definitions(
            tools=None, toolkits=None, raise_on_empty=True
        )

    assert "No tools or toolkits provided" in str(excinfo.value)


def test_retrieve_tool_definitions_empty_no_raise(manager):
    """
    Test that _retrieve_tool_definitions returns empty list when no tools or toolkits
    are provided and raise_on_empty is False.
    """
    # Act
    results = manager._retrieve_tool_definitions(
        tools=None, toolkits=None, raise_on_empty=False
    )

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_retrieve_tool_definitions_with_limit_offset_parameterized(
    manager_fixture, mock_arcade_client, async_mock_arcade_client, make_tool
):
    """
    Test that _retrieve_tool_definitions respects limit and offset parameters.
    """
    # Arrange
    manager, is_async = manager_fixture
    client = async_mock_arcade_client if is_async else mock_arcade_client

    mock_tool = make_tool("Search_SearchGoogle")
    page_cls = AsyncOffsetPage if is_async else SyncOffsetPage
    client.tools.list.return_value = page_cls(items=[mock_tool])

    # Act
    if is_async:
        results = await manager._retrieve_tool_definitions(
            toolkits=["Search"], limit=10, offset=5
        )
    else:
        results = manager._retrieve_tool_definitions(
            toolkits=["Search"], limit=10, offset=5
        )

    # Assert
    assert len(results) > 0
    client.tools.list.assert_called_once_with(toolkit="Search", limit=10, offset=5)


def test_get_client_config_with_kwargs():
    """
    Test that _get_client_config prioritizes kwargs over environment variables.
    """
    # Arrange
    manager = ToolManager(client=MagicMock())  # Client won't be used here

    # Act
    with patch.dict(
        "os.environ", {"ARCADE_API_KEY": "env_key", "ARCADE_BASE_URL": "env_url"}
    ):
        result = manager._get_client_config(api_key="kwarg_key", base_url="kwarg_url")

    # Assert
    assert result["api_key"] == "kwarg_key"
    assert result["base_url"] == "kwarg_url"


def test_get_client_config_with_env_vars():
    """
    Test that _get_client_config falls back to environment variables when kwargs not provided.
    """
    # Arrange
    manager = ToolManager(client=MagicMock())  # Client won't be used here

    # Act
    with patch.dict(
        "os.environ", {"ARCADE_API_KEY": "env_key", "ARCADE_BASE_URL": "env_url"}
    ):
        result = manager._get_client_config()

    # Assert
    assert result["api_key"] == "env_key"
    assert result["base_url"] == "env_url"


def test_getitem_access(manager, make_tool):
    """
    Test that __getitem__ allows dictionary-style access to tools.
    """
    # Arrange
    tool_name = "Search_SearchGoogle"
    mock_tool_def = make_tool(tool_name)
    manager._tools[tool_name] = mock_tool_def

    # Act
    definition = manager[tool_name]

    # Assert
    assert definition == mock_tool_def


def test_getitem_missing(manager):
    """
    Test that __getitem__ raises ValueError for missing tools.
    """
    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        _ = manager["Nonexistent.Tool"]

    assert "Tool 'Nonexistent.Tool' not found" in str(excinfo.value)


def test_create_tool_map_with_underscores(make_tool):
    """
    Test the _create_tool_map function with use_underscores=True.
    """
    # Arrange
    from langchain_arcade.manager import _create_tool_map

    tool1 = make_tool("GoogleSearch.Search")
    tool2 = make_tool("Gmail.SendEmail")

    # Act
    result = _create_tool_map([tool1, tool2], use_underscores=True)

    # Assert
    assert "GoogleSearch_Search" in result
    assert "Gmail_SendEmail" in result
    assert len(result) == 2


def test_create_tool_map_with_dots(make_tool):
    """
    Test the _create_tool_map function with use_underscores=False.
    """
    # Arrange
    from langchain_arcade.manager import _create_tool_map

    tool1 = make_tool("GoogleSearch.Search")
    tool2 = make_tool("Gmail.SendEmail")

    # Act
    result = _create_tool_map([tool1, tool2], use_underscores=False)

    # Assert
    assert "GoogleSearch.Search" in result
    assert "Gmail.SendEmail" in result
    assert len(result) == 2
