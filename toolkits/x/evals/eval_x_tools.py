from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

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

search_recent_tweets_by_username_history = [
    {"role": "user", "content": "list 1 tweet from elonmusk"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_kineaPbYCAof3n6qCwnYSKBb",
                "type": "function",
                "function": {
                    "name": "X_SearchRecentTweetsByUsername",
                    "arguments": '{"max_results":1,"username":"elonmusk"}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"data":[{"author_id":"44196397","author_name":"Elon Musk","author_username":"elonmusk","edit_history_tweet_ids":["1866572304320466985"],"id":"1866572304320466985","text":"RT @chamath: Meanwhile the State of California is going to spend almost double this ($35B) to build a 171 mile stretch of rail between Merc…","tweet_url":"https://x.com/x/status/1866572304320466985"},{"author_id":"44196397","edit_history_tweet_ids":["1866571568266219998"],"id":"1866571568266219998","text":"This is awesome 🚀🇺🇸 https://twitter.com/cb_doge/status/1866565984502550905","tweet_url":"https://x.com/x/status/1866571568266219998"},{"author_id":"44196397","edit_history_tweet_ids":["1866571416969285954"],"id":"1866571416969285954","text":"@ajtourville @Tesla I’ve always felt that the climate predictions were too pessimistic and bound to backfire. \\n\\nExtreme environmentalists can’t say ridiculous things like the world is doomed in 5 years, because 5 years goes by, the world is ok and they lose credibility. \\n\\nIf we transition to… https://x.com/i/web/status/1866571416969285954","tweet_url":"https://x.com/x/status/1866571416969285954"},{"author_id":"44196397","edit_history_tweet_ids":["1866569957309603946"],"id":"1866569957309603946","text":"@shaunmmaguire Yes, please. This is gone on for too long. Enough.","tweet_url":"https://x.com/x/status/1866569957309603946"},{"author_id":"44196397","edit_history_tweet_ids":["1866569078539948491"],"id":"1866569078539948491","text":"@FatEmperor 😂","tweet_url":"https://x.com/x/status/1866569078539948491"},{"author_id":"44196397","edit_history_tweet_ids":["1866554579925577793"],"id":"1866554579925577793","text":"@cb_doge I’m not buying or building a house anywhere","tweet_url":"https://x.com/x/status/1866554579925577793"},{"author_id":"44196397","edit_history_tweet_ids":["1866536009833361915"],"id":"1866536009833361915","text":"RT @amuse: http://x.com/i/article/1866500805211123713","tweet_url":"https://x.com/x/status/1866536009833361915"},{"author_id":"44196397","edit_history_tweet_ids":["1866535704924483739"],"id":"1866535704924483739","text":"@benshapiro 😂","tweet_url":"https://x.com/x/status/1866535704924483739"},{"author_id":"44196397","edit_history_tweet_ids":["1866535550632550854"],"id":"1866535550632550854","text":"@AutismCapital 😂","tweet_url":"https://x.com/x/status/1866535550632550854"},{"author_id":"44196397","edit_history_tweet_ids":["1866535352024043804"],"id":"1866535352024043804","text":"@JDVance Yes","tweet_url":"https://x.com/x/status/1866535352024043804"}],"includes":{"users":[{"id":"44196397","name":"Elon Musk","username":"elonmusk"}]},"meta":{"newest_id":"1866572304320466985","next_token":"b26v89c19zqg8o3frr3tekall7a7ooom3sctaw30rz62l","oldest_id":"1866535352024043804","result_count":10}}',  # noqa: RUF001
        "tool_call_id": "call_kineaPbYCAof3n6qCwnYSKBb",
        "name": "X_SearchRecentTweetsByUsername",
    },
    {
        "role": "assistant",
        "content": 'Here is a recent tweet from Elon Musk: \n\n"This is awesome 🚀🇺🇸" - [Tweet link](https://x.com/x/status/1866571568266219998)',
    },
]


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
            ExpectedToolCall(
                func=post_tweet,
                args={"tweet_text": "Hello World! Exciting stuff is happening over at Arcade AI!"},
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
            ExpectedToolCall(
                func=delete_tweet_by_id,
                args={"tweet_id": "148975632"},
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
            ExpectedToolCall(
                func=search_recent_tweets_by_username,
                args={"username": "elonmusk", "max_results": 10},
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
        name="Search recent tweets by username with history",
        user_message="Get the next 42",
        additional_messages=search_recent_tweets_by_username_history,
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_tweets_by_username,
                args={
                    "username": "elonmusk",
                    "max_results": 42,
                    "next_token": "b26v89c19zqg8o3frr3tekall7a7ooom3sctaw30rz62l",
                },
            ),
        ],
        critics=[
            BinaryCritic(
                critic_field="username",
                weight=0.2,
            ),
            BinaryCritic(
                critic_field="max_results",
                weight=0.2,
            ),
            BinaryCritic(
                critic_field="next_token",
                weight=0.6,
            ),
        ],
    )

    suite.add_case(
        name="Lookup user by username",
        user_message="Can you get information about the user '@jack'?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=lookup_single_user_by_username,
                args={"username": "jack"},
            ),
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
            ExpectedToolCall(
                func=search_recent_tweets_by_keywords,
                args={
                    "keywords": None,
                    "phrases": ["Arcade AI"],
                    "max_results": 10,
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
                weight=0.9,
            ),
        ],
    )

    # Extend the case to test lookup_tweet_by_id
    suite.extend_case(
        name="Lookup tweet by ID",
        user_message="Can you provide details about the tweet with ID '123456789'?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=lookup_tweet_by_id,
                args={"tweet_id": "123456789"},
            ),
        ],
        critics=[
            BinaryCritic(
                critic_field="tweet_id",
                weight=1.0,
            ),
        ],
    )

    return suite
