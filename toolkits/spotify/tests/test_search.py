from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_spotify.tools.models import SearchType
from arcade_spotify.tools.search import search
from arcade_spotify.tools.utils import get_url


@pytest.mark.asyncio
async def test_search_success(tool_context, mock_httpx_client, sample_track):
    sample_tracks = []
    for i in range(4):
        sample_track = sample_track.copy()
        sample_track["id"] = f"{i}"
        sample_tracks.append(sample_track)

    search_response = {
        "tracks": {
            "href": "https://api.spotify.com/v1/me/shows?offset=0&limit=20",
            "limit": 20,
            "next": "https://api.spotify.com/v1/me/shows?offset=1&limit=1",
            "offset": 0,
            "previous": "https://api.spotify.com/v1/me/shows?offset=1&limit=1",
            "total": 4,
            "items": sample_tracks,
        },
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = search_response
    mock_httpx_client.request.return_value = mock_response

    result = await search(tool_context, "test", [SearchType.TRACK], 4)

    assert result == search_response

    mock_httpx_client.request.assert_called_once_with(
        "GET",
        get_url("search", q="test"),
        headers={"Authorization": f"Bearer {tool_context.authorization.token}"},
        params={"q": "test", "type": SearchType.TRACK.value, "limit": 4},
        json=None,
    )


@pytest.mark.asyncio
async def test_search_rate_limit_error(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response = httpx.HTTPStatusError(
        "Too Many Requests", request=MagicMock(), response=MagicMock(status_code=429)
    )
    mock_httpx_client.request.side_effect = mock_response

    with pytest.raises(ToolExecutionError):
        await search(tool_context, "test", [SearchType.TRACK], 4)
