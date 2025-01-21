"""
Example script demonstrating how to call multiple tools (sequentially) using an LLM with authentication.

For this example, we are using the prebuilt Spotify toolkit to search for a song, start playing it, and
get info about the currently playing song.

Steps:
1. Search for the song
2. Start playing the song
3. Get info about the currently playing song
4. Inform the user which song is now playing
"""

import os

from openai import OpenAI


def call_tool(client: OpenAI, user_id: str, tool: str, message: dict, history: list[dict]) -> str:
    """Make a tool call with a specific tool and message."""
    response = client.chat.completions.create(
        messages=[
            *history,
            message,
        ],
        model="gpt-4o",
        user=user_id,
        tools=[tool],
        tool_choice="generate",
    )
    return response


def call_tools_with_llm(
    client: OpenAI, user_id: str, song_name: str, artist_name: str
) -> list[dict]:
    """Use an LLM to execute the sequence of tools to search for a song and start playback."""
    tools = [
        "Spotify.Search",
        "Spotify.StartTracksPlaybackById",
        "Spotify.GetCurrentlyPlaying",
    ]

    messages = [
        {"role": "user", "content": f"Search for '{song_name}' by {artist_name}' on Spotify."},
        {"role": "user", "content": "Start playing the song. Just one tool call."},
        {"role": "user", "content": "Get the currently playing song."},
    ]

    history = []
    for i in range(len(messages)):
        response = call_tool(client, user_id, tools[i], messages[i], history)
        print("\n\n", response.choices[0].message.content)
        if (
            response.choices[0].tool_authorizations
            and response.choices[0].tool_authorizations[0].get("status") == "pending"
        ):
            input("\nPress Enter once you have authorized...")
            response = call_tool(client, user_id, tools[i], messages[i], history)
        history.append(messages[i])
        history.append({"role": "assistant", "content": response.choices[0].message.content})

    return history


if __name__ == "__main__":
    arcade_api_key = os.environ.get("ARCADE_API_KEY")
    cloud_host = "https://api.arcade-ai.com/v1"

    openai_client = OpenAI(
        api_key=arcade_api_key,
        base_url=cloud_host,
    )

    user_id = "you@example.com"
    song_name = input("Enter the song name: ")
    artist_name = input("Enter the artist name: ")

    history = call_tools_with_llm(openai_client, user_id, song_name, artist_name)
    print("\n\n", history)
