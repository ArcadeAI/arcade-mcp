import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_asana
from arcade_asana.tools import list_workspaces

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def list_workspaces_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="list workspaces eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List workspaces",
        user_message="List the workspaces in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_workspaces,
                args={
                    "limit": 100,
                    "offset": 0,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
    )

    suite.add_case(
        name="List workspaces with pagination",
        user_message="Show me the next 2 workspaces.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_workspaces,
                args={
                    "limit": 2,
                    "offset": 2,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 workspaces in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListWorkspaces",
                            "arguments": '{"limit":2}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 2,
                    "workspaces": [
                        {
                            "id": "1234567890",
                            "name": "Workspace Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Workspace World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListWorkspaces",
            },
            {
                "role": "assistant",
                "content": "Here are two workspaces in Asana:\n\n1. Workspace Hello\n2. Workspace World",
            },
        ],
    )

    suite.add_case(
        name="List workspaces with pagination changing the limit",
        user_message="Show me the next 5 workspaces.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_workspaces,
                args={
                    "limit": 5,
                    "offset": "abc123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 5 workspaces in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListWorkspaces",
                            "arguments": '{"limit":5}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 2,
                    "next_page": {
                        "has_more_results": True,
                        "next_page_token": "abc123",
                    },
                    "workspaces": [
                        {
                            "id": "1234567890",
                            "name": "Workspace Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Workspace World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListWorkspaces",
            },
            {
                "role": "assistant",
                "content": "Here are two workspaces in Asana:\n\n1. Workspace Hello\n2. Workspace World",
            },
        ],
    )

    return suite
