from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Spotify
from arcade.sdk.errors import RetryableToolError
from arcade_spotify.tools.utils import (
    convert_to_playback_state,
    get_url,
    handle_404_playback_state,
    send_spotify_request,
)


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def adjust_playback_position(
    context: ToolContext,
    absolute_position_ms: Annotated[
        Optional[int], "The absolute position in milliseconds to seek to"
    ] = None,
    relative_position_ms: Annotated[
        Optional[int],
        "The relative position from the current playback position in milliseconds to seek to",
    ] = None,
) -> Annotated[dict, "The updated playback state"]:
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
            additional_prompt_content="Provide a value for either absolute_position_ms or relative_position_ms, but not both.",
            retry_after_ms=500,
        )

    if relative_position_ms is not None:
        playback_state = await get_playback_state(context)
        if playback_state.get("device_id") is None:
            playback_state["message"] = "No track to adjust position"
            return playback_state

        absolute_position_ms = playback_state["progress_ms"] + relative_position_ms

    absolute_position_ms = max(0, absolute_position_ms)

    url = get_url("player_seek_to_position")
    params = {"position_ms": absolute_position_ms}

    response = await send_spotify_request(context, "PUT", url, params=params)

    playback_state = handle_404_playback_state(response, "No track to adjust position", False)
    if playback_state:
        return playback_state

    response.raise_for_status()

    playback_state = await get_playback_state(context)
    return playback_state


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def skip_to_previous_track(
    context: ToolContext,
) -> Annotated[dict, "The updated playback state"]:
    """Skip to the previous track in the user's queue, if any"""
    url = get_url("player_skip_to_previous")

    response = await send_spotify_request(context, "POST", url)

    playback_state = handle_404_playback_state(response, "No track to go back to", False)
    if playback_state:
        return playback_state

    response.raise_for_status()

    playback_state = await get_playback_state(context)

    return playback_state


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def skip_to_next_track(
    context: ToolContext,
) -> Annotated[dict, "The updated playback state"]:
    """Skip to the next track in the user's queue, if any"""
    url = get_url("player_skip_to_next")

    response = await send_spotify_request(context, "POST", url)

    playback_state = handle_404_playback_state(response, "No track to skip", False)
    if playback_state:
        return playback_state

    response.raise_for_status()

    playback_state = await get_playback_state(context)

    return playback_state


# NOTE: This tool only works for Spotify Premium users
@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def pause_playback(
    context: ToolContext,
) -> Annotated[dict, "The updated playback state"]:
    """Pause the currently playing track, if any"""
    playback_state = await get_playback_state(context)

    # There is no current state, therefore nothing to pause
    if playback_state.get("device_id") is None:
        playback_state["message"] = "No track to pause"
        return playback_state
    # Track is already paused
    if playback_state.get("is_playing") is False:
        playback_state["message"] = "Track is already paused"
        return playback_state

    url = get_url("player_pause_playback")

    response = await send_spotify_request(context, "PUT", url)
    response.raise_for_status()

    playback_state["is_playing"] = False
    return playback_state


# NOTE: This tool only works for Spotify Premium users
@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
)
async def resume_playback(
    context: ToolContext,
) -> Annotated[dict, "The updated playback state"]:
    """Resume the currently playing track, if any"""
    playback_state = await get_playback_state(context)

    # There is no current state, therefore nothing to resume
    if playback_state.get("device_id") is None:
        playback_state["message"] = "No track to resume"
        return playback_state
    # Track is already playing
    if playback_state.get("is_playing") is True:
        playback_state["message"] = "Track is already playing"
        return playback_state

    url = get_url("player_modify_playback")

    response = await send_spotify_request(context, "PUT", url)
    response.raise_for_status()

    playback_state["is_playing"] = True
    return playback_state


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
        Optional[int],
        "The position in milliseconds to start the first track from",
    ] = 0,
) -> Annotated[dict, "The updated playback state"]:
    """Start playback of a list of tracks (songs)"""
    url = get_url("player_modify_playback")
    body = {
        "uris": [f"spotify:track:{track_id}" for track_id in track_ids],
        "position_ms": position_ms,
    }

    response = await send_spotify_request(context, "PUT", url, json_data=body)
    response.raise_for_status()

    playback_state = await get_playback_state(context)
    return playback_state


@tool(requires_auth=Spotify(scopes=["user-read-playback-state"]))
async def get_playback_state(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's current playback state"]:
    """
    Get information about the user's current playback state, including track or episode, and active device.
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
