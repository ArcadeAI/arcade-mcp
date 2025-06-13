from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_x.tools.users import lookup_single_user_by_username


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_success(tool_context, mock_httpx_client):
    """Test successful lookup of a user by username."""
    # Mock response for a successful user lookup
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "id": "1234567890",
            "name": "Test User",
            "username": "testuser",
            "description": "This is a test user",
            # Additional fields can be added here as needed
        }
    }
    mock_httpx_client.get.return_value = mock_response

    username = "testuser"
    result = await lookup_single_user_by_username(tool_context, username)

    assert "data" in result
    assert result["data"]["username"] == "testuser"
    assert result["data"]["name"] == "Test User"
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_user_not_found(tool_context, mock_httpx_client):
    """Test behavior when looking up user fails due to API error"""
    # Mock response for user not found
    mock_response = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
    )
    mock_httpx_client.get.side_effect = mock_response

    username = "nonexistentuser"
    with pytest.raises(ToolExecutionError):
        await lookup_single_user_by_username(tool_context, username)

    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_api_error(tool_context, mock_httpx_client):
    """Test behavior when API returns an error other than 404."""
    # Mock response for API error
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )
    mock_httpx_client.get.side_effect = mock_response

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await lookup_single_user_by_username(tool_context, username)

    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_network_error(tool_context, mock_httpx_client):
    """Test behavior when there is a network error during the request."""
    # Mock client.get to raise an HTTPError
    mock_httpx_client.get.side_effect = httpx.HTTPError("Network Error")

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await lookup_single_user_by_username(tool_context, username)

    mock_httpx_client.get.assert_called_once()
