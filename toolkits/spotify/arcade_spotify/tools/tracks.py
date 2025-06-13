from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Spotify

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
    return dict(response.json())
