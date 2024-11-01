"""
Example script demonstrating how to call multiple tools (sequentially) using an LLM with authentication.

For this example, we are using the prebuilt Spotify toolkit to start playing similar songs to the currently playing song.

Steps:
1. Get the currently playing song
2. Get audio features for the currently playing song
3. Get song recommendations that are similar to the currently playing song
4. Start playing the recommended songs
5. Inform the user which recommended song is now playing
"""

import os

from openai import OpenAI


def call_tool(client, user_id, tool, message, history):
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
    return response.choices[0].message.content


def call_tools_with_llm(client, user_id, user_country_code):
    """Use an LLM to execute the sequence of tools to get recommendations and start playback."""
    tools = [
        "Spotify.GetCurrentlyPlaying",
        "Spotify.GetTracksAudioFeatures",
        "Spotify.GetRecommendations",
        "Spotify.StartTracksPlaybackById",
        "Spotify.GetCurrentlyPlaying",
    ]

    messages = [
        {"role": "user", "content": "Get the currently playing song."},
        {"role": "user", "content": "Retrieve its audio features."},
        {
            "role": "user",
            "content": "Get song recommendations similar to it. Do not include the currently playing song in the recommendations or any remixed versions of the song.",
        },
        {"role": "user", "content": "Start playing the recommended songs. Just one tool call."},
        {"role": "user", "content": "Get the currently playing song."},
    ]

    history = []
    for i in range(len(messages)):
        response = call_tool(client, user_id, tools[i], messages[i], history)
        print("\n\n", response)
        if "https://accounts.spotify.com/authorize?" in response:
            input("\nPress Enter once you have authorized...")
            response = call_tool(client, user_id, tools[i], messages[i], history)
        history.append(messages[i])
        history.append({"role": "assistant", "content": response})

    return history


if __name__ == "__main__":
    arcade_api_key = os.environ.get("ARCADE_API_KEY")
    local_host = "http://localhost:9099/v1"

    openai_client = OpenAI(
        api_key=arcade_api_key,
        base_url=local_host,
    )

    user_id = "you@example.com"
    user_country_code = "US"

    while True:
        history = call_tools_with_llm(openai_client, user_id, user_country_code)

        print("\nPress Enter to get more recommendations...")
        input()
