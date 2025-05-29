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
from arcade_asana.tools import create_tag, list_tags

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def list_tags_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="list tags eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List tags",
        user_message="List the tags in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tags,
                args={
                    "limit": 100,
                    "offset": None,
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
        name="List tags with limit",
        user_message="List 10 tags in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tags,
                args={
                    "limit": 10,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.75),
            BinaryCritic(critic_field="offset", weight=0.25),
        ],
    )

    suite.add_case(
        name="List tags with pagination",
        user_message="Show me the next 2 tags.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tags,
                args={
                    "limit": 2,
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
            {"role": "user", "content": "Show me 2 tags in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListTags",
                            "arguments": '{"limit":2}',
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
                            "name": "Tag Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Tag World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListTags",
            },
            {
                "role": "assistant",
                "content": "Here are two tags in Asana:\n\n1. Tag Hello\n2. Tag World",
            },
        ],
    )

    suite.add_case(
        name="List tags with pagination changing the limit",
        user_message="Show me the next 5 tags.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tags,
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
            {"role": "user", "content": "Show me 5 tags in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListTags",
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
                            "name": "Tag Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Tag World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListTags",
            },
            {
                "role": "assistant",
                "content": "Here are two tags in Asana:\n\n1. Tag Hello\n2. Tag World",
            },
        ],
    )

    return suite


@tool_eval()
def create_tag_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="create tag eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create tag",
        user_message="Create a 'Hello World' tag in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_tag,
                args={
                    "name": "Hello World",
                    "description": None,
                    "color": None,
                    "workspace_id": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=0.7),
            BinaryCritic(critic_field="description", weight=0.1),
            BinaryCritic(critic_field="color", weight=0.1),
            BinaryCritic(critic_field="workspace_id", weight=0.1),
        ],
    )

    suite.add_case(
        name="Create tag with description and color",
        user_message="Create a dark orange tag 'Attention' in Asana with the description 'This is a tag for important tasks'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_tag,
                args={
                    "name": "Attention",
                    "description": "This is a tag for important tasks",
                    "color": "dark-orange",
                    "workspace_id": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="description", weight=0.3),
            BinaryCritic(critic_field="color", weight=0.3),
            BinaryCritic(critic_field="workspace_id", weight=0.1),
        ],
    )

    suite.add_case(
        name="Create tag in a specific workspace",
        user_message="Create a dark orange tag 'Attention' in Asana with the description 'This is a tag for important tasks' in the workspace '1234567890'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_tag,
                args={
                    "name": "Attention",
                    "description": "This is a tag for important tasks",
                    "color": "dark-orange",
                    "workspace_id": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=0.25),
            BinaryCritic(critic_field="description", weight=0.25),
            BinaryCritic(critic_field="color", weight=0.25),
            BinaryCritic(critic_field="workspace_id", weight=0.25),
        ],
    )

    return suite
