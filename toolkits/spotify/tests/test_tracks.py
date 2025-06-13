from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_spotify.tools.tracks import get_track_from_id
from arcade_spotify.tools.utils import get_url


@pytest.mark.asyncio
async def test_get_track_from_id_success(tool_context, mock_httpx_client, sample_track):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_track
    mock_httpx_client.request.return_value = mock_response

    result = await get_track_from_id(tool_context, "1234567890")

    assert result == sample_track

    mock_httpx_client.request.assert_called_once_with(
        "GET",
        get_url("tracks_get_track", track_id="1234567890"),
        headers={"Authorization": f"Bearer {tool_context.authorization.token}"},
        params=None,
        json=None,
    )


@pytest.mark.asyncio
async def test_get_track_from_id_rate_limit_error(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response = httpx.HTTPStatusError(
        "Too Many Requests", request=MagicMock(), response=MagicMock(status_code=429)
    )
    mock_httpx_client.request.side_effect = mock_response

    with pytest.raises(ToolExecutionError):
        await get_track_from_id(tool_context, "1234567890")
