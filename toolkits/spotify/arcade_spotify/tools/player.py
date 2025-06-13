from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Spotify
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_spotify.tools.constants import RESPONSE_MSGS
from arcade_spotify.tools.models import Device, SearchType
from arcade_spotify.tools.search import search
from arcade_spotify.tools.utils import (
    convert_to_playback_state,
    get_url,
    send_spotify_request,
)


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def adjust_playback_position(
    context: ToolContext,
    absolute_position_ms: Annotated[
        int | None, "The absolute position in milliseconds to seek to"
    ] = None,
    relative_position_ms: Annotated[
        int | None,
        "The relative position from the current playback position in milliseconds to seek to",
    ] = None,
) -> Annotated[str, "Success/failure message"]:
    """Adjust the playback position within the currently playing track.

    Knowledge of the current playback state is NOT needed to use this tool as it handles
    clamping the position to valid start/end boundaries to prevent overshooting or negative values.

    This tool allows you to seek to a specific position within the currently playing track.
    You can either provide an absolute position in milliseconds or a relative position from
    the current playback position in milliseconds.

    Note:
        Either absolute_position_ms or relative_position_ms must be provided, but not both.
    """
    if (absolute_position_ms is None) == (relative_position_ms is None):
        raise RetryableToolError(
            "Either absolute_position_ms or relative_position_ms must be provided, but not both",
            additional_prompt_content=(
                "Provide a value for either absolute_position_ms or "
                "relative_position_ms, but not both."
            ),
            retry_after_ms=500,
        )

    if relative_position_ms is not None:
        playback_state = await get_playback_state(context)
        if playback_state.get("device_id") is None:
            return RESPONSE_MSGS["no_track_to_adjust_position"]

        absolute_position_ms = playback_state["progress_ms"] + relative_position_ms

    absolute_position_ms = max(0, absolute_position_ms or 0)

    url = get_url("player_seek_to_position")
    params = {"position_ms": absolute_position_ms}

    try:
        response = await send_spotify_request(context, "PUT", url, params=params)
    except httpx.HTTPStatusError as e:
        raise ToolExecutionError(f"Failed to adjust playback position: {e}") from e

    if response.status_code == 404:
        return RESPONSE_MSGS["no_track_to_adjust_position"]

    response.raise_for_status()

    return RESPONSE_MSGS["playback_position_adjusted"]


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def skip_to_previous_track(
    context: ToolContext,
) -> Annotated[str, "Success/failure message"]:
    """Skip to the previous track in the user's queue, if any"""
    url = get_url("player_skip_to_previous")

    response = await send_spotify_request(context, "POST", url)

    if response.status_code == 404:
        return RESPONSE_MSGS["no_track_to_go_back_to"]

    response.raise_for_status()

    return RESPONSE_MSGS["playback_skipped_to_previous_track"]


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def skip_to_next_track(
    context: ToolContext,
) -> Annotated[str, "Success/failure message"]:
    """Skip to the next track in the user's queue, if any"""
    url = get_url("player_skip_to_next")

    response = await send_spotify_request(context, "POST", url)

    if response.status_code == 404:
        return RESPONSE_MSGS["no_track_to_skip"]

    response.raise_for_status()

    return RESPONSE_MSGS["playback_skipped_to_next_track"]


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def pause_playback(
    context: ToolContext,
) -> Annotated[str, "Success/failure message"]:
    """Pause the currently playing track, if any"""
    playback_state = await get_playback_state(context)

    # There is no current state, therefore nothing to pause
    if playback_state.get("device_id") is None:
        return RESPONSE_MSGS["no_track_to_pause"]
    # Track is already paused
    if playback_state.get("is_playing") is False:
        return RESPONSE_MSGS["track_is_already_paused"]

    url = get_url("player_pause_playback")

    response = await send_spotify_request(context, "PUT", url)
    response.raise_for_status()

    return RESPONSE_MSGS["playback_paused"]


# NOTE: This tool only works for Spotify Premium users
@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
)
async def resume_playback(
    context: ToolContext,
) -> Annotated[str, "Success/failure message"]:
    """Resume the currently playing track, if any"""
    playback_state = await get_playback_state(context)

    # There is no current state, therefore nothing to resume
    if playback_state.get("device_id") is None:
        return RESPONSE_MSGS["no_track_to_resume"]
    # Track is already playing
    if playback_state.get("is_playing") is True:
        return RESPONSE_MSGS["track_is_already_playing"]

    url = get_url("player_modify_playback")

    response = await send_spotify_request(context, "PUT", url)
    response.raise_for_status()

    return RESPONSE_MSGS["playback_resumed"]


