from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Spotify
from arcade_spotify.tools.utils import (
    get_url,
    handle_spotify_response,
    send_spotify_request,
)


@tool(requires_auth=Spotify())
async def get_track_from_id(
    context: ToolContext,
    track_id: Annotated[str, "The Spotify ID of the track"],
) -> Annotated[dict, "Information about the track"]:
    """Get information about a track"""
    url = get_url("tracks_get_track", track_id=track_id)

    response = await send_spotify_request(context, "GET", url)
    handle_spotify_response(response, url)
    return response.json()


@tool(requires_auth=Spotify())
async def get_recommendations(
    context: ToolContext,
    seed_artists: Annotated[
        list[str], "A list of Spotify artist IDs to seed the recommendations with"
    ],
    seed_genres: Annotated[
        list[str], "A list of Spotify genre IDs to seed the recommendations with"
    ],
    seed_tracks: Annotated[
        list[str], "A list of Spotify track IDs to seed the recommendations with"
    ],
    limit: Annotated[int, "The maximum number of recommended tracks to return"] = 5,
) -> Annotated[dict, "A list of recommended tracks"]:
    """Get track (song) recommendations based on seed artists, genres, and tracks"""
    url = get_url("tracks_get_recommendations")
    params = {
        "seed_artists": seed_artists,
        "seed_genres": seed_genres,
        "seed_tracks": seed_tracks,
        "limit": limit,
    }

    response = await send_spotify_request(context, "GET", url, params=params)
    handle_spotify_response(response, url)
    return response.json()
