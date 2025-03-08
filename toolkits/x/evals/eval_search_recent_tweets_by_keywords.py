from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import arcade_x
from arcade_x.tools.tweets import (
    search_recent_tweets_by_keywords,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the X tools
catalog.add_module(arcade_x)


@tool_eval()
def x_eval_suite() -> EvalSuite:
    """Evaluation suite for X (Twitter) tools."""

    suite = EvalSuite(
        name="X Tools Evaluation Suite",
        system_message=(
            "You are an AI assistant with access to the X (Twitter) tools. Use them to "
            "help answer the user's X-related tasks/questions."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Add cases
    suite.add_case(
        name="Search recent tweets by keywords",
        user_message="Find recent tweets containing 'Arcade AI'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_tweets_by_keywords,
                args={
                    "keywords": None,
                    "phrases": ["Arcade AI"],
                    "max_results": 10,
                    "next_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(
                critic_field="keywords",
                weight=0.1,
            ),
            BinaryCritic(
                critic_field="phrases",
                weight=0.7,
            ),
            BinaryCritic(
                critic_field="max_results",
                weight=0.1,
            ),
            BinaryCritic(
                critic_field="next_token",
                weight=0.1,
            ),
        ],
    )

    suite.extend_case(
        name="Split into keywords",
        user_message="Search again but now either of the words can appear anywhere in the post.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_tweets_by_keywords,
                args={
                    "keywords": ["Arcade", "AI"],
                    "phrases": None,
                    "max_results": 10,
                    "next_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(
                critic_field="keywords",
                weight=0.5,
            ),
            BinaryCritic(
                critic_field="phrases",
                weight=0.3,
            ),
            BinaryCritic(
                critic_field="max_results",
                weight=0.1,
            ),
            BinaryCritic(
                critic_field="next_token",
                weight=0.1,
            ),
        ],
    )

    return suite
