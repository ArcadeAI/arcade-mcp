from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_spotify.tools.models import SearchType
from arcade_spotify.tools.search import search

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(search, "Spotify")


@tool_eval()
def spotify_search_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Spotify "player" tools."""
    suite = EvalSuite(
        name="Spotify Tools Evaluation",
        system_message="You are an AI assistant that can manage Spotify using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search Spotify catalog",
        user_message="search for 3 songs in the the album 'American IV: The Man Comes Around' by Johnny Cash",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search,
                args={
                    "q": "album:American IV: The Man Comes Around artist:Johnny Cash",
                    "types": [SearchType.TRACK],
                    "limit": 3,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="q", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.25),
            BinaryCritic(critic_field="types", weight=0.25),
        ],
    )

    return suite
