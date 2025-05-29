from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_spotify.tools.player import (
    adjust_playback_position,
    get_currently_playing,
    get_playback_state,
    pause_playback,
    play_artist_by_name,
    play_track_by_name,
    resume_playback,
    skip_to_next_track,
    skip_to_previous_track,
    start_tracks_playback_by_id,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(adjust_playback_position, "Spotify")
catalog.add_tool(skip_to_next_track, "Spotify")
catalog.add_tool(skip_to_previous_track, "Spotify")
catalog.add_tool(pause_playback, "Spotify")
catalog.add_tool(resume_playback, "Spotify")
catalog.add_tool(start_tracks_playback_by_id, "Spotify")
catalog.add_tool(get_playback_state, "Spotify")
catalog.add_tool(get_currently_playing, "Spotify")
catalog.add_tool(play_artist_by_name, "Spotify")
catalog.add_tool(play_track_by_name, "Spotify")


@tool_eval()
def spotify_player_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Spotify "player" tools."""
    suite = EvalSuite(
        name="Spotify Tools Evaluation",
        system_message="You are an AI assistant that can manage Spotify using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Adjust playback position",
        user_message="can you skip to the 10th second of the song",
        expected_tool_calls=[
            ExpectedToolCall(
                func=adjust_playback_position,
                args={"absolute_position_ms": 10000},
            )
        ],
        critics=[
            NumericCritic(
                critic_field="absolute_position_ms", weight=1.0, value_range=(9000, 11000)
            ),
        ],
    )

    suite.add_case(
        name="Adjust playback position relative to current position",
        user_message="go back 10 seconds",
        expected_tool_calls=[
            ExpectedToolCall(
                func=adjust_playback_position,
                args={"relative_position_ms": -10000},
            )
        ],
        critics=[
            NumericCritic(
                critic_field="relative_position_ms",
                weight=1.0,
                value_range=(-11000, -9000),
            ),
        ],
    )

    suite.add_case(
        name="Skip to previous track",
        user_message="oops i didn't mean to skip that song, go back",
        expected_tool_calls=[ExpectedToolCall(func=skip_to_previous_track, args={})],
    )

    suite.add_case(
        name="Skip to next track",
        user_message="skip this song and also the next one",
        expected_tool_calls=[
            ExpectedToolCall(func=skip_to_next_track, args={}),
            ExpectedToolCall(func=skip_to_next_track, args={}),
        ],
    )

    suite.add_case(
        name="Pause playback",
        user_message="wait im getting a text, stop playing it please",
        expected_tool_calls=[ExpectedToolCall(func=pause_playback, args={})],
    )

    suite.add_case(
        name="Resume playback",
        user_message="ok i'm back, you can press play again",
        expected_tool_calls=[ExpectedToolCall(func=resume_playback, args={})],
    )

    suite.add_case(
        name="Start playback of a list of tracks",
        user_message="Play these two 03gaqN3aWm9TQxuHay0G8R, 03gaqN3aWm9TQxuHay0G8R. But start at the 10th second of the first track",
        expected_tool_calls=[
            ExpectedToolCall(
                func=start_tracks_playback_by_id,
                args={
                    "track_ids": ["03gaqN3aWm9TQxuHay0G8R", "03gaqN3aWm9TQxuHay0G8R"],
                    "position_ms": 10000,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="track_ids", weight=0.5),
            NumericCritic(critic_field="position_ms", weight=0.5, value_range=(9000, 11000)),
        ],
    )

    suite.add_case(
        name="Get playback state",
        user_message="what's the name of this song and who plays it?",
        expected_tool_calls=[ExpectedToolCall(func=get_currently_playing, args={})],
    )

    suite.add_case(
        name="Get playback state",
        user_message="what device is playing music rn?",
        expected_tool_calls=[ExpectedToolCall(func=get_playback_state, args={})],
    )

    suite.add_case(
        name="Play artist by name",
        user_message="play pearl jam",
        expected_tool_calls=[
            ExpectedToolCall(
                func=play_artist_by_name,
                args={"name": "Pearl Jam"},
            )
        ],
        critics=[
            SimilarityCritic(critic_field="name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Play track by name",
        user_message="it would be really great if I could listen to strobe by deadmau5 right now.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=play_track_by_name,
                args={"track_name": "strobe", "artist_name": "deadmau5"},
            )
        ],
        critics=[
            SimilarityCritic(critic_field="track_name", weight=0.5),
            SimilarityCritic(critic_field="artist_name", weight=0.5),
        ],
    )

    return suite
