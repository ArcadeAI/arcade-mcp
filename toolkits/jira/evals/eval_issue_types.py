import json

from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.tools.issues import (
    get_issue_type_by_id,
    list_issue_types_by_project,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_jira)


@tool_eval()
def list_issue_types_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="List issue types eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List issue types in a project (ID)",
        user_message="List the issue types in the project with ID '1234567890'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issue_types_by_project,
                args={
                    "project": "1234567890",
                    "limit": 200,
                    "offset": 0,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=0.8),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="List issue types in a project (Key)",
        user_message="List the issue types in the project PRJ-1.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issue_types_by_project,
                args={
                    "project": "PRJ-1",
                    "limit": 200,
                    "offset": 0,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=0.8),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="List issue types in a project (name)",
        user_message="List the issue types in the project 'Engineering'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issue_types_by_project,
                args={
                    "project": "Engineering",
                    "limit": 200,
                    "offset": 0,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=0.8),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="List issue types in a project (name) with pagination in the prompt",
        user_message="List 10 issue types in the project 'Engineering'. Skip the first 30 items.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issue_types_by_project,
                args={
                    "project": "Engineering",
                    "limit": 10,
                    "offset": 30,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="offset", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="List issue types in a project (name) with pagination from chat history",
        user_message="Get the next items.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issue_types_by_project,
                args={
                    "project": "Engineering",
                    "limit": 2,
                    "offset": 2,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="offset", weight=1 / 3),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "List 2 issue types in the project 'Engineering'.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Jira_ListIssueTypesByProject",
                            "arguments": json.dumps({
                                "project": "Engineering",
                                "limit": 2,
                                "offset": 0,
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "project": {
                        "id": "10000",
                        "key": "Eng-1",
                        "name": "Engineering",
                    },
                    "issue_types": [
                        {
                            "id": "10001",
                            "name": "Bug",
                            "description": (
                                "A bug is an error or flaw in a software application or website."
                            ),
                        },
                        {
                            "id": "10002",
                            "name": "Task",
                            "description": "A task is a unit of work that needs to be completed.",
                        },
                    ],
                    "pagination": {
                        "limit": 2,
                        "total_results": 2,
                        "next_offset": 2,
                    },
                }),
                "tool_call_id": "call_1",
                "name": "Jira_ListIssueTypesByProject",
            },
            {
                "role": "assistant",
                "content": (
                    "Here are two issue types in the project 'Engineering':\n\n1. Bug\n2. Task"
                ),
            },
        ],
    )

    return suite


@tool_eval()
def get_issue_type_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Get issue type by ID eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get issue type by ID",
        user_message="Get the issue type with ID '10001'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_type_by_id,
                args={
                    "issue_type": "10001",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=0.8),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    return suite
