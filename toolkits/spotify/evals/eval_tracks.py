from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_spotify.tools.tracks import get_track_from_id

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(get_track_from_id, "Spotify")

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
