from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

from arcade_spotify.tools.tracks import (
    get_recommendations,
    get_track_from_id,
    get_tracks_audio_features,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(get_track_from_id, "Spotify")
catalog.add_tool(get_recommendations, "Spotify")
catalog.add_tool(get_tracks_audio_features, "Spotify")

# This history is a conversation where the user asks for the currently playing song, and then asks for information about it.
history = [
    {"role": "user", "content": "what song is playing rn"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_fqZHT1DNcil1pbIv6UbOWVq9",
                "type": "function",
                "function": {"name": "Spotify_GetCurrentlyPlaying", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["Gajaka"],"album_id":"7b5h7MJ70KC92FrwSvRaQi","album_name":"Aerial","album_spotify_url":"https://open.spotify.com/album/7b5h7MJ70KC92FrwSvRaQi","currently_playing_type":"track","is_playing":true,"progress_ms":96962,"track_artists":["Gajaka"],"track_id":"03gaqN3aWm9TQxuHay0G8R","track_name":"Aerial"}',
        "tool_call_id": "call_fqZHT1DNcil1pbIv6UbOWVq9",
        "name": "Spotify_GetCurrentlyPlaying",
    },
    {
        "role": "assistant",
        "content": 'The song currently playing is "Aerial" by Gajaka. You can listen to it on Spotify [here](https://open.spotify.com/album/7b5h7MJ70KC92FrwSvRaQi).',
    },
]

# This history is a conversation where the user asks for the currently playing song, and then asks to skip to the next song, and then asks for information about the new song.
history_2 = [
    {"role": "user", "content": "what song is playing right now?"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_u2nS7hd7ETdbjElHW4mrFphd",
                "type": "function",
                "function": {"name": "Spotify_GetCurrentlyPlaying", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["The Dawning"],"album_id":"2dmrP48hhdCIoxeYJFMSVO","album_name":"summer breeze","album_spotify_url":"https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO","currently_playing_type":"track","is_playing":true,"progress_ms":144092,"track_artists":["The Dawning"],"track_id":"14CQdqVFygEls6szbfwuTL","track_name":"summer breeze"}',
        "tool_call_id": "call_u2nS7hd7ETdbjElHW4mrFphd",
        "name": "Spotify_GetCurrentlyPlaying",
    },
    {
        "role": "assistant",
        "content": 'The song "summer breeze" by The Dawning is currently playing. You can check it out on [Spotify](https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO).',
    },
    {"role": "user", "content": "please skip this song"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_htECRssaXZ4jtNvjdUY2r3ml",
                "type": "function",
                "function": {"name": "Spotify_SkipToNextTrack", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["Philó"],"album_id":"525aF5PKAQXzbmP7oAb0gC","album_name":"Skylar","album_spotify_url":"https://open.spotify.com/album/525aF5PKAQXzbmP7oAb0gC","currently_playing_type":"track","device_id":"84b6aa89387cfe3e132465001647027bfd1b44f3","device_name":"iPhone","is_playing":true,"progress_ms":233,"track_artists":["Philó"],"track_id":"5r9fTbn6YZVxHKaU4Rze3t","track_name":"Tempestade"}',
        "tool_call_id": "call_htECRssaXZ4jtNvjdUY2r3ml",
        "name": "Spotify_SkipToNextTrack",
    },
    {
        "role": "assistant",
        "content": 'I\'ve skipped to the next song. Now playing: "Tempestade" by Philó. You can listen to it on [Spotify](https://open.spotify.com/album/525aF5PKAQXzbmP7oAb0gC).',
    },
    {"role": "user", "content": "now what song is playing?"},
    {"role": "assistant", "content": 'The song now playing is "Tempestade" by Philó.'},
]


@tool_eval()
def spotify_tracks_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Spotify "track" tools."""
    suite = EvalSuite(
        name="Spotify Tools Evaluation",
        system_message="You are an AI assistant that can manage Spotify using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get information about a track",
        user_message="can you get more info about that song",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_track_from_id,
                args={
                    "track_id": "03gaqN3aWm9TQxuHay0G8R",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="track_id", weight=1.0),
        ],
        additional_messages=history,
    )

    return suite
