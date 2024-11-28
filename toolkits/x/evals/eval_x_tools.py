from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    tool_eval,
)

import arcade_x
from arcade_x.tools.tweets import (
    delete_tweet_by_id,
    lookup_tweet_by_id,
    post_tweet,
    search_recent_tweets_by_keywords,
    search_recent_tweets_by_username,
)
from arcade_x.tools.users import lookup_single_user_by_username

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
        name="Post a tweet",
        user_message=(
            "Send out a tweet that says 'Hello World! Exciting stuff is happening over "
            "at Arcade AI!'"
        ),
        expected_tool_calls=[
            (
                post_tweet,
                {"tweet_text": "Hello World! Exciting stuff is happening over at Arcade AI!"},
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="tweet_text",
                weight=1.0,
            ),
        ],
    )

    suite.add_case(
        name="Delete a tweet by ID",
        user_message="Please delete the tweet with ID '148975632'.",
        expected_tool_calls=[
            (
                delete_tweet_by_id,
                {"tweet_id": "148975632"},
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="tweet_id",
                weight=1.0,
            ),
        ],
    )

    suite.add_case(
        name="Search recent tweets by username",
        user_message="Show me the recent tweets from 'elonmusk'.",
        expected_tool_calls=[
            (
                search_recent_tweets_by_username,
                {"username": "elonmusk", "max_results": 10},
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="username",
                weight=1.0,
            ),
        ],
    )

    suite.add_case(
        name="Lookup user by username",
        user_message="Can you get information about the user '@jack'?",
        expected_tool_calls=[
            (
                lookup_single_user_by_username,
                {"username": "jack"},
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="username",
                weight=1.0,
            ),
        ],
    )

    # Add a case for searching recent tweets by keywords
    suite.add_case(
        name="Search recent tweets by keywords",
        user_message="Find recent tweets containing 'Arcade AI'.",
        expected_tool_calls=[
            (
                search_recent_tweets_by_keywords,
                {
                    "keywords": [],
                    "phrases": ["Arcade AI"],
                    "max_results": 10,
                },
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="keywords",
                weight=0.1,
            ),
            BinaryCritic(
                critic_field="phrases",
                weight=0.9,
            ),
        ],
    )

    # Extend the case to test lookup_tweet_by_id
    suite.extend_case(
        name="Lookup tweet by ID",
        user_message="Can you provide details about the tweet with ID '123456789'?",
        expected_tool_calls=[
            (
                lookup_tweet_by_id,
                {
                    "tweet_id": "123456789",
                },
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="tweet_id",
                weight=1.0,
            ),
        ],
    )

    return suite
