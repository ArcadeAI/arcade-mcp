from arcade.core.catalog import ToolCatalog
from arcade_x.tools.tweets import (
    post_tweet,
    delete_tweet_by_id,
    # search_recent_tweets_by_query,
    search_recent_tweets_by_username,
    search_recent_tweets_by_keywords,
)
from arcade_x.tools.users import lookup_single_user_by_username
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
catalog.add_tool(search_recent_tweets_by_keywords)
catalog.add_tool(lookup_single_user_by_username)
catalog.add_tool(post_tweet)
catalog.add_tool(delete_tweet_by_id)
catalog.add_tool(search_recent_tweets_by_username)


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
            ExpectedToolCall(
                name="PostTweet",
                args={
                    "tweet_text": "Hello World! Exciting stuff is happening over at Arcade AI!"
                },
            )
        ],
        critics=[
            BinaryCritic(
                critic_field="tweet_text",
                weight=1.0,
            ),
        ],
    )
    return suite
