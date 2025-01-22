"""Example script demonstrating how to call multiple tools directly with authentication.

For this example, we are using the prebuilt Spotify toolkit to start playing similar songs to the currently playing song.

Steps:
1. Search for the song
2. Start playing the song
3. Get info about the currently playing song
4. Inform the user which song is now playing
"""

from typing import Any, Optional

from arcade_spotify.tools.models import SearchType
from arcadepy import Arcade  # pip install arcade-py


# Need to click on a link for every provider
def get_permissions(client: Arcade, provider_to_scopes: dict, user_id: str) -> None:
    """Prompt the user to authorize necessary permissions for each provider."""
    for provider, scopes in provider_to_scopes.items():
        auth_response = client.auth.start(
            user_id=user_id,
            provider=provider,
            scopes=scopes,
        )

        if auth_response.status != "completed":
            print(f"Click this link to authorize: {auth_response.authorization_url}")
            input("After you have authorized, press Enter to continue...")


def call_tool(client: Arcade, tool_name: str, user_id: str, inputs: Optional[dict] = None) -> Any:
    """Call a single tool."""
    if inputs is None:
        inputs = {}

    response = client.tools.execute(
        tool_name=tool_name,
        inputs=inputs,
        user_id=user_id,
    )

    if response.output.error:
        print(response.output.error)

    return response.output.value


def search_and_play_song(
    client: Arcade,
    provider_to_scopes: dict,
    tools: list[str],
    user_id: str,
    song_name: str,
    artist_name: str,
) -> None:
    """Execute the sequence of tools to get recommendations and start playback."""
    get_permissions(client, provider_to_scopes, user_id)

    (
        search_tool,
        start_playback_tool,
        get_currently_playing_tool,
    ) = tools

    # Step 1: search for the song
    response = call_tool(
        client=client,
        tool_name=search_tool,
        user_id=user_id,
        inputs={
            "q": f"{song_name} {artist_name}",
            "types": [SearchType.TRACK],
        },
    )

    if not response["tracks"]["items"]:
        print("Sorry, I couldn't find that song on Spotify.")
        return

    # Step 2: Start playing the song
    track_id = response["tracks"]["items"][0]["id"]
    response = call_tool(
        client,
        start_playback_tool,
        user_id,
        inputs={"track_ids": [track_id]},
    )

    # Step 3: get currently playing song
    response = call_tool(client, get_currently_playing_tool, user_id)
    print(
        f"\nNow playing: {response['track_name']} by {', '.join(response['track_artists'])} - {response['track_spotify_url']}"
    )


if __name__ == "__main__":
    client = Arcade(base_url="https://api.arcade-ai.com")

    # Necessary scopes for the tools we are calling:
    provider_to_scopes = {
        "spotify": [
            "user-read-currently-playing",
            "user-read-playback-state",
        ],
    }

    tools = [
        "Spotify.Search",  # Search for a song
        "Spotify.StartTracksPlaybackById",  # Start playing the song
        "Spotify.GetCurrentlyPlaying",  # Get info about the current song
    ]

    user_id = "you@example.com"
    song_name = input("Enter the song name: ")
    artist_name = input("Enter the artist name: ")

    search_and_play_song(client, provider_to_scopes, tools, user_id, song_name, artist_name)