# NOTE: This tool only works for Spotify Premium users
@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
)
async def start_tracks_playback_by_id(
    context: ToolContext,
    track_ids: Annotated[
        list[str],
        "A list of Spotify track (song) IDs to play. Order of execution is not guarenteed.",
    ],
    position_ms: Annotated[
        int | None,
        "The position in milliseconds to start the first track from",
    ] = 0,
) -> Annotated[str, "Success/failure message"]:
    """Start playback of a list of tracks (songs)"""

    devices = [
        Device(**device) for device in (await get_available_devices(context)).get("devices", [])
    ]

    # If no active device is available, pick the first one.
    # Otherwise, Spotify defaults to the active device.
    device_id = None
    if devices and not any(device.is_active for device in devices):
        device_id = devices[0].id

    params = {"device_id": device_id} if device_id else {}

    url = get_url("player_modify_playback")
    body = {
        "uris": [f"spotify:track:{track_id}" for track_id in track_ids],
        "position_ms": position_ms,
    }

    response = await send_spotify_request(context, "PUT", url, params=params, json_data=body)

    if response.status_code == 404:
        return RESPONSE_MSGS["no_active_device"]

    response.raise_for_status()

    return RESPONSE_MSGS["playback_started"]


@tool(requires_auth=Spotify(scopes=["user-read-playback-state"]))
async def get_playback_state(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's current playback state"]:
    """
    Get information about the user's current playback state,
    including track or episode, and active device.
    This tool does not perform any actions. Use other tools to control playback.
    """
    url = get_url("player_get_playback_state")
    response = await send_spotify_request(context, "GET", url)
    response.raise_for_status()
    data = {"is_playing": False} if response.status_code == 204 else response.json()
    return convert_to_playback_state(data).to_dict()


@tool(requires_auth=Spotify(scopes=["user-read-currently-playing"]))
async def get_currently_playing(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's currently playing track"]:
    """Get information about the user's currently playing track"""
    url = get_url("player_get_currently_playing")
    response = await send_spotify_request(context, "GET", url)
    response.raise_for_status()
    data = {"is_playing": False} if response.status_code == 204 else response.json()
    return convert_to_playback_state(data).to_dict()


# NOTE: This tool only works for Spotify Premium users
@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
)
async def play_artist_by_name(
    context: ToolContext,
    name: Annotated[str, "The name of the artist to play"],
) -> Annotated[str, "Success/failure message"]:
    """Plays a song by an artist and queues four more songs by the same artist"""
    q = f"artist:{name}"
    search_results = await search(context, q, [SearchType.TRACK], 5)
    if not search_results["tracks"]["items"]:
        message = RESPONSE_MSGS["artist_not_found"].format(artist_name=name)
        raise RetryableToolError(
            message,
            additional_prompt_content=f"{message} Try a different artist name.",
            retry_after_ms=500,
        )
    track_ids = [item["id"] for item in search_results["tracks"]["items"]]
    response = await start_tracks_playback_by_id(context, track_ids)

    return str(response)


# NOTE: This tool only works for Spotify Premium users
@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
)
async def play_track_by_name(
    context: ToolContext,
    track_name: Annotated[str, "The name of the track to play"],
    artist_name: Annotated[str | None, "The name of the artist of the track"] = None,
) -> Annotated[str, "Success/failure message"]:
    """Plays a song by name"""
    q = f"track:{track_name}"
    if artist_name:
        q += f" artist:{artist_name}"
    search_results = await search(context, q, [SearchType.TRACK], 1)

    if not search_results["tracks"]["items"]:
        message = RESPONSE_MSGS["track_not_found"].format(track_name=track_name)
        if artist_name:
            message += f" by '{artist_name}'"
        raise RetryableToolError(
            message,
            additional_prompt_content=f"{message}. Try a different track name or artist name.",
            retry_after_ms=500,
        )

    track_id = search_results["tracks"]["items"][0]["id"]
    response = await start_tracks_playback_by_id(context, [track_id])

    return str(response)


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state"]))
async def get_available_devices(
    context: ToolContext,
) -> Annotated[dict, "The available devices"]:
    """Get the available devices"""
    url = get_url("player_get_available_devices")
    response = await send_spotify_request(context, "GET", url)
    response.raise_for_status()
    return dict(response.json())
