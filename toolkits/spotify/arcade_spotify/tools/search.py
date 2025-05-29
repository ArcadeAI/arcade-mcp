from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Spotify

from arcade_spotify.tools.models import SearchType
from arcade_spotify.tools.utils import (
    get_url,
    send_spotify_request,
)


@tool(requires_auth=Spotify())
async def search(
    context: ToolContext,
    q: Annotated[str, "The search query"],
    types: Annotated[list[SearchType], "The types of results to return"],
    limit: Annotated[int, "The maximum number of results to return"] = 1,
) -> Annotated[dict, "A list of artists matching the search query"]:
    """Search Spotify catalog information

    Explanation of the q parameter:
        You can narrow down your search using field filters.
        Available filters are album, artist, track, year, upc, tag:hipster, tag:new, isrc, and
        genre. Each field filter only applies to certain result types.

        The artist and year filters can be used while searching albums, artists and tracks.
        You can filter on a single year or a range (e.g. 1955-1960).
        The album filter can be used while searching albums and tracks.
        The genre filter can be used while searching artists and tracks.
        The isrc and track filters can be used while searching tracks.
        The upc, tag:new and tag:hipster filters can only be used while searching albums.
        The tag:new filter will return albums released in the past two weeks and tag:hipster
        can be used to return only albums with the lowest 10% popularity.

        Example: q="remaster track:Doxy artist:Miles Davis"
    """

    url = get_url("search", q=q)

    response = await send_spotify_request(
        context, "GET", url, params={"q": q, "type": ",".join(types), "limit": limit}
    )
    response.raise_for_status()
    return dict(response.json())
