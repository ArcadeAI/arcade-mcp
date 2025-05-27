from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade.sdk.eval.critic import BinaryCritic

import arcade_jira
from arcade_jira.critics import (
    CaseInsensitiveBinaryCritic,
    CaseInsensitiveListOfStringsBinaryCritic,
)
from arcade_jira.tools.issues import (
    create_issue,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_jira)


@tool_eval()
def create_issue_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Create issue eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create issue",
        user_message="Create a 'High' priority task for John Doe with the following properties: "
        "title: 'Test issue', "
        "description: 'This is a test issue', "
        "project: 'ENG-123', "
        "issue_type: 'Task', "
        "due on '2025-06-30'. "
        "Label it with Hello and World.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "Test issue",
                    "description": "This is a test issue",
                    "project": "ENG-123",
                    "issue_type": "Task",
                    "priority": "High",
                    "assignee": "John Doe",
                    "due_date": "2025-06-30",
                    "labels": ["Hello", "World"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="title", weight=1 / 8),
            CaseInsensitiveBinaryCritic(critic_field="description", weight=1 / 8),
            CaseInsensitiveBinaryCritic(critic_field="project", weight=1 / 8),
            CaseInsensitiveBinaryCritic(critic_field="issue_type", weight=1 / 8),
            CaseInsensitiveBinaryCritic(critic_field="priority", weight=1 / 8),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=1 / 8),
            BinaryCritic(critic_field="due_date", weight=1 / 8),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=1 / 8),
        ],
    )

    suite.add_case(
        name="Create issue with parent and reporter",
        user_message=(
            "Create a task for John Doe to 'Implement message queue service' as a child of the issue ENG-321 "
            "and reported by Jenifer Bear. It should be due on 2025-06-30. Label it with 'Project XYZ'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "Implement message queue service",
                    "parent_issue_id": "ENG-321",
                    "issue_type": "Task",
                    "assignee": "John Doe",
                    "reporter": "Jenifer Bear",
                    "due_date": "2025-06-30",
                    "labels": ["Project XYZ"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="title", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="parent_issue_id", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="issue_type", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="reporter", weight=1 / 7),
            BinaryCritic(critic_field="due_date", weight=1 / 7),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=1 / 7),
        ],
    )

    return suite
