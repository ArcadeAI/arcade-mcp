import httpx
from arcade_tdk import ToolContext

from arcade_spotify.tools.constants import ENDPOINTS, SPOTIFY_BASE_URL
from arcade_spotify.tools.models import PlaybackState


async def send_spotify_request(
    context: ToolContext,
    method: str,
    url: str,
    params: dict | None = None,
    json_data: dict | None = None,
) -> httpx.Response:
    """
    Send an asynchronous request to the Spotify API.

    Args:
        context: The tool context containing the authorization token.
        method: The HTTP method (GET, POST, PUT, DELETE, etc.).
        url: The full URL for the API endpoint.
        params: Query parameters to include in the request.
        json_data: JSON data to include in the request body.

    Returns:
        The response object from the API request.

    Raises:
        ToolExecutionError: If the request fails for any reason.
    """
    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, params=params, json=json_data)

    return response


def get_url(endpoint: str, **kwargs: object) -> str:
    """
    Get the full Spotify URL for a given endpoint.

    :param endpoint: The endpoint key from ENDPOINTS
    :param kwargs: The parameters to format the URL with
    :return: The full URL
    """
    return f"{SPOTIFY_BASE_URL}{ENDPOINTS[endpoint].format(**kwargs)}"


def convert_to_playback_state(data: dict) -> PlaybackState:
    """
    Convert the Spotify API endpoint "/me/player" response data to a PlaybackState object.

    Args:
        data: The response data from the Spotify API endpoint "/me/player".

    Returns:
        An instance of PlaybackState populated with the data.
    """
    playback_state = PlaybackState(
        device_name=data.get("device", {}).get("name"),
        device_id=data.get("device", {}).get("id"),
        currently_playing_type=data.get("currently_playing_type"),
        is_playing=data.get("is_playing"),
        progress_ms=data.get("progress_ms"),
        message=data.get("message"),
    )

    if data.get("currently_playing_type") == "track":
        item = data.get("item") or {}
        album = item.get("album", {})
        playback_state.album_name = album.get("name")
        playback_state.album_id = album.get("id")
        playback_state.album_artists = [artist.get("name") for artist in album.get("artists", [])]
        playback_state.album_spotify_url = album.get("external_urls", {}).get("spotify")
        playback_state.track_name = item.get("name")
        playback_state.track_id = item.get("id")
        playback_state.track_spotify_url = item.get("external_urls", {}).get("spotify")
        playback_state.track_artists = [artist.get("name") for artist in item.get("artists", [])]
        playback_state.track_artists_ids = [artist.get("id") for artist in item.get("artists", [])]
    elif data.get("currently_playing_type") == "episode":
        item = data.get("item") or {}
        show = item.get("show", {})
        playback_state.show_name = show.get("name")
        playback_state.show_id = show.get("id")
        playback_state.show_spotify_url = show.get("external_urls", {}).get("spotify")
        playback_state.episode_name = item.get("name")
        playback_state.episode_id = item.get("id")
        playback_state.episode_spotify_url = item.get("external_urls", {}).get("spotify")

    return playback_state
