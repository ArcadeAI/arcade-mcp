from unittest.mock import AsyncMock, Mock

import pytest
from httpx import HTTPStatusError, Response

from arcade.client import Arcade, AsyncArcade, AuthProvider
from arcade.client.errors import (
    BadRequestError,
    EngineNotHealthyError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)
from arcade.client.schema import AuthResponse, ExecuteToolResponse
from arcade.core.schema import ToolDefinition

AUTH_RESPONSE_DATA = {
    "auth_id": "auth_123",
    "authorization_url": "https://example.com/auth",
    "status": "pending",
    "authorization_id": "auth_123",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
}

TOOL_RESPONSE_DATA = {
    "tool_name": "GetEmails",
    "tool_version": "0.1.0",
    "output": {"result": "Hello, World!"},
    "error": None,
    "invocation_id": "inv_123",
    "duration": 1.5,
    "finished_at": "2023-04-01T12:00:00Z",
    "success": True,
}

TOOL_DEFINITION_DATA = {
    "name": "GetEmails",
    "full_name": "TestToolkit.GetEmails",
    "description": "Retrieve emails from a user's inbox",
    "toolkit": {
        "name": "TestToolkit",
        "version": "0.1.0",
        "description": "A toolkit for testing",
    },
    "input_schema": {"type": "object", "properties": {"n_emails": {"type": "integer"}}},
    "output_schema": {"type": "array", "items": {"type": "string"}},
    "version": "0.1.0",
    "inputs": {"parameters": []},
    "output": {},
    "requirements": {"auth_requirements": []},
}

TOOL_AUTHORIZE_RESPONSE_DATA = {
    "authorization_id": "auth_456",
    "authorization_url": "https://example.com/auth",
    "scopes": ["scope1", "scope2"],
    "status": "pending",
}

HEALTH_CHECK_HEALTHY_RESPONSE_DATA = {
    "healthy": True,
}

HEALTH_CHECK_UNHEALTHY_RESPONSE_DATA = {
    "healthy": False,
    "reason": "Cannot reticulate splines",
}


@pytest.fixture
def test_sync_client():
    """Test client."""
    return Arcade(base_url="http://arcade.example.com", api_key="fake_api_key")


@pytest.fixture
def test_async_client():
    """Test client."""
    return AsyncArcade(base_url="http://arcade.example.com", api_key="fake_api_key")


@pytest.fixture
def mock_response():
    """Mock Response object for testing."""
    response = Mock(spec=Response)
    response.json.return_value = {}
    return response


@pytest.fixture
def mock_async_response():
    """Mock AsyncResponse object for testing."""
    response = AsyncMock(spec=Response)
    response.json.return_value = {}
    return response


