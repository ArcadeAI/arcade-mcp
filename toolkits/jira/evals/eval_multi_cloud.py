import json
import uuid

from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.tools.comments import get_issue_comments
from arcade_jira.tools.issues import get_issue_by_id

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_jira)


@tool_eval()
def multi_cloud_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Atlassian multi-cloud evaluation suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Test calling tool without specifying a cloud id",
        user_message="Get the issue with ID '10000'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_by_id,
                args={
                    "issue_id": "10000",
                    "atlassian_cloud_id": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="atlassian_cloud_id", weight=0.5),
        ],
    )

    cloud_id = str(uuid.uuid4())

    suite.add_case(
        name="Test calling tool specifying a cloud id directly with the request",
        user_message=f"Get the issue with ID '10000' in the Cloud with ID '{cloud_id}'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_by_id,
                args={
                    "issue_id": "10000",
                    "atlassian_cloud_id": cloud_id,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="atlassian_cloud_id", weight=0.5),
        ],
    )

    cloud_1_id = str(uuid.uuid4())
    cloud_2_id = str(uuid.uuid4())
    available_clouds = [
        {"id": cloud_1_id, "name": "Foobar", "url": "https://foobar.atlassian.com"},
        {"id": cloud_2_id, "name": "Quick Brown Fox", "url": "https://quickbrownfox.atlassian.com"},
    ]
    available_clouds_str = json.dumps(available_clouds)

    suite.add_case(
        name="Test calling tool with multiple clouds error and specifying which cloud to use",
        user_message="Let's use the Foobar Cloud",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_by_id,
                args={
                    "issue_id": "10000",
                    "atlassian_cloud_id": cloud_1_id,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="atlassian_cloud_id", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Get the issue with id '10000' in Jira"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Jira_GetIssueById",
                            "arguments": json.dumps({
                                "issue": "10000",
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "name": "retryable_tool_call_error",
                    "message": (
                        "Multiple Atlassian Clouds are available. One Cloud ID has to be selected "
                        "and provided in the tool call using the `atlassian_cloud_id` argument.",
                    ),
                    "developer_message": (
                        "Multiple Atlassian Clouds are available. One Cloud ID has to be selected "
                        "and provided in the tool call using the `atlassian_cloud_id` argument.",
                    ),
                    "additional_prompt_content": (
                        f"Available Atlassian Clouds:\n\n```json\n{available_clouds_str}\n```"
                    ),
                }),
                "tool_call_id": "call_1",
                "name": "Jira_GetIssueById",
            },
            {
                "role": "assistant",
                "content": (
                    "Here is the list of available Atlassian clouds:\n\n"
                    "1. **Name:** Foobar\n"
                    "   - **URL:** https://foobar.atlassian.com\n"
                    "2. **Name:** Quick Brown Fox\n"
                    "   - **URL:** https://quickbrownfox.atlassian.com\n"
                    "Please select one of the above Clouds to get the Jira issue."
                ),
            },
        ],
    )

    suite.add_case(
        name="Test calling tool one interaction after specifying a cloud id",
        user_message="Get the comments on this issue",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue_comments,
                args={
                    "issue": "10000",
                    "atlassian_cloud_id": cloud_1_id,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="issue", weight=0.5),
            BinaryCritic(critic_field="atlassian_cloud_id", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Get the issue with id '10000' in Jira"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Jira_GetIssueById",
                            "arguments": json.dumps({
                                "issue": "10000",
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "name": "retryable_tool_call_error",
                    "message": (
                        "Multiple Atlassian Clouds are available. One Cloud ID has to be selected "
                        "and provided in the tool call using the `atlassian_cloud_id` argument.",
                    ),
                    "developer_message": (
                        "Multiple Atlassian Clouds are available. One Cloud ID has to be selected "
                        "and provided in the tool call using the `atlassian_cloud_id` argument.",
                    ),
                    "additional_prompt_content": (
                        f"Available Atlassian Clouds:\n\n```json\n{available_clouds_str}\n```"
                    ),
                }),
                "tool_call_id": "call_1",
                "name": "Jira_GetIssueById",
            },
            {
                "role": "assistant",
                "content": (
                    "Here is the list of available Atlassian clouds:\n\n"
                    "1. **Name:** Foobar\n"
                    "   - **URL:** https://foobar.atlassian.com\n"
                    "2. **Name:** Quick Brown Fox\n"
                    "   - **URL:** https://quickbrownfox.atlassian.com\n"
                    "Please select one of the above Clouds to get the Jira issue."
                ),
            },
            {"role": "user", "content": "Let's use the Foobar Cloud from now on."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "Jira_GetIssueById",
                            "arguments": json.dumps({
                                "issue": "10000",
                                "atlassian_cloud_id": cloud_1_id,
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "id": "10000",
                    "key": "ENG-101",
                    "assignee": {
                        "id": "10010",
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                    },
                    "description": "Implement the message queue",
                    "status": {
                        "id": "10020",
                        "name": "In Progress",
                    },
                    "issuetype": {
                        "id": "10030",
                        "name": "Task",
                    },
                    "project": {
                        "id": "10040",
                        "key": "ENG",
                        "name": "Engineering",
                    },
                }),
                "tool_call_id": "call_2",
                "name": "Jira_GetIssueById",
            },
            {
                "role": "assistant",
                "content": (
                    "Here is the issue:\n\n"
                    "1. **ID:** 10000\n"
                    "   - **Key:** ENG-101\n"
                    "   - **Assignee:** John Doe\n"
                    "   - **Description:** Implement the message queue\n"
                    "   - **Status:** In Progress\n"
                    "   - **Issue Type:** Task\n"
                    "   - **Project:** Engineering"
                ),
            },
        ],
    )

    return suite
