from unittest.mock import MagicMock, patch

import httpx
import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_spotify.tools.constants import RESPONSE_MSGS
from arcade_spotify.tools.models import SearchType
from arcade_spotify.tools.player import (
    adjust_playback_position,
    get_available_devices,
    get_currently_playing,
    get_playback_state,
    pause_playback,
    play_artist_by_name,
    play_track_by_name,
    resume_playback,
    skip_to_next_track,
    skip_to_previous_track,
    start_tracks_playback_by_id,
)
from arcade_spotify.tools.utils import get_url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, tool_kwargs",
    [
        (adjust_playback_position, {"absolute_position_ms": 10000}),
        (get_available_devices, {}),
        (get_currently_playing, {}),
        (get_playback_state, {}),
        (pause_playback, {}),
        (resume_playback, {}),
        (start_tracks_playback_by_id, {"track_ids": ["1234567890"], "position_ms": 10000}),
        (skip_to_previous_track, {}),
        (skip_to_next_track, {}),
    ],
)
async def test_too_many_requests_http_error(
    tool_function, tool_kwargs, tool_context, mock_httpx_client
):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Too Many Requests", request=MagicMock(), response=MagicMock(status_code=429)
    )
    mock_httpx_client.request.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await tool_function(context=tool_context, **tool_kwargs)


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_adjust_playback_position_absolute_success(
    mock_get_playback_state, tool_context, mock_httpx_client
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await adjust_playback_position(context=tool_context, absolute_position_ms=10000)

    assert response == RESPONSE_MSGS["playback_position_adjusted"]

    mock_get_playback_state.assert_not_called()
    mock_httpx_client.request.assert_called_once_with(
        "PUT",
        get_url("player_seek_to_position"),
        headers={"Authorization": f"Bearer {tool_context.authorization.token}"},
        params={"position_ms": 10000},
        json=None,
    )


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_adjust_playback_position_relative_success(
    mock_get_playback_state, tool_context, mock_httpx_client
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    mock_get_playback_state.return_value = {"device_id": "1234567890", "progress_ms": 10000}
    response = await adjust_playback_position(context=tool_context, relative_position_ms=10000)

    assert response == RESPONSE_MSGS["playback_position_adjusted"]

    mock_get_playback_state.assert_called_once_with(tool_context)
    mock_httpx_client.request.assert_called_once_with(
        "PUT",
        get_url("player_seek_to_position"),
        headers={"Authorization": f"Bearer {tool_context.authorization.token}"},
        params={"position_ms": 20000},
        json=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, tool_kwargs",
    [
        # Both arguments provided
        (
            adjust_playback_position,
            {"absolute_position_ms": 10000, "relative_position_ms": 10000},
        ),
        # No arguments provided
        (
            adjust_playback_position,
            {},
        ),
    ],
)
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_adjust_playback_position_wrong_arguments_error(
    mock_get_playback_state, tool_context, mock_httpx_client, tool_function, tool_kwargs
):
    with pytest.raises(RetryableToolError):
        await tool_function(context=tool_context, **tool_kwargs)

    mock_get_playback_state.assert_not_called()
    mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_adjust_playback_position_no_device_error(
    mock_get_playback_state, tool_context, mock_httpx_client
):
    mock_get_playback_state.return_value = {"device_id": None}

    response = await adjust_playback_position(context=tool_context, relative_position_ms=10000)

    assert response == RESPONSE_MSGS["no_track_to_adjust_position"]

    mock_get_playback_state.assert_called_once_with(tool_context)
    mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_adjust_playback_position_not_found_error(
    mock_get_playback_state, tool_context, mock_httpx_client
):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx_client.request.return_value = mock_response

    response = await adjust_playback_position(context=tool_context, absolute_position_ms=10000)

    assert response == RESPONSE_MSGS["no_track_to_adjust_position"]

    mock_get_playback_state.assert_not_called()
    mock_httpx_client.request.assert_called_once_with(
        "PUT",
        get_url("player_seek_to_position"),
        headers={"Authorization": f"Bearer {tool_context.authorization.token}"},
        params={"position_ms": 10000},
        json=None,
    )


@pytest.mark.asyncio
async def test_skip_to_previous_track_success(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await skip_to_previous_track(context=tool_context)

    assert response == RESPONSE_MSGS["playback_skipped_to_previous_track"]


@pytest.mark.asyncio
async def test_skip_to_previous_track_not_found_error(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx_client.request.return_value = mock_response

    response = await skip_to_previous_track(context=tool_context)

    assert response == RESPONSE_MSGS["no_track_to_go_back_to"]


@pytest.mark.asyncio
async def test_skip_to_next_track_success(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await skip_to_next_track(context=tool_context)

    assert response == RESPONSE_MSGS["playback_skipped_to_next_track"]


@pytest.mark.asyncio
async def test_skip_to_next_track_not_found_error(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx_client.request.return_value = mock_response

    response = await skip_to_next_track(context=tool_context)

    assert response == RESPONSE_MSGS["no_track_to_skip"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, mock_is_playing, expected_message",
    [
        (pause_playback, True, RESPONSE_MSGS["playback_paused"]),
        (resume_playback, False, RESPONSE_MSGS["playback_resumed"]),
    ],
)
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_change_playback_state_success(
    mock_get_playback_state,
    tool_context,
    tool_function,
    mock_is_playing,
    expected_message,
    mock_httpx_client,
):
    mock_get_playback_state.return_value = {
        "device_id": "1234567890",
        "is_playing": mock_is_playing,
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await tool_function(context=tool_context)
    assert response == expected_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, expected_message",
    [
        (pause_playback, RESPONSE_MSGS["no_track_to_pause"]),
        (resume_playback, RESPONSE_MSGS["no_track_to_resume"]),
    ],
)
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_change_playback_state_no_device_running(
    mock_get_playback_state, tool_context, tool_function, expected_message, mock_httpx_client
):
    mock_get_playback_state.return_value = {"device_id": None}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await tool_function(context=tool_context)
    assert response == expected_message
    mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, mock_is_playing, expected_message",
    [
        (pause_playback, False, RESPONSE_MSGS["track_is_already_paused"]),
        (resume_playback, True, RESPONSE_MSGS["track_is_already_playing"]),
    ],
)
@patch("arcade_spotify.tools.player.get_playback_state")
async def test_change_playback_state_already_set_success(
    mock_get_playback_state,
    tool_context,
    tool_function,
    mock_is_playing,
    expected_message,
    mock_httpx_client,
):
    mock_get_playback_state.return_value = {
        "device_id": "1234567890",
        "is_playing": mock_is_playing,
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await tool_function(context=tool_context)
    assert response == expected_message
    mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_available_devices")
async def test_start_tracks_playback_by_id_success(
    mock_get_available_devices, tool_context, mock_httpx_client
):
    mock_get_available_devices.return_value = {
        "devices": [
            {
                "id": "1234567890",
                "is_active": True,
                "name": "Test Device",
                "type": "Computer",
                "is_private_session": False,
                "is_restricted": False,
                "supports_volume": True,
                "volume_percent": 100,
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await start_tracks_playback_by_id(
        context=tool_context, track_ids=["1234567890"], position_ms=10000
    )
    assert response == RESPONSE_MSGS["playback_started"]


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.get_available_devices")
async def test_start_tracks_playback_by_id_no_active_device(
    mock_get_available_devices, tool_context, mock_httpx_client
):
    mock_get_available_devices.return_value = {"devices": []}
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx_client.request.return_value = mock_response

    response = await start_tracks_playback_by_id(
        context=tool_context, track_ids=["1234567890"], position_ms=10000
    )
    assert response == RESPONSE_MSGS["no_active_device"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, expected_message",
    [
        (get_playback_state, RESPONSE_MSGS["playback_started"]),
        (get_currently_playing, RESPONSE_MSGS["playback_started"]),
    ],
)
async def test_get_state_success(
    tool_context,
    mock_httpx_client,
    tool_function,
    expected_message,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "device": {
            "id": "1234567890",
            "is_active": True,
            "name": "Test Device",
            "type": "Computer",
        },
        "currently_playing_type": "track",
        "is_playing": True,
        "progress_ms": 10000,
        "message": "Playback started",
    }
    mock_httpx_client.request.return_value = mock_response

    response = await tool_function(context=tool_context)

    assert response["device_id"] == "1234567890"
    assert response["device_name"] == "Test Device"
    assert response["is_playing"] is True
    assert response["progress_ms"] == 10000
    assert response["message"] == "Playback started"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function",
    [get_playback_state, get_currently_playing],
)
async def test_get_state_playback_not_active(tool_context, mock_httpx_client, tool_function):
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_httpx_client.request.return_value = mock_response

    response = await tool_function(context=tool_context)

    assert response["is_playing"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, tool_kwargs, expected_search_query, expected_limit",
    [
        (play_artist_by_name, {"name": "Test Artist"}, "artist:Test Artist", 5),
        (play_track_by_name, {"track_name": "Test Track"}, "track:Test Track", 1),
    ],
)
@patch("arcade_spotify.tools.player.start_tracks_playback_by_id")
@patch("arcade_spotify.tools.player.search")
async def test_play_by_name_success(
    mock_search,
    mock_start_tracks_playback_by_id,
    tool_context,
    tool_function,
    tool_kwargs,
    expected_search_query,
    expected_limit,
    mock_httpx_client,
):
    track_id = "1234567890"
    mock_search.return_value = {"tracks": {"items": [{"id": track_id, "name": "Test Track"}]}}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    mock_start_tracks_playback_by_id.return_value = RESPONSE_MSGS["playback_started"]

    response = await tool_function(context=tool_context, **tool_kwargs)

    assert response == RESPONSE_MSGS["playback_started"]

    mock_search.assert_called_once_with(
        tool_context,
        expected_search_query,
        [SearchType.TRACK],
        expected_limit,
    )
    mock_start_tracks_playback_by_id.assert_called_once_with(tool_context, [track_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, tool_kwargs, expected_search_query, expected_limit, expected_message",
    [
        (
            play_artist_by_name,
            {"name": "Test Artist"},
            "artist:Test Artist",
            5,
            RESPONSE_MSGS["artist_not_found"].format(artist_name="Test Artist"),
        ),
        (
            play_track_by_name,
            {"track_name": "Test Track"},
            "track:Test Track",
            1,
            RESPONSE_MSGS["track_not_found"].format(track_name="Test Track"),
        ),
    ],
)
@patch("arcade_spotify.tools.player.start_tracks_playback_by_id")
@patch("arcade_spotify.tools.player.search")
async def test_play_by_name_no_tracks_found(
    mock_search,
    mock_start_tracks_playback_by_id,
    tool_context,
    tool_function,
    tool_kwargs,
    expected_search_query,
    expected_limit,
    expected_message,
    mock_httpx_client,
):
    mock_search.return_value = {"tracks": {"items": []}}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    mock_start_tracks_playback_by_id.return_value = RESPONSE_MSGS["playback_started"]

    with pytest.raises(RetryableToolError) as e:
        await tool_function(context=tool_context, **tool_kwargs)
        assert e.value.message == expected_message

    mock_search.assert_called_once_with(
        tool_context, expected_search_query, [SearchType.TRACK], expected_limit
    )
    mock_start_tracks_playback_by_id.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_spotify.tools.player.start_tracks_playback_by_id")
@patch("arcade_spotify.tools.player.search")
async def test_play_track_by_name_with_artist_success(
    mock_search, mock_start_tracks_playback_by_id, tool_context, mock_httpx_client
):
    track_id = "1234567890"
    mock_search.return_value = {"tracks": {"items": [{"id": track_id, "name": "Test Track"}]}}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await play_track_by_name(
        context=tool_context, track_name="Test Track", artist_name="Test Artist"
    )

    assert response == str(mock_start_tracks_playback_by_id.return_value)

    mock_search.assert_called_once_with(
        tool_context, "track:Test Track artist:Test Artist", [SearchType.TRACK], 1
    )
    mock_start_tracks_playback_by_id.assert_called_once_with(tool_context, [track_id])


@pytest.mark.asyncio
async def test_get_available_devices_success(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "devices": [{"id": "1234567890", "name": "Test Device", "type": "Computer"}]
    }
    mock_httpx_client.request.return_value = mock_response

    response = await get_available_devices(context=tool_context)
    assert response == dict(mock_response.json())
