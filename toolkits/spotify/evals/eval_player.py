from arcade_spotify.tools.player import (
    adjust_playback_position,
    get_currently_playing,
    get_playback_state,
    pause_playback,
    resume_playback,
    skip_to_next_track,
    skip_to_previous_track,
    start_tracks_playback_by_id,
)

from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    tool_eval,
)
from arcade.sdk.eval.critic import NumericCritic

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


@tool_eval()
def spotify_eval_suite() -> EvalSuite:
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
            (
                adjust_playback_position,
                {
                    "absolute_position_ms": 10000,
                },
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
            (
                adjust_playback_position,
                {
                    "relative_position_ms": -10000,
                },
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
        expected_tool_calls=[(skip_to_previous_track, {})],
    )

    suite.add_case(
        name="Skip to next track",
        user_message="skip this song and also the next one",
        expected_tool_calls=[(skip_to_next_track, {}), (skip_to_next_track, {})],
    )

    suite.add_case(
        name="Pause playback",
        user_message="wait im getting a text, stop playing it please",
        expected_tool_calls=[(pause_playback, {})],
    )

    suite.add_case(
        name="Resume playback",
        user_message="ok i'm back, you can press play again",
        expected_tool_calls=[(resume_playback, {})],
    )

    suite.add_case(
        name="Start playback of a list of tracks",
        user_message="Play these two 03gaqN3aWm9TQxuHay0G8R, 03gaqN3aWm9TQxuHay0G8R. But start at the 10th second of the first track",
        expected_tool_calls=[
            (
                start_tracks_playback_by_id,
                {
                    "track_ids": ["03gaqN3aWm9TQxuHay0G8R", "03gaqN3aWm9TQxuHay0G8R"],
                    "position_ms": 10000,
                },
            )
        ],
    )

    suite.add_case(
        name="Get playback state",
        user_message="what's the name of this song and who plays it?",
        expected_tool_calls=[(get_currently_playing, {})],
    )

    suite.add_case(
        name="Get playback state",
        user_message="what device is playing music rn?",
        expected_tool_calls=[(get_playback_state, {})],
    )

    return suite
