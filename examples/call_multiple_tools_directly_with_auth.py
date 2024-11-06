"""Example script demonstrating how to call multiple tools directly with authentication.

For this example, we are using the prebuilt Spotify toolkit to start playing similar songs to the currently playing song.

Steps:
1. Get the currently playing song
2. Get audio features for the currently playing song
3. Get song recommendations that are similar to the currently playing song
4. Start playing the recommended songs
5. Inform the user which recommended song is now playing
"""

from typing import Any, Optional

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
    return response.output.value


def recommend_similar_songs(
    client: Arcade, provider_to_scopes: dict, tools: list[str], user_id: str, user_country_code: str
) -> None:
    """Execute the sequence of tools to get recommendations and start playback."""
    get_permissions(client, provider_to_scopes, user_id)

    recommendation_params = {"seed_genres": []}

    (
        get_currently_playing_tool,
        get_tracks_audio_features_tool,
        get_recommendations_tool,
        start_tracks_playback_tool,
    ) = tools

    # Step 1: Get the currently playing song
    while True:
        response = call_tool(client, get_currently_playing_tool, user_id)

        if response["is_playing"]:
            break

        print("Nothing is playing right now. Press Enter once you start playing a song...")
        input()

    # Step 1.5: Use the previous tool output to construct the inputs for the following tool calls
    current_track_name = response["track_name"]
    current_track_artists = response["track_artists"]
    current_track_id = response["track_id"]
    current_track_spotify_url = response["track_spotify_url"]
    current_track_artists_ids = response["track_artists_ids"]
    print(
        f"\nYou are currently listening to '{current_track_name}' by {', '.join(current_track_artists)}"
    )
    recommendation_params.update({
        "seed_tracks": [current_track_id],
        "seed_artists": current_track_artists_ids,
    })

    # Step 2:Get audio features for the currently playing song
    response = call_tool(
        client,
        get_tracks_audio_features_tool,
        user_id,
        inputs={"track_ids": [current_track_id]},
    )

    # Step 2.5: Use the previous tool output to construct the inputs for the following tool calls
    audio_features = response["audio_features"][0]
    recommendation_params.update({
        "target_acousticness": float(audio_features["acousticness"]),
        "target_danceability": float(audio_features["danceability"]),
        "target_energy": float(audio_features["energy"]),
        "target_instrumentalness": float(audio_features["instrumentalness"]),
        "target_key": int(audio_features["key"]),
        "target_liveness": float(audio_features["liveness"]),
        "target_loudness": float(audio_features["loudness"]),
        "target_mode": int(audio_features["mode"]),
        "target_speechiness": float(audio_features["speechiness"]),
        "target_tempo": float(audio_features["tempo"]),
        "target_time_signature": int(audio_features["time_signature"]),
        "target_valence": float(audio_features["valence"]),
    })

    # Step 3: Get song recommendations that are similar to the currently playingsong
    print(
        f"Getting recommendations similar to '{current_track_name}' by {', '.join(current_track_artists)} - {current_track_spotify_url}"
    )
    response = call_tool(client, get_recommendations_tool, user_id, inputs=recommendation_params)

    # Step 3.5: Use the previous tool output to construct the inputs for the following tool calls
    # Filter out remixes and the same song from the recommendations
    tracks = [
        track for track in response["tracks"] if not track["name"].startswith(current_track_name)
    ]
    track_ids = [
        track["id"] for track in tracks if (user_country_code in track["available_markets"])
    ]
    track_names = [track["name"] for track in tracks]
    tracks_artists = [[artist["name"] for artist in track["artists"]] for track in tracks]
    track_spotify_urls = [track["external_urls"]["spotify"] for track in tracks]

    if not track_ids:
        print("I couldn't find any similar songs that are available in your country.")
        return

    print("\nHere are some recommendations:")
    for track_name, track_artists, track_spotify_url in zip(
        track_names, tracks_artists, track_spotify_urls
    ):
        print(f"\t{track_name} by {', '.join(track_artists)} - {track_spotify_url}")

    # Step 4: Start playing the recommended songs
    response = call_tool(
        client,
        start_tracks_playback_tool,
        user_id,
        inputs={"track_ids": track_ids},
    )

    # Step 5: Inform the user which recommended song is now playing
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
            "user-modify-playback-state",
        ],
    }

    tools = [
        "Spotify.GetCurrentlyPlaying",  # Get info about the current song
        "Spotify.GetTracksAudioFeatures",  # Get audio features for the current song
        "Spotify.GetRecommendations",  # Get recommendations similar to the current song
        "Spotify.StartTracksPlaybackById",  # Start playing the recommended songs
    ]

    user_id = "you@example.com"
    user_country_code = "US"

    while True:
        recommend_similar_songs(client, provider_to_scopes, tools, user_id, user_country_code)
        print("\nPress Enter to get more recommendations...")
        input()
