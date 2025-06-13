from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.critics import (
    CaseInsensitiveBinaryCritic,
    CaseInsensitiveListOfStringsBinaryCritic,
)
from arcade_jira.tools.issues import (
    add_labels_to_issue,
    create_issue,
    remove_labels_from_issue,
    update_issue,
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
            "Create a task for John Doe to 'Implement message queue service' "
            "as a child of the issue ENG-321 and reported by Jenifer Bear. "
            "It should be due on 2025-06-30. "
            "Label it with 'Project XYZ'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "Implement message queue service",
                    "parent_issue": "ENG-321",
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
            CaseInsensitiveBinaryCritic(critic_field="parent_issue", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="issue_type", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=1 / 7),
            CaseInsensitiveBinaryCritic(critic_field="reporter", weight=1 / 7),
            BinaryCritic(critic_field="due_date", weight=1 / 7),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=1 / 7),
        ],
    )

    return suite


@tool_eval()
def labels_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Labels eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Add labels",
        user_message="Add the labels 'Hello' and 'World' to the issue ENG-123.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_labels_to_issue,
                args={
                    "issue": "ENG-123",
                    "labels": ["Hello", "World"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=0.5),
        ],
    )

    suite.add_case(
        name="Add labels without notifying watchers",
        user_message=(
            "Add the labels 'Hello' and 'World' to the issue ENG-123. Do not notify watchers."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_labels_to_issue,
                args={
                    "issue": "ENG-123",
                    "labels": ["Hello", "World"],
                    "notify_watchers": False,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1 / 3),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=1 / 3),
            BinaryCritic(critic_field="notify_watchers", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Remove labels",
        user_message="Remove the labels 'Hello' and 'World' from the issue ENG-123.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=remove_labels_from_issue,
                args={
                    "issue": "ENG-123",
                    "labels": ["Hello", "World"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=0.5),
        ],
    )

    suite.add_case(
        name="Remove labels without notifying watchers",
        user_message=(
            "Remove the labels 'Hello' and 'World' from the issue ENG-123. Do not notify watchers."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=remove_labels_from_issue,
                args={
                    "issue": "ENG-123",
                    "labels": ["Hello", "World"],
                    "notify_watchers": False,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1 / 3),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=1 / 3),
            BinaryCritic(critic_field="notify_watchers", weight=1 / 3),
        ],
    )

    return suite


@tool_eval()
def update_issue_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Update issue eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Update issue with new assignee",
        user_message="Change the assignee of the ENG-123 issue to John Doe.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "assignee": "John Doe",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update issue with new priority",
        user_message="Set the priority of the ENG-123 issue to high.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "priority": "High",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="priority", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update issue with new due date",
        user_message="Set the due date of the ENG-123 issue to 2025-06-30.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "due_date": "2025-06-30",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="due_date", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update issue with new labels",
        user_message="Change the labels in the ENG-123 issue to 'Hello' and 'World'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "labels": ["Hello", "World"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveListOfStringsBinaryCritic(critic_field="labels", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update issue with new title and description",
        user_message=(
            "Change the title and description of the ENG-123 issue to 'Test issue' "
            "and 'This is a test issue'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "title": "Test issue",
                    "description": "This is a test issue",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1 / 3),
            CaseInsensitiveBinaryCritic(critic_field="title", weight=1 / 3),
            CaseInsensitiveBinaryCritic(critic_field="description", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Clear due date",
        user_message="Clear the due date of the issue ENG-123.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "due_date": "",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="due_date", weight=0.5),
        ],
    )

    suite.add_case(
        name="Remove assignee",
        user_message="Remove the assignee from the issue ENG-123.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "assignee": "",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=0.5),
        ],
    )

    suite.add_case(
        name="Remove assignee",
        user_message="Remove the assignee from the issue ENG-123 without notifying anyone.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue": "ENG-123",
                    "assignee": "",
                    "notify_watchers": False,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1 / 3),
            CaseInsensitiveBinaryCritic(critic_field="assignee", weight=1 / 3),
            BinaryCritic(critic_field="notify_watchers", weight=1 / 3),
        ],
    )

    return suite
