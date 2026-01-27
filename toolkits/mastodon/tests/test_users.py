from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_mastodon.tools.users import lookup_single_user_by_username

fake_account = {
    "acct": "testuser",
    "avatar": "https://files.example.com/image.jpg",
    "avatar_static": "https://files.example.com/image.jpg",
    "bot": False,
    "created_at": "2025-06-27T00:00:00.000Z",
    "discoverable": True,
    "display_name": "Test User",
    "emojis": [],
    "fields": [],
    "followers_count": 0,
    "following_count": 0,
    "group": False,
    "header": "https://example.com/headers/original/missing.png",
    "header_static": "https://example.com/headers/original/missing.png",
    "hide_collections": None,
    "id": "0987654321",
    "indexable": True,
    "last_status_at": "2025-06-30",
    "locked": False,
    "noindex": False,
    "note": "<p>Test account for Arcade</p>",
    "roles": [],
    "statuses_count": 5,
    "uri": "https://example.com/users/testuser",
    "url": "https://example.com/@testuser",
    "username": "testuser",
}


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_success(tool_context, httpx_mock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_account
    httpx_mock.get.return_value = mock_response

    username = "testuser"
    result = await lookup_single_user_by_username(
        context=tool_context,
        username=username,
    )

    assert result == {"account": fake_account}
    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_user_not_found(tool_context, httpx_mock):
    mock_response = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    httpx_mock.get.side_effect = mock_response

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await lookup_single_user_by_username(
            context=tool_context,
            username=username,
        )

    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_single_user_by_username_failure(tool_context, httpx_mock):
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    httpx_mock.get.side_effect = mock_response

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await lookup_single_user_by_username(
            context=tool_context,
            username=username,
        )

    httpx_mock.get.assert_called_once()
