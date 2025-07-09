from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic, NumericCritic, SimilarityCritic
from arcade_tdk import ToolCatalog

import arcade_mastodon
from arcade_mastodon.tools.statuses import (
    delete_status_by_id,
    lookup_status_by_id,
    post_status,
    search_recent_statuses_by_keywords,
    search_recent_statuses_by_username,
)
from arcade_mastodon.tools.users import lookup_single_user_by_username

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_mastodon)


@tool_eval()
def mastodon_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="mastodon Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to mastodon tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Lookup a user by username",
        user_message="Please lookup the user with the username @techblogger",
        expected_tool_calls=[
            ExpectedToolCall(func=lookup_single_user_by_username, args={"username": "techblogger"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="username", weight=1.0),
        ],
    )

    suite.add_case(
        name="Posting a status",
        user_message="Post a status to Mastodon saying 'Hello, world from an AI assistant!'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=post_status, args={"status": "Hello, world from an AI assistant!"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="status", weight=1.0),
        ],
    )

    suite.add_case(
        name="Delete a status by ID",
        user_message="Please delete the status with the ID 1234567890",
        expected_tool_calls=[
            ExpectedToolCall(func=delete_status_by_id, args={"status_id": "1234567890"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="status_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="Lookup a status by ID",
        user_message="Please lookup the status with the ID 1234567890",
        expected_tool_calls=[
            ExpectedToolCall(func=lookup_status_by_id, args={"status_id": "1234567890"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="status_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search for statuses by username",
        user_message="Show me the last 10 statuses from the user @techblogger",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_statuses_by_username,
                args={"username": "techblogger", "limit": 10},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="username", weight=0.5),
            NumericCritic(critic_field="limit", weight=0.5, value_range=(9, 11)),
        ],
    )

    suite.add_case(
        name="Search for statuses by username with default limit",
        user_message="Show me the last statuses from the user @techblogger",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_statuses_by_username, args={"username": "techblogger"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="username", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search for statuses by keywords",
        user_message="Show me the last statuses with the keywords 'mastodon' and 'ai'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_recent_statuses_by_keywords, args={"keywords": ["mastodon", "ai"]}
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1.0),
        ],
    )

    return suite
