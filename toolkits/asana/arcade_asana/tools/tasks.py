from datetime import datetime
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2
from arcade.sdk.errors import ToolExecutionError

from arcade_asana.constants import TASK_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import build_task_search_query_params, remove_none_values


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["tasks:read"]))
async def get_task_by_id(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to get."],
) -> Annotated[dict[str, Any], "The task with the given ID."]:
    """Get a task by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/tasks/{task_id}",
        params={"opt_fields": TASK_OPT_FIELDS},
    )
    return {"task": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["tasks:read"]))
async def search_tasks(
    context: ToolContext,
    keywords: Annotated[
        str, "Keywords to search for tasks. Matches against the task name and description."
    ],
    assignee_ids: Annotated[
        list[str] | None, "IDs of the users to search for tasks assigned to."
    ] = None,
    project_ids: Annotated[list[str] | None, "IDs of the projects to search for tasks in."] = None,
    team_ids: Annotated[list[str] | None, "IDs of the teams to search for tasks in."] = None,
    tags: Annotated[list[str] | None, "Tags to search for tasks with."] = None,
    due_on: Annotated[
        str | None,
        "Match tasks that are due on this date. Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    due_on_or_after: Annotated[
        str | None,
        "Match tasks that are due on or after this date. "
        "Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    due_on_or_before: Annotated[
        str | None,
        "Match tasks that are due on or before this date. "
        "Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    start_on: Annotated[
        str | None,
        "Match tasks that are started on this date. Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    start_on_or_after: Annotated[
        str | None,
        "Match tasks that are started on or after this date. "
        "Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    start_on_or_before: Annotated[
        str | None,
        "Match tasks that are started on or before this date. "
        "Format: YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    completed: Annotated[
        bool,
        "Match tasks that are completed. Defaults to False (tasks that are NOT completed).",
    ] = False,
) -> Annotated[dict[str, Any], "The tasks that match the query."]:
    """Search for tasks"""
    client = AsanaClient(context.get_auth_token_or_empty())
    query_params = build_task_search_query_params(
        keywords,
        completed,
        assignee_ids,
        project_ids,
        team_ids,
        tags,
        due_on,
        due_on_or_after,
        due_on_or_before,
        start_on,
        start_on_or_after,
        start_on_or_before,
    )

    response = await client.get("/tasks", params=query_params)
    return {"tasks": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["tasks:write"]))
async def update_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to update."],
    name: Annotated[str | None, "The new name of the task"] = None,
    start_date: Annotated[
        str | None,
        "The new start date of the task in the format YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    due_date: Annotated[
        str | None,
        "The new due date of the task in the format YYYY-MM-DD. Example: '2025-01-01'.",
    ] = None,
    description: Annotated[str | None, "The new description of the task."] = None,
    parent_task_id: Annotated[str | None, "The ID of the new parent task."] = None,
    project_ids: Annotated[
        list[str] | None, "The IDs of the new projects to associate the task to."
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the new user to assign the task to. "
        "Provide 'me' to assign the task to the current user.",
    ] = None,
    tags: Annotated[list[str] | None, "The new tags to associate with the task."] = None,
) -> Annotated[
    dict[str, Any],
    "Updates a task in Asana",
]:
    """Updates a task in Asana"""
    client = AsanaClient(context.get_auth_token_or_empty())

    task_data = {
        "name": name,
        "due_on": due_date,
        "start_on": start_date,
        "notes": description,
        "parent": parent_task_id,
        "projects": project_ids,
        "assignee": assignee_id,
        "tags": tags,
    }

    response = await client.put(f"/tasks/{task_id}", json_data=remove_none_values(task_data))
    return {
        "status": {"success": True, "message": "task updated successfully"},
        "task": response["data"],
    }


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["tasks:write"]))
async def create_task(
    context: ToolContext,
    name: Annotated[str, "The name of the task"],
    start_date: Annotated[
        str | None, "The start date of the task in the format YYYY-MM-DD. Example: '2025-01-01'."
    ] = None,
    due_date: Annotated[
        str | None, "The due date of the task in the format YYYY-MM-DD. Example: '2025-01-01'."
    ] = None,
    description: Annotated[str | None, "The description of the task."] = None,
    parent_task_id: Annotated[str | None, "The ID of the parent task."] = None,
    workspace_id: Annotated[str | None, "The ID of the workspace to associate the task to."] = None,
    project_ids: Annotated[
        list[str] | None, "The IDs of the projects to associate the task to."
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to assign the task to. "
        "Provide 'me' to assign the task to the current user.",
    ] = None,
    tags: Annotated[list[str] | None, "The tags to associate with the task."] = None,
) -> Annotated[
    dict[str, Any],
    "Creates a task in Asana",
]:
    """Creates a task in Asana"""
    client = AsanaClient(context.get_auth_token_or_empty())

    try:
        datetime.strptime(due_date, "%Y-%m-%d")
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise ToolExecutionError(
            "Invalid date format. Use the format YYYY-MM-DD for both start_date and due_date."
        )

    if assignee_id == "me":
        assignee_id = await client.get_current_user()["gid"]

    task_data = {
        "name": name,
        "due_date": due_date,
        "notes": description,
        "parent": parent_task_id,
        "projects": project_ids,
        "workspace": workspace_id,
        "assignee": assignee_id,
        "tags": tags,
    }

    response = await client.post("/tasks", json_data=remove_none_values(task_data))
    return {
        "status": {"success": True, "message": "task created successfully"},
        "task": response["data"],
    }
