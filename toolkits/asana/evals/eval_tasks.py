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
from arcade_asana.constants import SortOrder, TaskSortBy
from arcade_asana.tools import (
    get_subtasks_from_a_task,
    get_task_by_id,
    get_tasks_without_id,
    update_task,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def get_task_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get task by id eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get task by id",
        user_message="Get the task with id '1234567890' in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_task_by_id,
                args={
                    "task_id": "1234567890",
                    "max_subtasks": 100,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.8),
            BinaryCritic(critic_field="max_subtasks", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get task by id with subtasks limit",
        user_message="Get the task with id '1234567890' in Asana with up to 10 subtasks.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_task_by_id,
                args={
                    "task_id": "1234567890",
                    "max_subtasks": 10,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="max_subtasks", weight=0.5),
        ],
    )

    return suite


@tool_eval()
def get_subtasks_from_a_task_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get subtasks from a task eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get subtasks from a task",
        user_message="Get the next 2 subtasks.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_subtasks_from_a_task,
                args={
                    "task_id": "1234567890",
                    "limit": 2,
                    "offset": "abc123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="offset", weight=1 / 3),
        ],
        additional_messages=[
            {"role": "user", "content": "Get 2 subtasks from the task '1234567890'."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_GetSubtasksFromATask",
                            "arguments": '{"task_id":"1234567890","limit":2}',
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
                    "subtasks": [
                        {
                            "id": "1234567890",
                            "name": "Subtask Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Subtask World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_GetSubtasksFromATask",
            },
            {
                "role": "assistant",
                "content": "Here are two subtasks in Asana:\n\n1. Subtask Hello\n2. Subtask World",
            },
        ],
    )

    return suite


@tool_eval()
def search_tasks_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="search tasks eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search tasks by name",
        user_message="Search for the task 'Hello' in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1),
        ],
    )

    suite.add_case(
        name="Search tasks by name with custom sorting",
        user_message="Search for the task 'Hello' in Asana sorting by likes in descending order.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "sort_by": TaskSortBy.LIKES,
                    "sort_order": SortOrder.DESCENDING,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1 / 3),
            BinaryCritic(critic_field="sort_by", weight=1 / 3),
            BinaryCritic(critic_field="sort_order", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by project ID",
        user_message="Search for the task 'Hello' associated to the project with ID '1234567890'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "project_id": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="project_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by project name",
        user_message="Search for the task 'Hello' associated to the project named 'My Project'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "project_name": "My Project",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="project_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by team ID",
        user_message="Search for the task 'Hello' associated to the team with ID '1234567890'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "team_id": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="team_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by tag IDs",
        user_message="Search for the task 'Hello' associated to the tags with IDs '1234567890' and '1234567891'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "tags": ["1234567890", "1234567891"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="tag_ids", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by tags names",
        user_message="Search for the task 'Hello' associated to the tags 'My Tag' and 'My Other Tag'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "tags": ["My Tag", "My Other Tag"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="tag_names", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by start and due dates",
        user_message="Search for tasks 'Hello' that started on '2025-01-01' and are due on '2025-01-02'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "start_on": "2025-01-01",
                    "due_on": "2025-01-02",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1 / 3),
            BinaryCritic(critic_field="start_on", weight=1 / 3),
            BinaryCritic(critic_field="due_on", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Search tasks by name filtering by start and due dates",
        user_message="Search for tasks 'Hello' that start on 2025-05-05 and are due on or before 2025-05-11.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "start_on": "2025-05-05",
                    "due_on_or_before": "2025-05-11",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1 / 3),
            BinaryCritic(critic_field="start_on", weight=1 / 3),
            BinaryCritic(critic_field="due_on_or_before", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Search not-completed tasks by name filtering by due date",
        user_message="Search for tasks 'Hello' that are not completed and are due on or before 2025-05-11.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_without_id,
                args={
                    "keywords": "Hello",
                    "due_on_or_before": "2025-05-11",
                    "completed": False,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=1 / 3),
            BinaryCritic(critic_field="due_on_or_before", weight=1 / 3),
            BinaryCritic(critic_field="completed", weight=1 / 3),
        ],
    )

    return suite


@tool_eval()
def update_task_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="update task eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Update task name",
        user_message="Update the task '1234567890' with the name 'Hello World'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_task,
                args={"task_id": "1234567890", "name": "Hello World"},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update task as completed",
        user_message="Mark the task '1234567890' as completed.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_task,
                args={"task_id": "1234567890", "completed": True},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="completed", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update task with new parent task",
        user_message="Update the task '1234567890' with the parent task '1234567891'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_task,
                args={"task_id": "1234567890", "parent_task_id": "1234567891"},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="parent_task_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update task with new assignee",
        user_message="Update the task '1234567890' with the assignee '1234567891'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_task,
                args={"task_id": "1234567890", "assignee_id": "1234567891"},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="assignee_id", weight=0.5),
        ],
    )

    return suite
