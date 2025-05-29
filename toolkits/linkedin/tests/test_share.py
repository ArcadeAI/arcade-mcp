from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_linkedin.tools.share import create_text_post


@pytest.mark.asyncio
async def test_create_text_post_success(tool_context, mock_httpx_client):
    """Test successful creation of a LinkedIn text post."""
    # Mock response for a successful post creation
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "1234567890"}
    # Ensure the mock is awaited properly
    mock_httpx_client.request = AsyncMock(return_value=mock_response)

    post_text = "Hello, LinkedIn!"
    result = await create_text_post(tool_context, post_text)

    expected_url = "https://www.linkedin.com/feed/update/1234567890/"
    assert result == expected_url
    mock_httpx_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_create_text_post_no_user_id(tool_context):
    """Test error when user ID is not found in the context."""
    # Simulate missing user ID in the context
    tool_context.authorization.user_info = {}

    post_text = "Hello, LinkedIn!"
    with pytest.raises(ToolExecutionError, match="User ID not found"):
        await create_text_post(tool_context, post_text)
