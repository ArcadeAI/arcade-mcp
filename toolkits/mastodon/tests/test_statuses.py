from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_mastodon.tools.statuses import (
    delete_status_by_id,
    lookup_status_by_id,
    post_status,
    search_recent_statuses_by_keywords,
    search_recent_statuses_by_username,
)

full_status_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed non interdum dolor. Pellentesque augue mauris, venenatis dapibus massa eget,
elementum rutrum ex. Donec et purus egestas, pharetra odio rhoncus, feugiat dolor.
Cras sollicitudin, enim sit amet sagittis consequat, metus mauris blandit neque, eu
finibus leo velit a lacus. Curabitur a justo lorem. Integer iaculis feugiat ex sed imperdiet.
Cras feugiat ut justo quis venenatis. Pellentesque efficitur sit amet enim quis facilisis.
Proin malesuada mollis purus, eu tempus sem venenatis a.
Vestibulum convallis tortor ac elementum gravida.
Sed arcu massa, dictum ac suscipit id, pretium non nulla. Aenean lorem urna, convallis nec elit non,
ehoncus sollicitudin eros. Vestibulum eget dolor consectetur, tempor orci quis, elementum neque.
Aenean quis consectetur justo, vitae faucibus velit. Proin ex metus, lacinia sit amet lorem et,
posuere facilisis nunc. Donec ut viverra sem, ac iaculis neque.

Morbi blandit ante ut tellus varius fringilla. Quisque eget felis non tellus
lobortis congue. Praesent eu malesuada est. Morbi dui dolor, vehicula non est eu,
dapibus pellentesque sapien. In hac habitasse platea dictumst. Praesent ac est scelerisque,
tristique magna et, viverra nunc. Nunc accumsan magna nec felis varius, ut iaculis velit dapibus.
Aenean sit amet porttitor leo."""

truncated_status_text = full_status_text[:500]


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

fake_status_response = {
    "account": fake_account,
    "application": {"name": "Test Application", "website": "https://example.com"},
    "bookmarked": False,
    "card": None,
    "content": "<p>This is a test status</p>",
    "created_at": "2025-06-30T14:53:12.499Z",
    "edited_at": None,
    "emojis": [],
    "favourited": False,
    "favourites_count": 0,
    "filtered": [],
    "id": "1234567890",
    "in_reply_to_account_id": None,
    "in_reply_to_id": None,
    "language": "en",
    "media_attachments": [],
    "mentions": [],
    "muted": False,
    "pinned": False,
    "poll": None,
    "quote": None,
    "reblog": None,
    "reblogged": False,
    "reblogs_count": 0,
    "replies_count": 0,
    "sensitive": False,
    "spoiler_text": "",
    "tags": [],
    "uri": "https://example.com/users/testuser/statuses/1234567890",
    "url": "https://example.com/@testuser/1234567890",
    "visibility": "public",
}


fake_parsed_status = {
    "account_display_name": "Test User",
    "account_id": "0987654321",
    "account_username": "testuser",
    "content": "<p>This is a test status</p>",
    "created_at": "2025-06-30T14:53:12.499Z",
    "favourites_count": 0,
    "id": "1234567890",
    "media_attachments": [],
    "tags": [],
    "url": "https://example.com/@testuser/1234567890",
}


@pytest.mark.asyncio
async def test_post_status_success(
    tool_context,
    httpx_mock,
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_status_response
    httpx_mock.post.return_value = mock_response

    status = "Hello, world!"
    result = await post_status(
        context=tool_context,
        status=status,
    )

    assert result == fake_parsed_status
    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_delete_status_by_id_success(
    tool_context,
    httpx_mock,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_status_response
    httpx_mock.delete.return_value = mock_response

    status_id = "1234567890"
    result = await delete_status_by_id(
        context=tool_context,
        status_id=status_id,
    )

    assert result == fake_parsed_status
    httpx_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_status_by_id_failure(
    tool_context,
    httpx_mock,
):
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    httpx_mock.delete.side_effect = mock_response

    status_id = "1234567890"
    with pytest.raises(ToolExecutionError):
        await delete_status_by_id(
            context=tool_context,
            status_id=status_id,
        )

    httpx_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_statuses_by_username_success(
    tool_context,
    httpx_mock,
    mock_lookup_single_user_by_username,
):
    mock_lookup_single_user_by_username.return_value = {"account": fake_account}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [fake_status_response] * 5
    httpx_mock.get.return_value = mock_response

    username = "testuser"
    result = await search_recent_statuses_by_username(
        context=tool_context,
        username=username,
    )

    assert "statuses" in result
    assert len(result["statuses"]) == 5
    assert result["statuses"][0]["content"] == fake_parsed_status["content"]
    httpx_mock.get.assert_called_once()
    mock_lookup_single_user_by_username.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_statuses_by_username_no_statuses_found(
    tool_context,
    httpx_mock,
    mock_lookup_single_user_by_username,
):
    mock_lookup_single_user_by_username.return_value = {"account": fake_account}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    httpx_mock.get.return_value = mock_response

    username = "testuser"
    result = await search_recent_statuses_by_username(
        context=tool_context,
        username=username,
    )

    assert "statuses" in result
    assert len(result["statuses"]) == 0
    httpx_mock.get.assert_called_once()
    mock_lookup_single_user_by_username.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_statuses_by_username_failure(
    tool_context,
    httpx_mock,
    mock_lookup_single_user_by_username,
):
    mock_lookup_single_user_by_username.return_value = {"account": None}
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    httpx_mock.get.side_effect = mock_response

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await search_recent_statuses_by_username(
            context=tool_context,
            username=username,
        )

    httpx_mock.get.assert_not_called()
    mock_lookup_single_user_by_username.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_statuses_by_keywords_success(
    tool_context,
    httpx_mock,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [fake_status_response] * 5
    httpx_mock.get.return_value = mock_response

    keywords = ["test", "keyword"]
    phrases = ["test phrase"]
    result = await search_recent_statuses_by_keywords(
        context=tool_context,
        keywords=keywords,
        phrases=phrases,
    )

    assert "statuses" in result
    assert len(result["statuses"]) == 5
    assert result["statuses"][0]["content"] == fake_parsed_status["content"]
    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_statuses_by_keywords_no_keywords_or_phrases(
    tool_context,
    httpx_mock,
):
    with pytest.raises(RetryableToolError):
        await search_recent_statuses_by_keywords(
            context=tool_context,
        )

    httpx_mock.get.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_status_by_id_success(
    tool_context,
    httpx_mock,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_status_response
    httpx_mock.get.return_value = mock_response

    status_id = "1234567890"
    result = await lookup_status_by_id(
        context=tool_context,
        status_id=status_id,
    )

    assert result == fake_parsed_status
    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_status_by_id_failure(
    tool_context,
    httpx_mock,
):
    mock_response = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    httpx_mock.get.side_effect = mock_response

    status_id = "1234567890"
    with pytest.raises(ToolExecutionError):
        await lookup_status_by_id(
            context=tool_context,
            status_id=status_id,
        )

    httpx_mock.get.assert_called_once()
