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
from arcade_asana.tools import get_project_by_id, list_projects

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def list_projects_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="list projects eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List projects",
        user_message="List the projects in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_projects,
                args={
                    "team_ids": None,
                    "limit": 100,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="team_ids", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    suite.add_case(
        name="List projects filtering by teams",
        user_message="List the projects in Asana for the team '1234567890'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_projects,
                args={
                    "team_ids": ["1234567890"],
                    "limit": 100,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="team_ids", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.2),
        ],
    )

    suite.add_case(
        name="List projects with limit",
        user_message="List 10 projects in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_projects,
                args={
                    "team_ids": None,
                    "limit": 10,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="team_ids", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.6),
            BinaryCritic(critic_field="offset", weight=0.2),
        ],
    )

    suite.add_case(
        name="List projects with pagination",
        user_message="Show me the next 2 projects.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_projects,
                args={
                    "limit": 2,
                    "offset": "abc123",
                    "team_ids": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.45),
            BinaryCritic(critic_field="offset", weight=0.45),
            BinaryCritic(critic_field="team_ids", weight=0.1),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 projects in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListProjects",
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
                            "name": "Project Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Project World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListProjects",
            },
            {
                "role": "assistant",
                "content": "Here are two projects in Asana:\n\n1. Project Hello\n2. Project World",
            },
        ],
    )

    return suite


@tool_eval()
def get_project_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get project by id eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get project by id",
        user_message="Get the project with id '1234567890' in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_project_by_id,
                args={
                    "project_id": "1234567890",
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

    return suite
