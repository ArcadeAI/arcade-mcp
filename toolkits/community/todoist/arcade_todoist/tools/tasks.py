from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_todoist.utils import (
    get_headers,
    get_tasks_with_pagination,
    get_url,
    parse_task,
    parse_tasks,
    resolve_project_id,
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
        "Default is 50 which should be sufficient for most use cases.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results.",
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get all tasks from the Todoist API with pagination support. Use this when the user wants
    to see, list, view, or browse ALL their existing tasks. For getting tasks from a specific
    project, use get_tasks_by_project instead.

    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """
    return await get_tasks_with_pagination(
        context=context, limit=limit, next_page_token=next_page_token
    )


async def _get_tasks_by_project_id(
    context: ToolContext,
    project_id: Annotated[str, "The ID of the project to get tasks from."],
    limit: Annotated[
        int,
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results.",
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Internal utility function to get tasks from a specific project by project ID with
    pagination support.

    Args:
        context: ToolContext for API access
        project_id: The ID of the project to get tasks from
        limit: Number of tasks to return (min: 1, default: 50, max: 200)
        next_page_token: Token for pagination, use None for first page

    Returns:
        Dict containing tasks and next_page_token for pagination
    """
    return await get_tasks_with_pagination(
        context=context, limit=limit, next_page_token=next_page_token, project_id=project_id
    )


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_tasks_by_project(
    context: ToolContext,
    project: Annotated[str, "The ID or name of the project to get tasks from."],
    limit: Annotated[
        int,
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results.",
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get tasks from a specific project by project ID or name with pagination support.
    Use this when the user wants to see tasks from a specific project.

    The function will first try to find a project with the given ID, and if that doesn't exist,
    it will search for a project with the given name.

    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """
    project_id = await resolve_project_id(context=context, project=project)

    return await _get_tasks_by_project_id(
        context=context, project_id=project_id, limit=limit, next_page_token=next_page_token
    )


async def _create_task_in_project(
    context: ToolContext,
    description: Annotated[str, "The title of the task to be created."],
    project_id: Annotated[
        str | None, "The ID of the project to add the task to. Use None to add to inbox."
    ],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Internal utility function to create a new task in a specific project by project ID.

    Args:
        context: ToolContext for API access
        description: The title of the task to be created
        project_id: The ID of the project to add the task to, use None to add to inbox

    Returns:
        Dict containing the created task object
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
    project: Annotated[
        str | None,
        "The ID or name of the project to add the task to. Use the project ID or name if "
        "user mentions a specific project. Leave as None to add to inbox.",
    ] = None,
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Create a new task for the user. Use this whenever the user wants to create, add, or make a task.
    If the user mentions a specific project, pass the project ID or name as project.
    If no project is mentioned, leave project as None to add to inbox.

    The function will first try to find a project with the given ID, and if that doesn't exist,
    it will search for a project with the given name.
    """

    project_id = None
    if project is not None:
        project_id = await resolve_project_id(context=context, project=project)

    return await _create_task_in_project(
        context=context, description=description, project_id=project_id
    )


async def _close_task_by_task_id(
    context: ToolContext,
    task_id: Annotated[str, "The id of the task to be closed."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Internal utility function to close a task by its ID.

    Args:
        context: ToolContext for API access
        task_id: The ID of the task to be closed

    Returns:
        Dict with success message
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
    task_id: Annotated[str, "The exact ID of the task to be closed."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Close a task by its exact ID. Use this whenever the user wants to
    mark a task as completed, done, or closed.

    """

    return await _close_task_by_task_id(context=context, task_id=task_id)


async def _delete_task_by_task_id(
    context: ToolContext,
    task_id: Annotated[str, "The id of the task to be deleted."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Internal utility function to delete a task by its ID.

    Args:
        context: ToolContext for API access
        task_id: The ID of the task to be deleted

    Returns:
        Dict with success message
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
    task_id: Annotated[str, "The exact ID of the task to be deleted."],
) -> Annotated[dict, "The task object returned by the Todoist API."]:
    """
    Delete a task by its exact ID. Use this whenever the user wants to
    delete a task.
    """

    return await _delete_task_by_task_id(context=context, task_id=task_id)


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_tasks_by_filter(
    context: ToolContext,
    filter_query: Annotated[
        str,
        "The filter query to search tasks.",
    ],
    limit: Annotated[
        int,
        "Number of tasks to return (min: 1, default: 50, max: 200). "
        "Default is 50 which should be sufficient for most use cases.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "Token for pagination. Use None for the first page, or the token returned "
        "from a previous call to get the next page of results.",
    ] = None,
) -> Annotated[dict, "The tasks object with pagination info returned by the Todoist API."]:
    """
    Get tasks by filter query with pagination support.
    Use this when the user wants to search for specific tasks.

    The response includes both tasks and a next_page_token. If next_page_token is not None,
    there are more tasks available and you can call this function again with that token.
    """
    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint="tasks/filter")
        headers = get_headers(context=context)

        params = {"query": filter_query, "limit": limit}
        if next_page_token:
            params["cursor"] = next_page_token

        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        tasks = parse_tasks(data["results"])
        next_cursor = data.get("next_cursor")

        return {"tasks": tasks, "next_page_token": next_cursor}
