from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_reddit
from arcade_reddit.tools import (
    submit_text_post,
)
from arcade_reddit.tools.submit import comment_on_post
from evals.additional_messages import get_post_in_subreddit_messages
from evals.critics import AnyOfCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_reddit)


@tool_eval()
def reddit_submit_text_post_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_submit_text_post_1",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="reddit_submit_text_post_1",
        user_message=(
            "Post this in AskReddit - 'Why is the sky blue?'. I dont want replies sent to my dms"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=submit_text_post,
                args={
                    "subreddit": "AskReddit",
                    "title": "Why is the sky blue?",
                    "send_replies": False,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="subreddit", weight=0.3),
            BinaryCritic(critic_field="title", weight=0.3),
            BinaryCritic(critic_field="body", weight=0.3),
            BinaryCritic(critic_field="send_replies", weight=0.1),
        ],
    )

    return suite


@tool_eval()
def reddit_comment_on_post_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="reddit_comment_on_post_1",
        system_message=(
            "You are an AI assistant with access to reddit tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    comment = "Your dog's four-legged structure is a manifestation of tetrapodal evolution, where natural selection has optimized limb development for biomechanical stability and efficient terrestrial locomotion. Duh!"  # noqa: E501
    suite.add_case(
        name="reddit_comment_on_post_1",
        user_message=(f"here's my comment - {comment}"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=comment_on_post,
                args={
                    "post_identifier": [  # post_identifier can be any of the following
                        "1abcdef",
                        "t3_1abcdef",
                        "https://www.reddit.com/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                        "/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/",
                    ],
                    "text": comment,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            AnyOfCritic(critic_field="post_identifier", weight=0.5),
            SimilarityCritic(critic_field="text", weight=0.5),
        ],
        additional_messages=get_post_in_subreddit_messages,
    )

    return suite
