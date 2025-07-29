from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import SimilarityCritic
from arcade_tdk import ToolCatalog

import arcade_todoist
from arcade_todoist.tools.projects import get_projects
from arcade_todoist.tools.tasks import (
    close_task,
    close_task_by_task_id,
    create_task,
    delete_task,
    delete_task_by_task_id,
    get_all_tasks,
    get_tasks_by_project_id,
    get_tasks_by_project_name,
)

rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_todoist)


@tool_eval()
def todoist_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="todoist Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to todoist tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Getting the projects",
        user_message="Get all my projects",
        expected_tool_calls=[ExpectedToolCall(func=get_projects, args={})],
        rubric=rubric,
        critics=[],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting all the tasks",
        user_message="Get all my tasks from across the board",
        expected_tool_calls=[ExpectedToolCall(func=get_all_tasks, args={})],
        rubric=rubric,
        critics=[],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting tasks from a specific project with project id",
        user_message="What are my tasks in the project with id '12345'?",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_project_id, args={"project_id": "12345"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="project_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting tasks from a specific project with project name",
        user_message="What do I have left to do in the 'Personal' project?",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_project_name, args={"project_name": "Personal"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="project_name", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Create a task for the inbox",
        user_message="Hey! create a task to 'Buy groceries'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task, args={"description": "Buy groceries", "project_id": None}
            )
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="description", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Create a task for the a specific project",
        user_message="Hey! create a task to 'Check the email' in the 'Personal' project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task,
                args={"description": "Check the email", "project_name": "Personal"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="description", weight=0.5),
            SimilarityCritic(critic_field="project_name", weight=0.5),
        ],
        additional_messages=[],
    )

    suite.add_case(
        name="Close a task by ID",
        user_message="Mark task with ID '12345' as completed",
        expected_tool_calls=[
            ExpectedToolCall(func=close_task_by_task_id, args={"task_id": "12345"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Close a task by Name",
        user_message="I'm done with the task 'Buy groceries'",
        expected_tool_calls=[
            ExpectedToolCall(func=close_task, args={"task_description": "Buy groceries"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_description", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Complete a task by id",
        user_message="Please close task with id abc123, I finished it",
        expected_tool_calls=[
            ExpectedToolCall(func=close_task_by_task_id, args={"task_id": "abc123"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Delete a task by ID",
        user_message="Delete task with ID 'task_456'",
        expected_tool_calls=[
            ExpectedToolCall(func=delete_task_by_task_id, args={"task_id": "task_456"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Remove a task by name",
        user_message="I want to remove task Wash car completely",
        expected_tool_calls=[
            ExpectedToolCall(func=delete_task, args={"task_description": "Wash car"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_description", weight=1)],
        additional_messages=[],
    )

    # Pagination test cases
    suite.add_case(
        name="Getting limited number of all tasks",
        user_message="Get only 10 of my tasks from across the board",
        expected_tool_calls=[ExpectedToolCall(func=get_all_tasks, args={"limit": 10})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="limit", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting limited tasks from specific project",
        user_message="Show me only 5 tasks from the 'Work' project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_by_project_name, 
                args={"project_name": "Work", "limit": 5}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="project_name", weight=0.5),
            SimilarityCritic(critic_field="limit", weight=0.5)
        ],
        additional_messages=[],
    )

    return suite
