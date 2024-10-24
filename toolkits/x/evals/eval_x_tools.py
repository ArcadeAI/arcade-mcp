import arcade_x
from arcade_x.tools.tweets import post_tweet

# TODO
# delete_tweet_by_id,
# search_recent_tweets_by_keywords,
# search_recent_tweets_by_username,
# from arcade_x.tools.users import lookup_single_user_by_username
from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    SimilarityCritic,
    tool_eval,
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
        system_message="You are an AI assistant with access to the X (Twitter) tools. Use them to help answer the user's X-related tasks/questions.",
        catalog=catalog,
        rubric=rubric,
    )

    # Add cases
    suite.add_case(
        name="Post a tweet",
        user_message="Send out a tweet that says 'Hello World! Exciting stuff is happening over at Arcade AI!'",
        expected_tool_calls=[
            (
                post_tweet,
                {"tweet_text": "Hello World! Exciting stuff is happening over at Arcade AI!"},
            )
        ],
        critics=[
            SimilarityCritic(
                critic_field="tweet_text",
                weight=1.0,
                similarity_threshold=0.9,
            ),
        ],
    )
    return suite
