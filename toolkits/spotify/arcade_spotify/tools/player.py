from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Spotify
from arcade_spotify.tools.utils import (
    convert_to_playback_state,
    get_url,
    handle_spotify_response,
    send_spotify_request,
)


@tool(requires_auth=Spotify(scopes=["user-read-playback-state", "user-modify-playback-state"]))
async def pause_playback(
    context: ToolContext,
) -> Annotated[dict, "The updated playback state"]:
    """Pause the currently playing track"""
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
    handle_spotify_response(response, url)

    playback_state["is_playing"] = False
    return playback_state


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
    handle_spotify_response(response, url)

    playback_state["is_playing"] = True
    return playback_state


@tool(requires_auth=Spotify(scopes=["user-read-playback-state"]))
async def get_playback_state(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's current playback state"]:
    """
    Get information about the user's current playback state, including track or episode, progress, and active device.
    """
    url = get_url("player_get_playback_state")
    response = await send_spotify_request(context, "GET", url)
    handle_spotify_response(response, url)
    data = {"is_playing": False} if response.status_code == 204 else response.json()
    return convert_to_playback_state(data).to_dict()
