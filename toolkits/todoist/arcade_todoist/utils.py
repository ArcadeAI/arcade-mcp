from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError


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
