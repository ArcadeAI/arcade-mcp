import arcade_todoist
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic, SimilarityCritic
from arcade_tdk import ToolCatalog
from arcade_todoist.tools.projects import get_projects
from arcade_todoist.tools.tasks import (
    close_task,
    create_task,
    delete_task,
    get_all_tasks,
    get_tasks_by_filter,
    get_tasks_by_project,
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
            ExpectedToolCall(func=get_tasks_by_project, args={"project": "12345"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="project", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting tasks from a specific project with project name",
        user_message="What do I have left to do in the 'Personal' project?",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_project, args={"project": "Personal"})
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="project", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Create a task for the inbox",
        user_message="Hey! create a task to 'Buy groceries'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task, args={"description": "Buy groceries", "project": None}
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
                args={"description": "Check the email", "project": "Personal"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="description", weight=0.5),
            SimilarityCritic(critic_field="project", weight=0.5),
        ],
        additional_messages=[],
    )

    suite.add_case(
        name="Close a task by ID",
        user_message="Mark task with ID '12345' as completed",
        expected_tool_calls=[ExpectedToolCall(func=close_task, args={"task_id": "12345"})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Close a task by ID",
        user_message="I'm done with task ID 'task_456'",
        expected_tool_calls=[ExpectedToolCall(func=close_task, args={"task_id": "task_456"})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Complete a task by id",
        user_message="Please close task with id abc123, I finished it",
        expected_tool_calls=[ExpectedToolCall(func=close_task, args={"task_id": "abc123"})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Delete a task by ID",
        user_message="Delete task with ID 'task_456'",
        expected_tool_calls=[ExpectedToolCall(func=delete_task, args={"task_id": "task_456"})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Remove a task by ID",
        user_message="I want to remove task with ID task_789 completely",
        expected_tool_calls=[ExpectedToolCall(func=delete_task, args={"task_id": "task_789"})],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="task_id", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting limited number of all tasks",
        user_message="Get only 10 of my tasks from across the board",
        expected_tool_calls=[ExpectedToolCall(func=get_all_tasks, args={"limit": 10})],
        rubric=rubric,
        critics=[BinaryCritic(critic_field="limit", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Getting limited tasks from specific project",
        user_message="Show me only 5 tasks from the 'Work' project",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_project, args={"project": "Work", "limit": 5})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="project", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
        additional_messages=[],
    )

    suite.add_case(
        name="Search tasks using filter query",
        user_message="Use filter search to find all tasks that contain the word 'meeting'",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_filter, args={"filter_query": "meeting"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="filter_query", weight=1),
        ],
        additional_messages=[],
    )

    suite.add_case(
        name="Search tasks with project filter",
        user_message="Use the filter search to find tasks in project 'Work' that contain 'report'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_tasks_by_filter, args={"filter_query": "#Work & search:report"}
            )
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="filter_query", weight=1)],
        additional_messages=[],
    )

    suite.add_case(
        name="Search tasks with limit",
        user_message="Use filter search to find the first 3 tasks that contain 'urgent'",
        expected_tool_calls=[
            ExpectedToolCall(func=get_tasks_by_filter, args={"filter_query": "urgent", "limit": 3})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="filter_query", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
        additional_messages=[],
    )

    suite.add_case(
        name="Create task with project ID",
        user_message="Create a task 'Review documents' in project with ID 'proj_123'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task, args={"description": "Review documents", "project": "proj_123"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="description", weight=0.6),
            SimilarityCritic(critic_field="project", weight=0.4),
        ],
        additional_messages=[],
    )

    return suite
