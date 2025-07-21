from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.chat import list_chats

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def list_chats_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools listing chats in Teams."""
    suite = EvalSuite(
        name="Teams Chat Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get a list of my chats",
        user_message="Get a list of my chats",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_chats,
                args={
                    "limit": 50,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="next_page_token", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get a list of 10 chats",
        user_message="Get a list of 10 chats",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_chats,
                args={
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="next_page_token", weight=0.5),
        ],
    )

    return suite
