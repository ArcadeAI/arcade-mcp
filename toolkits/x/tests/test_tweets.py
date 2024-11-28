from unittest.mock import MagicMock

import httpx
import pytest
from arcade.sdk.errors import RetryableToolError, ToolExecutionError

from arcade_x.tools.tweets import (
    delete_tweet_by_id,
    lookup_tweet_by_id,
    post_tweet,
    search_recent_tweets_by_keywords,
    search_recent_tweets_by_username,
)
from arcade_x.tools.utils import get_tweet_url


@pytest.mark.asyncio
async def test_post_tweet_success(tool_context, mock_httpx_client):
    """Test successful posting of a tweet."""
    # Mock response for a successful tweet post
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"data": {"id": "1234567890"}}
    mock_httpx_client.post.return_value = mock_response

    tweet_text = "Hello, world!"
    result = await post_tweet(tool_context, tweet_text)

    expected_url = get_tweet_url("1234567890")
    assert result == f"Tweet with id 1234567890 posted successfully. URL: {expected_url}"
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_post_tweet_failure(tool_context, mock_httpx_client):
    """Test failure when posting a tweet due to API error."""
    # Mock response for a failed tweet post
    mock_response = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400)
    )
    mock_httpx_client.post.side_effect = mock_response

    tweet_text = "Hello, world!"
    with pytest.raises(ToolExecutionError):
        await post_tweet(tool_context, tweet_text)

    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_delete_tweet_by_id_success(tool_context, mock_httpx_client):
    """Test successful deletion of a tweet by ID."""
    # Mock response for a successful tweet deletion
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.delete.return_value = mock_response

    tweet_id = "1234567890"
    result = await delete_tweet_by_id(tool_context, tweet_id)

    assert result == f"Tweet with id {tweet_id} deleted successfully."
    mock_httpx_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_tweet_by_id_failure(tool_context, mock_httpx_client):
    """Test failure when deleting a tweet due to API error."""
    # Mock response for a failed tweet deletion
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=404)
    )
    mock_httpx_client.delete.side_effect = mock_response

    tweet_id = "1234567890"
    with pytest.raises(ToolExecutionError):
        await delete_tweet_by_id(tool_context, tweet_id)

    mock_httpx_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_tweets_by_username_success(tool_context, mock_httpx_client):
    """Test successful search of recent tweets by username."""
    # Mock response for a successful tweet search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "id": "1234567890",
                "text": "Test tweet",
                "entities": {
                    "urls": [
                        {"url": "https://t.co/short", "expanded_url": "https://example.com/long"}
                    ]
                },
            }
        ],
        "includes": {"users": [{"id": "0987654321", "name": "Test User", "username": "testuser"}]},
    }
    mock_httpx_client.get.return_value = mock_response

    username = "testuser"
    result = await search_recent_tweets_by_username(tool_context, username)

    assert "data" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["text"] == "Test tweet"
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_tweets_by_username_failure(tool_context, mock_httpx_client):
    """Test failure when searching tweets due to API error."""
    # Mock response for a failed tweet search
    mock_response = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )
    mock_httpx_client.get.side_effect = mock_response

    username = "testuser"
    with pytest.raises(ToolExecutionError):
        await search_recent_tweets_by_username(tool_context, username)

    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_tweets_by_keywords_success(tool_context, mock_httpx_client):
    """Test successful search of recent tweets by keywords."""
    # Mock response for a successful keyword search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"id": "1234567890", "text": "Keyword tweet", "entities": {}}],
        "includes": {"users": [{"id": "0987654321", "name": "Test User", "username": "testuser"}]},
    }
    mock_httpx_client.get.return_value = mock_response

    keywords = ["test", "keyword"]
    result = await search_recent_tweets_by_keywords(tool_context, keywords=keywords)

    assert "data" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["text"] == "Keyword tweet"
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_recent_tweets_by_keywords_no_input(tool_context):
    """Test error when no keywords or phrases are provided."""
    with pytest.raises(RetryableToolError) as exc_info:
        await search_recent_tweets_by_keywords(tool_context)

    assert "No keywords or phrases provided" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lookup_tweet_by_id_success(tool_context, mock_httpx_client):
    """Test successful lookup of a tweet by ID."""
    # Use MagicMock for the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"id": "1234567890", "text": "Lookup tweet", "entities": {}}
    }
    mock_httpx_client.get.return_value = mock_response

    tweet_id = "1234567890"
    result = await lookup_tweet_by_id(tool_context, tweet_id)

    assert "data" in result
    assert result["data"]["text"] == "Lookup tweet"
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_tweet_by_id_failure(tool_context, mock_httpx_client):
    """Test failure when looking up a tweet due to API error."""
    # Mock response for a failed tweet lookup
    mock_response = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
    )
    mock_httpx_client.get.side_effect = mock_response

    tweet_id = "1234567890"
    with pytest.raises(ToolExecutionError):
        await lookup_tweet_by_id(tool_context, tweet_id)

    mock_httpx_client.get.assert_called_once()
