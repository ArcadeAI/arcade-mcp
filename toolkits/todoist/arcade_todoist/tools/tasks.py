from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import ToolExecutionError

from arcade_todoist.tools.projects import get_projects
from arcade_todoist.utils import get_headers, get_url, parse_task, parse_tasks


async def _get_tasks_with_pagination(
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
        
        return {
            "tasks": tasks,
            "next_page_token": next_cursor
        }


class ProjectNotFoundError(ToolExecutionError):
    """Raised when a project is not found."""

    def __init__(self, project_name: str, partial_matches: list[str] | None = None):
        if partial_matches:
            matches_str = "', '".join(partial_matches)
            super().__init__(
                "Project not found",
                developer_message=(
                    f"Project '{project_name}' not found, but found partial matches: "
                    f"{matches_str}. "
                    f"Please specify the exact project name."
                ),
            )
        else:
            super().__init__(
                "Project not found",
                developer_message=(
                    f"Project '{project_name}' not found. "
                    f"Ask the user to create the project first."
                ),
            )


class TaskNotFoundError(ToolExecutionError):
    """Raised when a task is not found."""

    def __init__(self, task_description: str, partial_matches: list[str] | None = None):
        if partial_matches:
            matches_str = "', '".join(partial_matches)
            super().__init__(
                "Task not found",
                developer_message=(
                    f"Task '{task_description}' not found, but found partial matches: "
                    f"{matches_str}. "
                    f"Please specify the exact task description."
                ),
            )
        else:
            super().__init__(
                "Task not found", developer_message=f"Task '{task_description}' not found."
            )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_all_tasks(
    context: ToolContext,
    limit: Annotated[
        int, 
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases."
    ] = 50,
    next_page_token: Annotated[
        str | None, 
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results."
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get all tasks from the Todoist API with pagination support. Use this when the user wants to see, list, view, or
    browse all their existing tasks. For getting tasks from a specific project, use
    get_tasks_by_project_name or get_tasks_by_project_id instead.
    
    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """
    return await _get_tasks_with_pagination(
        context=context,
        limit=limit,
        next_page_token=next_page_token
    )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_tasks_by_project_id(
    context: ToolContext,
    project_id: Annotated[str, "The ID of the project to get tasks from."],
    limit: Annotated[
        int, 
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases."
    ] = 50,
    next_page_token: Annotated[
        str | None, 
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results."
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get tasks from a specific project by project ID with pagination support. Use this when you already have the project ID.
    For getting tasks by project name, use get_tasks_by_project_name instead.
    
    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """
    return await _get_tasks_with_pagination(
        context=context,
        limit=limit,
        next_page_token=next_page_token,
        project_id=project_id
    )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_tasks_by_project_name(
    context: ToolContext,
    project_name: Annotated[str, "The name of the project to get tasks from."],
    limit: Annotated[
        int, 
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases."
    ] = 50,
    next_page_token: Annotated[
        str | None, 
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results."
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get tasks from a specific project by project name with pagination support. Use this when the user wants to see
    tasks from a specific project.
    
    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """

    projects = await get_projects(context=context)

    project_id = None

    for project in projects["projects"]:
        if project["name"].lower() == project_name.lower():
            project_id = project["id"]
            break

    if project_id is None:
        partial_matches = []
        for project in projects["projects"]:
            if project_name.lower() in project["name"].lower():
                partial_matches.append(project["name"])

        if partial_matches:
            raise ProjectNotFoundError(project_name, partial_matches)
        else:
            raise ProjectNotFoundError(project_name)

    return await get_tasks_by_project_id(
        context=context, 
        project_id=project_id, 
        limit=limit, 
        next_page_token=next_page_token
    )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def create_task_in_project(
    context: ToolContext,
    description: Annotated[str, "The title of the task to be created."],
    project_id: Annotated[
        str | None, "The ID of the project to add the task to. Use None to add to inbox."
    ],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Create a new task in a specific project by project ID. Use this when you already have the
    project ID. For creating tasks by project name, use create_task instead.
    """

    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint="tasks")
        headers = get_headers(context=context)

        response = await client.post(
            url,
            headers=headers,
            json={
                "content": description,
                "project_id": project_id,
            },
        )

        response.raise_for_status()

        task = parse_task(response.json())

        return task


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def create_task(
    context: ToolContext,
    description: Annotated[str, "The title of the task to be created."],
    project_name: Annotated[
        str | None,
        "The name of the project to add the task to. Use the project name if user mentions a "
        "specific project.",
    ],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Create a new task for the user. Use this whenever the user wants to create, add, or make a task.
    If the user mentions a specific project, pass the project name as project_name.
    If no project is mentioned, leave project_name as None to add to inbox.
    """

    project_id = None
    if project_name is not None:
        projects = await get_projects(context=context)

        for project in projects["projects"]:
            if project["name"].lower() == project_name.lower():
                project_id = project["id"]
                break

        if project_id is None:
            partial_matches = []
            for project in projects["projects"]:
                if project_name.lower() in project["name"].lower():
                    partial_matches.append(project["name"])

            if partial_matches:
                raise ProjectNotFoundError(project_name, partial_matches)
            else:
                raise ProjectNotFoundError(project_name)

    return await create_task_in_project(
        context=context, description=description, project_id=project_id
    )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def close_task_by_task_id(
    context: ToolContext,
    task_id: Annotated[str, "The id of the task to be closed."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Close a task by its ID. Use this when you already have the task ID.
    For closing tasks by description/content, use close_task instead.
    """

    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint=f"tasks/{task_id}/close")
        headers = get_headers(context=context)

        response = await client.post(url, headers=headers)

        response.raise_for_status()

        return {"message": "Task closed successfully"}


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def close_task(
    context: ToolContext,
    task_description: Annotated[str, "The description/content of the task to be closed."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Close a task by its description/content. Use this whenever the user wants to mark a task as
    completed, done, or closed.
    """

    tasks = await get_all_tasks(context=context)

    task_id = None

    for task in tasks["tasks"]:
        if task["content"].lower() == task_description.lower():
            task_id = task["id"]
            break

    if task_id is None:
        partial_matches = []
        for task in tasks["tasks"]:
            if task_description.lower() in task["content"].lower():
                partial_matches.append(task["content"])

        if partial_matches:
            raise TaskNotFoundError(task_description, partial_matches)
        else:
            raise TaskNotFoundError(task_description)

    return await close_task_by_task_id(context=context, task_id=task_id)


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def delete_task_by_task_id(
    context: ToolContext,
    task_id: Annotated[str, "The id of the task to be deleted."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Delete a task by its ID. Use this when you already have the task ID.
    For deleting tasks by description/content, use delete_task instead.
    """

    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint=f"tasks/{task_id}")
        headers = get_headers(context=context)

        response = await client.delete(url, headers=headers)

        response.raise_for_status()

        return {"message": "Task deleted successfully"}


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read_write"],
    ),
)
async def delete_task(
    context: ToolContext,
    task_description: Annotated[str, "The description/content of the task to be deleted."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Delete a task by its description/content. Use this whenever the user wants to delete a task.
    """

    tasks = await get_all_tasks(context=context)

    task_id = None

    for task in tasks["tasks"]:
        if task["content"].lower() == task_description.lower():
            task_id = task["id"]
            break

    if task_id is None:
        partial_matches = []
        for task in tasks["tasks"]:
            if task_description.lower() in task["content"].lower():
                partial_matches.append(task["content"])

        if partial_matches:
            raise TaskNotFoundError(task_description, partial_matches)
        else:
            raise TaskNotFoundError(task_description)

    return await delete_task_by_task_id(context=context, task_id=task_id)
