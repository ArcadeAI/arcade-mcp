from unittest.mock import AsyncMock, patch

import pytest

from {{ package_name }}.tools.sample import RedditUserProfile, get_my_reddit_profile


@pytest.mark.asyncio
async def test_get_my_reddit_profile(mock_context) -> None:
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "name": "test_user",
        "comment_karma": 100,
        "link_karma": 200,
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("{{ package_name }}.tools.sample.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        result = await get_my_reddit_profile(mock_context)

    assert result == RedditUserProfile(
        username="test_user",
        comment_karma=100,
        link_karma=200,
    )
