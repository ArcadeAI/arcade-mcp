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
from arcade_jira.critics import CaseInsensitiveBinaryCritic, HasSubstringCritic
from arcade_jira.tools.issues import (
    get_issue_by_id,
    get_issues_without_id,
    list_issues,
    search_issues_with_jql,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_jira)


@tool_eval()
def get_issue_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Get issue by ID eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get issue by ID",
        user_message="Get the issue with ID '10000'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_by_id,
                args={
                    "issue_id": "10000",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get issue by Key",
        user_message="Get the issue ENG-103.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_by_id,
                args={
                    "issue_id": "ENG-103",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue_id", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def get_issues_without_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Get issues without an ID",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks. "
            "Today is 2025-05-27 (Tuesday)."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get issues by keywords",
        user_message="Find the issue about implementing the message queue.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "keywords": "message queue",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            HasSubstringCritic(critic_field="keywords", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get issues by due date",
        user_message="Which issues are due this month?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "due_from": "2025-05-01",
                    "due_until": "2025-05-31",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="due_from", weight=0.5),
            BinaryCritic(critic_field="due_until", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get issues by assignee, due date, status, priority and issue type",
        user_message=(
            "Find task issues assigned to John Doe that are in progress, "
            "with high priority, and due until the end of this month"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "assignee": "John Doe",
                    "due_from": None,
                    "due_until": "2025-05-31",
                    "status": "in progress",
                    "priority": "high",
                    "issue_type": "task",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="due_from", weight=0.1),
            BinaryCritic(critic_field="due_until", weight=0.1),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=0.2),
            CaseInsensitiveBinaryCritic(critic_field="status", weight=0.2),
            CaseInsensitiveBinaryCritic(critic_field="priority", weight=0.2),
            CaseInsensitiveBinaryCritic(critic_field="issue_type", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get issues by label and project name",
        user_message="Find issues labeled with version 2 in the Engineering project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "project": "Engineering",
                    "labels": ["version 2"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="project", weight=0.5),
            BinaryCritic(critic_field="labels", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get issues by parent issue",
        user_message="Get the children issues of ENG-123",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "parent_issue": "ENG-123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="parent_issue", weight=1.0),
        ],
    )

    suite.add_case(
        name="Paginate issues in multiple chat turns",
        user_message="Get the next page of issues",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issues_without_id,
                args={
                    "assignee": "john doe",
                    "priority": "high",
                    "status": "in progress",
                    "issue_type": "task",
                    "limit": 2,
                    "offset": 4,
                    "next_page_token": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="priority", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="status", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="issue_type", weight=1 / 7),
            BinaryCritic(critic_field="limit", weight=1 / 7),
            BinaryCritic(critic_field="offset", weight=1 / 7),
            BinaryCritic(critic_field="next_page_token", weight=1 / 7),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": (
                    "Find 2 tasks assigned to John Doe that are in progress, with high priority"
                ),
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Jira_GetIssuesWithoutId",
                            "arguments": json.dumps({
                                "assignee": "John Doe",
                                "priority": "high",
                                "status": "in progress",
                                "issue_type": "task",
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
                    "issues": [
                        {
                            "id": "10001",
                            "key": "ENG-101",
                            "summary": "Implement the message queue",
                            "assignee": {
                                "id": "10010",
                                "name": "John Doe",
                                "email": "john.doe@example.com",
                            },
                            "status": {
                                "id": "10020",
                                "name": "In Progress",
                            },
                            "priority": {
                                "id": "10030",
                                "name": "High",
                            },
                            "issue_type": {
                                "id": "10040",
                                "name": "Task",
                            },
                            "project": {
                                "id": "10050",
                                "key": "ENG",
                                "name": "Engineering",
                            },
                        },
                        {
                            "id": "10002",
                            "key": "ENG-102",
                            "summary": "Deploy the message queue system",
                            "assignee": {
                                "id": "10010",
                                "name": "John Doe",
                                "email": "john.doe@example.com",
                            },
                            "status": {
                                "id": "10020",
                                "name": "In Progress",
                            },
                            "priority": {
                                "id": "10030",
                                "name": "High",
                            },
                            "issue_type": {
                                "id": "10040",
                                "name": "Task",
                            },
                            "project": {
                                "id": "10050",
                                "key": "ENG",
                                "name": "Engineering",
                            },
                        },
                    ],
                    "pagination": {
                        "limit": 2,
                        "total_results": 2,
                        "next_page_token": "1234567890",
                    },
                }),
                "tool_call_id": "call_1",
                "name": "Jira_GetIssuesWithoutId",
            },
            {
                "role": "assistant",
                "content": (
                    "Here are two issues:\n\n"
                    "1. ENG-101: Implement the message queue\n"
                    "2. ENG-102: Deploy the message queue system"
                ),
            },
        ],
    )

    return suite


@tool_eval()
def search_issues_with_jql_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Search issues with JQL",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks. "
            "Today is 2025-05-27 (Tuesday)."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    jql_query_str = 'text ~ "message queue" AND dueDate <= 2025-05-31'

    suite.add_case(
        name="Search issues by keywords",
        user_message=f"Search for up to 10 issues using the JQL query: {jql_query_str}",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues_with_jql,
                args={
                    "jql": jql_query_str,
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            HasSubstringCritic(critic_field="jql", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="offset", weight=1 / 3),
        ],
    )

    return suite


@tool_eval()
def list_issues_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="List issues eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get me any one issue in Jira",
        user_message="Get me one issue in Jira.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issues,
                args={
                    "limit": 1,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="next_page_token", weight=0.5),
        ],
    )

    suite.add_case(
        name="List 10 issues in Jira",
        user_message="List 10 issues in Jira.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issues,
                args={
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="next_page_token", weight=0.5),
        ],
    )

    suite.add_case(
        name="List 10 issues in the Arcade project",
        user_message="List 10 issues in the Arcade project.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_issues,
                args={
                    "project": "Arcade",
                    "limit": 50,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="project", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="next_page_token", weight=1 / 3),
        ],
    )

    return suite
