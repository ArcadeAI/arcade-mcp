from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Spotify
from arcade_spotify.tools.utils import (
    get_url,
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
    response.raise_for_status()
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
    target_acousticness: Annotated[
        Optional[float],
        "The target acousticness of the recommended tracks (between 0 and 1)",
    ] = None,
    target_danceability: Annotated[
        Optional[float],
        "The target danceability of the recommended tracks (between 0 and 1)",
    ] = None,
    target_duration_ms: Annotated[
        Optional[int],
        "The target duration of the recommended tracks in milliseconds",
    ] = None,
    target_energy: Annotated[
        Optional[float],
        "The target energy of the recommended tracks (between 0 and 1)",
    ] = None,
    target_instrumentalness: Annotated[
        Optional[float],
        "The target instrumentalness of the recommended tracks (between 0 and 1)",
    ] = None,
    target_key: Annotated[
        Optional[int],
        "The target key of the recommended tracks (0-11)",
    ] = None,
    target_liveness: Annotated[
        Optional[float],
        "The target liveness of the recommended tracks (between 0 and 1)",
    ] = None,
    target_loudness: Annotated[
        Optional[float],
        "The target loudness of the recommended tracks (in decibels)",
    ] = None,
    target_mode: Annotated[
        Optional[int],
        "The target mode of the recommended tracks (0 or 1)",
    ] = None,
    target_popularity: Annotated[
        Optional[int],
        "The target popularity of the recommended tracks (0-100)",
    ] = None,
    target_speechiness: Annotated[
        Optional[float],
        "The target speechiness of the recommended tracks (between 0 and 1)",
    ] = None,
    target_tempo: Annotated[
        Optional[float],
        "The target tempo of the recommended tracks (in beats per minute)",
    ] = None,
    target_time_signature: Annotated[
        Optional[int],
        "The target time signature of the recommended tracks",
    ] = None,
    target_valence: Annotated[
        Optional[float],
        "The target valence of the recommended tracks (between 0 and 1)",
    ] = None,
) -> Annotated[dict, "A list of recommended tracks"]:
    """Get track (song) recommendations based on seed artists, genres, and tracks
    If a provided target value is outside of the expected range, it will clamp to the nearest valid value.
    """
    url = get_url("tracks_get_recommendations")
    params = {
        "seed_artists": seed_artists,
        "seed_genres": seed_genres,
        "seed_tracks": seed_tracks,
        "limit": limit,
        "target_acousticness": target_acousticness,
        "target_danceability": target_danceability,
        "target_duration_ms": target_duration_ms,
        "target_energy": target_energy,
        "target_instrumentalness": target_instrumentalness,
        "target_key": target_key,
        "target_liveness": target_liveness,
        "target_loudness": target_loudness,
        "target_mode": target_mode,
        "target_popularity": target_popularity,
        "target_speechiness": target_speechiness,
        "target_tempo": target_tempo,
        "target_time_signature": target_time_signature,
        "target_valence": target_valence,
    }
    params = {k: v for k, v in params.items() if v is not None}

    response = await send_spotify_request(context, "GET", url, params=params)
    response.raise_for_status()
    return response.json()


@tool(requires_auth=Spotify())
async def get_tracks_audio_features(
    context: ToolContext,
    track_ids: Annotated[list[str], "A list of Spotify track (song) IDs"],
) -> Annotated[dict, "A list of audio features for the tracks"]:
    """Get audio features for a list of tracks (songs)"""
    url = get_url("tracks_get_audio_features")
    params = {"ids": ",".join(track_ids)}

    response = await send_spotify_request(context, "GET", url, params=params)
    response.raise_for_status()
    return response.json()
