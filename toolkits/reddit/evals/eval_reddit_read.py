from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade.sdk.eval.critic import BinaryCritic

import arcade_reddit
from arcade_reddit.enums import RedditTimeFilter, SubredditListingType
from arcade_reddit.tools import (
    get_content_of_post,
    get_posts_in_subreddit,
    get_top_level_comments,
)
from arcade_reddit.tools.read import get_content_of_multiple_posts
from evals.additional_messages import get_post_in_subreddit_messages
from evals.critics import AnyOfCritic, ListCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_reddit)


@tool_eval()
def reddit_get_posts_in_subreddit_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_get_posts_in_subreddit_1",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="reddit_get_posts_in_subreddit_1",
        user_message="Get 30 posts from AskReddit that are contentious at this moment.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_posts_in_subreddit,
                args={
                    "subreddit": "AskReddit",
                    "listing": SubredditListingType.CONTROVERSIAL.value,
                    "limit": 30,
                    "cursor": None,
                    "time_range": RedditTimeFilter.NOW.value,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="subreddit", weight=0.3),
            BinaryCritic(critic_field="listing", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="cursor", weight=0.1),
            BinaryCritic(critic_field="time_range", weight=0.2),
        ],
    )

    suite.add_case(
        name="reddit_get_posts_in_subreddit_2",
        user_message="Get the next 5 posts from AskReddit that are contentious at this moment.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_posts_in_subreddit,
                args={
                    "subreddit": "AskReddit",
                    "listing": SubredditListingType.CONTROVERSIAL.value,
                    "limit": 5,
                    "cursor": "t3_1abcdef",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="subreddit", weight=0.2),
            BinaryCritic(critic_field="listing", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="cursor", weight=0.3),
            BinaryCritic(critic_field="time_range", weight=0.2),
        ],
        additional_messages=get_post_in_subreddit_messages,
    )

    suite.add_case(  # time-based listing, but don't provide a specific time range
        name="reddit_get_posts_in_subreddit_3",
        user_message="Get 5 top posts from AskReddit",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_posts_in_subreddit,
                args={
                    "subreddit": "AskReddit",
                    "listing": SubredditListingType.TOP.value,
                    "limit": 5,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="subreddit", weight=0.3),
            BinaryCritic(critic_field="listing", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.3),
        ],
    )

    suite.add_case(
        name="reddit_get_posts_in_subreddit_4",
        user_message="Get posts from AskReddit that are gaining traction as we speak",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_posts_in_subreddit,
                args={
                    "subreddit": "AskReddit",
                    "listing": SubredditListingType.RISING.value,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="subreddit", weight=0.3),
            BinaryCritic(critic_field="listing", weight=0.7),
        ],
    )

    return suite


@tool_eval()
def reddit_get_content_of_post_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_get_content_of_post",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="reddit_get_content_of_post_1",
        user_message="Get the content of the post with the id t3_1abcdef",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_content_of_post,
                args={
                    "post_identifier": [  # post_identifier can be any of the following
                        "1abcdef",
                        "t3_1abcdef",
                        "https://www.reddit.com/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                        "/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                    ],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            AnyOfCritic(
                critic_field="post_identifier",
                weight=1.0,
            ),
        ],
        additional_messages=get_post_in_subreddit_messages,
    )

    return suite


@tool_eval()
def reddit_get_content_of_multiple_posts_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_get_content_of_multiple_posts",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="reddit_get_content_of_multiple_posts_1",
        user_message=(
            "Get the content of the posts t3_1abcdef, "
            "https://www.reddit.com/r/AskReddit/comments/1jdfgk1vn/why_is_water_wet/, "
            "t3_3abcdef, t3_4abcdef, and t3_5abcdef, t3_6abcdef, and t3_7abcdef, 4jfnsklf, "
            "/r/AskReddit/comments/2dsghr/, and /r/AskReddit/comments/1jdfg35dvn/"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_content_of_multiple_posts,
                args={
                    "post_identifiers": [
                        "t3_1abcdef",
                        "https://www.reddit.com/r/AskReddit/comments/1jdfgk1vn/why_is_water_wet/",
                        "t3_3abcdef",
                        "t3_4abcdef",
                        "t3_5abcdef",
                        "t3_6abcdef",
                        "t3_7abcdef",
                        "4jfnsklf",
                        "/r/AskReddit/comments/2dsghr/",
                        "/r/AskReddit/comments/1jdfg35dvn/",
                    ],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ListCritic(
                critic_field="post_identifiers",
                weight=1.0,
                order_matters=False,
                duplicates_matter=True,
            ),
        ],
    )

    return suite


@tool_eval()
def reddit_get_top_level_comments_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_get_top_level_comments",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="reddit_get_top_level_comments_1",
        user_message="What are people saying in response?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_top_level_comments,
                args={
                    "post_identifier": [  # post_identifier can be any of the following
                        "1abcdef",
                        "t3_1abcdef",
                        "https://www.reddit.com/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                        "/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                    ],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            AnyOfCritic(
                critic_field="post_identifier",
                weight=1.0,
            ),
        ],
        additional_messages=get_post_in_subreddit_messages,
    )

    return suite
