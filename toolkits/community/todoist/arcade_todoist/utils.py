from typing import Any

import httpx
from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError

from arcade_todoist.errors import MultipleTasksFoundError, ProjectNotFoundError, TaskNotFoundError


class TodoistAuthError(ToolExecutionError):
    """Raised when Todoist authentication token is missing."""

    def __init__(self):
        super().__init__("No token found")


def get_headers(context: ToolContext) -> dict[str, str]:
    """
    Build headers for the Todoist API requests.
    """

    token = context.get_auth_token_or_empty()

    if not token:
        raise TodoistAuthError()

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_url(
    context: ToolContext,
    endpoint: str,
    api_version: str = "v1",
) -> str:
    """
    Build the URL for the Todoist API request.
    """

    base_url = "https://api.todoist.com"

    return f"{base_url}/api/{api_version}/{endpoint}"


def parse_project(project: dict[str, Any]) -> dict[str, Any]:
    """
    Parse the project object returned by the Todoist API.
    """

    return {
        "id": project["id"],
        "name": project["name"],
        "created_at": project["created_at"],
    }


def parse_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Parse the projects object returned by the Todoist API.
    """

    return [parse_project(project) for project in projects]


def parse_task(task: dict[str, Any]) -> dict[str, Any]:
    """
    Parse the task object returned by the Todoist API.
    """

    return {
        "id": task["id"],
        "content": task["content"],
        "added_at": task["added_at"],
        "checked": task["checked"],
        "project_id": task["project_id"],
    }


def parse_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Parse the tasks object returned by the Todoist API.
    """

    return [parse_task(task) for task in tasks]


async def get_tasks_with_pagination(
    context: ToolContext,
    limit: int = 50,
    next_page_token: str | None = None,
    project_id: str | None = None,
) -> dict:
    """
    Utility function to get tasks with pagination support.

    Args:
        context: ToolContext for API access
        limit: Number of tasks to return (min: 1, default: 50, max: 200)
        next_page_token: Token for pagination, use None for first page
        project_id: Optional project ID to filter tasks by project

    Returns:
        Dict containing tasks and next_page_token for pagination
    """

    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint="tasks")
        headers = get_headers(context=context)

        params = {"limit": limit}
        if next_page_token:
            params["cursor"] = next_page_token
        if project_id:
            params["project_id"] = project_id

        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        tasks = parse_tasks(data["results"])
        next_cursor = data.get("next_cursor")

        return {"tasks": tasks, "next_page_token": next_cursor}


async def resolve_project_id(context: ToolContext, project: str) -> str:
    """
    Utility function to resolve a project identifier to project ID.

    Args:
        context: ToolContext for API access
        project: Project ID or name to resolve

    Returns:
        The project ID

    Raises:
        ProjectNotFoundError: If the project is not found
    """
    from arcade_todoist.tools.projects import get_projects

    projects = await get_projects(context=context)

    for proj in projects["projects"]:
        if proj["id"] == project:
            return project

    for proj in projects["projects"]:
        if proj["name"].lower() == project.lower():
            return proj["id"]

    partial_matches = []
    for proj in projects["projects"]:
        if project.lower() in proj["name"].lower():
            partial_matches.append(proj["name"])

    if partial_matches:
        raise ProjectNotFoundError(project, partial_matches)
    else:
        raise ProjectNotFoundError(project)


def _check_exact_id_match(tasks: list[dict], task: str) -> str | None:
    """Check if task matches any task ID exactly."""
    for task_obj in tasks:
        if task_obj["id"] == task:
            return task
    return None


def _find_exact_content_matches(tasks: list[dict], task: str) -> list[dict]:
    """Find tasks with exact content match (case-insensitive)."""
    return [task_obj for task_obj in tasks if task_obj["content"].lower() == task.lower()]


def _find_partial_content_matches(tasks: list[dict], task: str) -> list[dict]:
    """Find tasks with partial content match (case-insensitive)."""
    return [task_obj for task_obj in tasks if task.lower() in task_obj["content"].lower()]


def _handle_task_matches(task: str, exact_matches: list[dict], partial_matches: list[dict]) -> str:
    """Handle task matching logic and raise appropriate errors."""
    if len(exact_matches) == 1:
        return exact_matches[0]["id"]
    elif len(exact_matches) > 1:
        _raise_multiple_tasks_error(task, exact_matches)

    if len(partial_matches) == 1:
        return partial_matches[0]["id"]
    elif len(partial_matches) > 1:
        _raise_multiple_tasks_error(task, partial_matches)

    # If we have partial matches but multiple, convert to content strings for error
    if partial_matches:
        partial_match_contents = [task_obj["content"] for task_obj in partial_matches]
        _raise_task_not_found_error(task, partial_match_contents)

    _raise_task_not_found_error(task)


def _raise_multiple_tasks_error(task: str, matches: list[dict]) -> None:
    """Raise MultipleTasksFoundError."""
    raise MultipleTasksFoundError(task, matches)


def _raise_task_not_found_error(task: str, suggestions: list[str] | None = None) -> None:
    """Raise TaskNotFoundError."""
    if suggestions:
        raise TaskNotFoundError(task, suggestions)
    raise TaskNotFoundError(task)


def _resolve_task_from_task_list(tasks: list[dict], task: str) -> str:
    """Resolve task ID from a list of tasks."""
    # Check for exact ID match first
    exact_id = _check_exact_id_match(tasks, task)
    if exact_id:
        return exact_id

    # Check for exact and partial content matches
    exact_matches = _find_exact_content_matches(tasks, task)
    partial_matches = _find_partial_content_matches(tasks, task)

    return _handle_task_matches(task, exact_matches, partial_matches)


async def resolve_task_id(context: ToolContext, task: str) -> str:
    """
    Utility function to resolve a task identifier to task ID.

    Args:
        context: ToolContext for API access
        task: Task ID or description/content to resolve

    Returns:
        The task ID

    Raises:
        TaskNotFoundError: If the task is not found
        MultipleTasksFoundError: If multiple tasks match the criteria
    """
    from arcade_todoist.tools.tasks import get_tasks_by_filter

    try:
        tasks = await get_tasks_by_filter(context=context, filter_query=f"search: {task}")
        return _resolve_task_from_task_list(tasks["tasks"], task)

    except (TaskNotFoundError, MultipleTasksFoundError):
        # Re-raise these specific errors
        raise
    except Exception as err:
        # If search filter fails, fall back to getting all tasks
        try:
            from arcade_todoist.tools.tasks import get_all_tasks

            tasks = await get_all_tasks(context=context)
            return _resolve_task_from_task_list(tasks["tasks"], task)
        except (TaskNotFoundError, MultipleTasksFoundError):
            # Re-raise these specific errors from the fallback
            raise
        except Exception:
            # If both methods fail, raise the original error
            raise TaskNotFoundError(task) from err