@pytest.mark.parametrize(
    "error_code, expected_error",
    [
        (400, BadRequestError),
        (401, UnauthorizedError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (500, InternalServerError),
    ],
)
def test_handle_http_error(test_sync_client, error_code, expected_error, mock_response):
    """Test _handle_http_error method for different error codes."""
    mock_response.status_code = error_code
    mock_response.json.return_value = {"error": "Test error message"}

    # Create a mock HTTPStatusError
    mock_http_error = Mock(spec=HTTPStatusError)
    mock_http_error.response = mock_response

    with pytest.raises(expected_error):
        test_sync_client._handle_http_error(mock_http_error)  # Call the method on the instance


def test_arcade_auth_authorize(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.auth.authorize method."""
    monkeypatch.setattr(Arcade, "_execute_request", lambda *args, **kwargs: AUTH_RESPONSE_DATA)
    auth_response = test_sync_client.auth.authorize(
        provider=AuthProvider.google,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        user_id="sam@arcade-ai.com",
    )
    assert auth_response == AuthResponse(**AUTH_RESPONSE_DATA)


def test_arcade_auth_poll_authorization(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.auth.poll_authorization method."""
    monkeypatch.setattr(Arcade, "_execute_request", lambda *args, **kwargs: AUTH_RESPONSE_DATA)
    auth_response = test_sync_client.auth.status("auth_123")
    assert auth_response == AuthResponse(**AUTH_RESPONSE_DATA)


def test_arcade_tool_run(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.tools.run method."""
    monkeypatch.setattr(Arcade, "_execute_request", lambda *args, **kwargs: TOOL_RESPONSE_DATA)
    tool_response = test_sync_client.tools.run(
        tool_name="GetEmails",
        user_id="sam@arcade-ai.com",
        tool_version="0.1.0",
        inputs={"n_emails": 5},
    )
    assert tool_response == ExecuteToolResponse(**TOOL_RESPONSE_DATA)


def test_arcade_tool_get(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.tools.get method."""
    monkeypatch.setattr(Arcade, "_execute_request", lambda *args, **kwargs: TOOL_DEFINITION_DATA)
    tool_definition = test_sync_client.tools.get(director_id="default", tool_id="GetEmails")
    assert tool_definition == ToolDefinition(**TOOL_DEFINITION_DATA)


def test_arcade_tool_authorize(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.tools.authorize method."""
    monkeypatch.setattr(
        Arcade, "_execute_request", lambda *args, **kwargs: TOOL_AUTHORIZE_RESPONSE_DATA
    )
    auth_response = test_sync_client.tools.authorize(
        tool_name="GetEmails", user_id="sam@arcade-ai.com"
    )
    assert auth_response == AuthResponse(**TOOL_AUTHORIZE_RESPONSE_DATA)


def test_arcade_health_check(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.health.check method."""
    monkeypatch.setattr(
        Arcade, "_execute_request", lambda *args, **kwargs: HEALTH_CHECK_HEALTHY_RESPONSE_DATA
    )
    test_sync_client.health.check()
    assert True  # If no exception is raised, the test passes


def test_arcade_health_check_raises_error(test_sync_client, mock_response, monkeypatch):
    """Test Arcade.health.check method."""
    monkeypatch.setattr(
        Arcade, "_execute_request", lambda *args, **kwargs: HEALTH_CHECK_UNHEALTHY_RESPONSE_DATA
    )
    with pytest.raises(EngineNotHealthyError):
        test_sync_client.health.check()


@pytest.mark.asyncio
async def test_async_arcade_auth_authorize(test_async_client, mock_async_response, monkeypatch):
    """Test AsyncArcade.auth.authorize method."""

    async def mock_execute_request(*args, **kwargs):
        return AUTH_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    auth_response = await test_async_client.auth.authorize(
        provider=AuthProvider.google,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        user_id="sam@arcade-ai.com",
    )
    assert auth_response == AuthResponse(**AUTH_RESPONSE_DATA)


@pytest.mark.asyncio
async def test_async_arcade_auth_poll_authorization(
    test_async_client, mock_async_response, monkeypatch
):
    """Test AsyncArcade.auth.poll_authorization method."""

    async def mock_execute_request(*args, **kwargs):
        return AUTH_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    auth_response = await test_async_client.auth.status("auth_123")
    assert auth_response == AuthResponse(**AUTH_RESPONSE_DATA)


@pytest.mark.asyncio
async def test_async_arcade_tool_run(test_async_client, mock_async_response, monkeypatch):
    """Test AsyncArcade.tools.run method."""

    async def mock_execute_request(*args, **kwargs):
        return TOOL_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    tool_response = await test_async_client.tools.run(
        tool_name="GetEmails",
        user_id="sam@arcade-ai.com",
        tool_version="0.1.0",
        inputs={"n_emails": 5},
    )
    assert tool_response == ExecuteToolResponse(**TOOL_RESPONSE_DATA)


@pytest.mark.asyncio
async def test_async_arcade_tool_get(test_async_client, mock_async_response, monkeypatch):
    """Test AsyncArcade.tools.get method."""

    async def mock_execute_request(*args, **kwargs):
        return TOOL_DEFINITION_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    tool_definition = await test_async_client.tools.get(director_id="default", tool_id="GetEmails")
    assert tool_definition == ToolDefinition(**TOOL_DEFINITION_DATA)


@pytest.mark.asyncio
async def test_async_arcade_tool_authorize(test_async_client, mock_async_response, monkeypatch):
    """Test AsyncArcade.tools.authorize method."""

    async def mock_execute_request(*args, **kwargs):
        return TOOL_AUTHORIZE_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    auth_response = await test_async_client.tools.authorize(
        tool_name="GetEmails", user_id="sam@arcade-ai.com"
    )
    assert auth_response == AuthResponse(**TOOL_AUTHORIZE_RESPONSE_DATA)


@pytest.mark.asyncio
async def test_async_arcade_health_check(test_async_client, mock_async_response, monkeypatch):
    """Test AsyncArcade.health.check method."""

    async def mock_execute_request(*args, **kwargs):
        return HEALTH_CHECK_HEALTHY_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    await test_async_client.health.check()
    assert True  # If no exception is raised, the test passes


@pytest.mark.asyncio
async def test_async_arcade_health_check_raises_error(
    test_async_client, mock_async_response, monkeypatch
):
    """Test AsyncArcade.health.check method."""

    async def mock_execute_request(*args, **kwargs):
        return HEALTH_CHECK_UNHEALTHY_RESPONSE_DATA

    monkeypatch.setattr(AsyncArcade, "_execute_request", mock_execute_request)
    with pytest.raises(EngineNotHealthyError):
        await test_async_client.health.check()
