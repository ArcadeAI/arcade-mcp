from typing import Annotated, Optional

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(
        provider_id="spotify",
        scopes=["user-modify-playback-state"],
    )
)
async def pause(
    context: ToolContext,
    device_id: Annotated[
        Optional[str],
        "The id of the device this command is targeting. If omitted, the active device is targeted.",
    ] = None,
) -> Annotated[str, "Success string confirming the pause"]:
    """Pause the current track"""
    url = "https://api.spotify.com/v1/me/player/pause"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}
    params = {"device_id": device_id} if device_id else {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, params=params, headers=headers)
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to pause the current track: {e}")

    if response.status_code >= 200 and response.status_code < 300:
        return "Playback paused"
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: User does not have Spotify Premium")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(requires_auth=OAuth2(provider_id="spotify", scopes=["user-modify-playback-state"]))
async def resume(
    context: ToolContext,
    device_id: Annotated[
        Optional[str],
        "The id of the device this command is targeting. If omitted, the active device is targeted.",
    ] = None,
) -> Annotated[str, "Success string confirming the playback resume"]:
    """Resume the current track, if any"""
    url = "https://api.spotify.com/v1/me/player/play"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}
    params = {"device_id": device_id} if device_id else {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, params=params, json={})
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to resume playback: {e}")

    if response.status_code >= 200 and response.status_code < 300:
        return "Playback resumed"
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: User does not have Spotify Premium")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(
    requires_auth=OAuth2(
        provider_id="spotify",
        scopes=["user-read-playback-state"],
    )
)
async def get_playback_state(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's current playback state"]:
    """Get information about the user's current playback state, including track or episode, progress, and active device."""
    url = "https://api.spotify.com/v1/me/player"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}
    params = {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to get playback state: {e}")

    if response.status_code == 200:
        data = response.json()

        result = {
            "device_name": data.get("device", {}).get("name"),
            "currently_playing_type": data.get("currently_playing_type"),
        }

        if data.get("currently_playing_type") == "track":
            item = data.get("item", {})
            album = item.get("album", {})
            result.update({
                "album_name": album.get("name"),
                "album_artists": [artist.get("name") for artist in album.get("artists", [])],
                "album_spotify_url": album.get("external_urls", {}).get("spotify"),
                "track_name": item.get("name"),
                "track_artists": [artist.get("name") for artist in item.get("artists", [])],
            })
        elif data.get("currently_playing_type") == "episode":
            item = data.get("item", {})
            show = item.get("show", {})
            result.update({
                "show_name": show.get("name"),
                "show_spotify_url": show.get("external_urls", {}).get("spotify"),
                "episode_name": item.get("name"),
                "episode_spotify_url": item.get("external_urls", {}).get("spotify"),
            })
        return result
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: Access to the resource is denied")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")
