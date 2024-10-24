from typing import Annotated, Optional

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Spotify
from arcade.sdk.errors import ToolExecutionError

SPOTIFY_BASE_URL = "https://api.spotify.com/v1"


async def _send_spotify_request(
    context: ToolContext,
    method: str,
    endpoint: str,
    params: dict | None = None,
    json_data: dict | None = None,
) -> httpx.Response:
    """
    Send an asynchronous request to the Spotify API.

    Args:
        context: The tool context containing the authorization token.
        method: The HTTP method (GET, POST, PUT, DELETE, etc.).
        endpoint: The API endpoint path (e.g., "/me/player/play").
        params: Query parameters to include in the request.
        json_data: JSON data to include in the request body.

    Returns:
        The response object from the API request.

    Raises:
        ToolExecutionError: If the request fails for any reason.
    """
    url = f"{SPOTIFY_BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method, url, headers=headers, params=params, json=json_data
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to send request to Spotify API: {e}")

    return response


def _handle_spotify_api_error(response: httpx.Response):
    """
    Handle errors from the Spotify API by mapping common status codes to ToolExecutionErrors.

    Args:
        response: The response object from the API request.

    Raises:
        ToolExecutionError: If the response contains an error status code.
    """
    status_code_map = {
        401: ToolExecutionError("Unauthorized: Invalid or expired token"),
        403: ToolExecutionError("Forbidden: User does not have Spotify Premium"),
        429: ToolExecutionError("Too Many Requests: Rate limit exceeded"),
    }

    if response.status_code in status_code_map:
        raise status_code_map[response.status_code]
    elif response.status_code >= 400:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(
    requires_auth=Spotify(
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
    endpoint = "/me/player/pause"
    params = {"device_id": device_id} if device_id else {}

    response = await _send_spotify_request(context, "PUT", endpoint, params=params)
    if response.status_code >= 200 and response.status_code < 300:
        return "Playback paused"
    else:
        _handle_spotify_api_error(response)


@tool(
    requires_auth=Spotify(
        scopes=["user-modify-playback-state"],
    )
)
async def resume(
    context: ToolContext,
    device_id: Annotated[
        Optional[str],
        "The id of the device this command is targeting. If omitted, the active device is targeted.",
    ] = None,
) -> Annotated[str, "Success string confirming the playback resume"]:
    """Resume the current track, if any"""
    endpoint = "/me/player/play"
    params = {"device_id": device_id} if device_id else {}

    response = await _send_spotify_request(context, "PUT", endpoint, params=params)
    if response.status_code >= 200 and response.status_code < 300:
        return "Playback resumed"
    else:
        _handle_spotify_api_error(response)


@tool(
    requires_auth=Spotify(
        scopes=["user-read-playback-state"],
    )
)
async def get_playback_state(
    context: ToolContext,
) -> Annotated[dict, "Information about the user's current playback state"]:
    """Get information about the user's current playback state, including track or episode, progress, and active device."""
    endpoint = "/me/player"

    response = await _send_spotify_request(context, "GET", endpoint)
    if response.status_code == 204:
        return {"status": "Playback not available or active"}
    elif response.status_code == 200:
        data = response.json()

        # TODO: Return a more structured model
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
    else:
        _handle_spotify_api_error(response)
