from datetime import datetime
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2
from arcade.sdk.errors import ToolExecutionError

from arcade_asana.constants import TASK_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    build_task_search_query_params,
    handle_new_task_associations,
    handle_new_task_tags,
    remove_none_values,
)


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
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


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def search_tasks(
    context: ToolContext,
    keywords: Annotated[
        str, "Keywords to search for tasks. Matches against the task name and description."
    ],
    workspace_id: Annotated[
        str | None,
        "Restricts the search to the given workspace. "
        "Defaults to None (searches across all workspaces).",
    ] = None,
    assignee_ids: Annotated[
        list[str] | None,
        "Restricts the search to tasks assigned to the given users. "
        "Defaults to None (searches tasks assigned to anyone or no one).",
    ] = None,
    project_ids: Annotated[
        list[str] | None,
        "Restricts the search to tasks associated to the given projects. "
        "Defaults to None (searches tasks associated to any project).",
    ] = None,
    team_ids: Annotated[
        list[str] | None,
        "Restricts the search to tasks associated to the given teams. "
        "Defaults to None (searches tasks associated to any team).",
    ] = None,
    tags: Annotated[
        list[str] | None,
        "Restricts the search to tasks associated to the given tags. "
        "Defaults to None (searches tasks associated to any tag or no tag).",
    ] = None,
    due_on: Annotated[
        str | None,
        "Match tasks that are due exactly on this date. Format: YYYY-MM-DD. Ex: '2025-01-01'. "
        "Defaults to None (searches tasks due on any date or without a due date).",
    ] = None,
    due_on_or_after: Annotated[
        str | None,
        "Match tasks that are due on OR AFTER this date. Format: YYYY-MM-DD. Ex: '2025-01-01' "
        "Defaults to None (searches tasks due on any date or without a due date).",
    ] = None,
    due_on_or_before: Annotated[
        str | None,
        "Match tasks that are due on OR BEFORE this date. Format: YYYY-MM-DD. Ex: '2025-01-01' "
        "Defaults to None (searches tasks due on any date or without a due date).",
    ] = None,
    start_on: Annotated[
        str | None,
        "Match tasks that started on this date. Format: YYYY-MM-DD. Ex: '2025-01-01'. "
        "Defaults to None (searches tasks started on any date or without a start date).",
    ] = None,
    start_on_or_after: Annotated[
        str | None,
        "Match tasks that started on OR AFTER this date. Format: YYYY-MM-DD. Ex: '2025-01-01' "
        "Defaults to None (searches tasks started on any date or without a start date).",
    ] = None,
    start_on_or_before: Annotated[
        str | None,
        "Match tasks that started on OR BEFORE this date. Format: YYYY-MM-DD. Ex: '2025-01-01' "
        "Defaults to None (searches tasks started on any date or without a start date).",
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

    return {
        "tasks": response["data"],
        "count": len(response["data"]),
    }


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
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


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def create_task(
    context: ToolContext,
    name: Annotated[str, "The name of the task"],
    start_date: Annotated[
        str | None,
        "The start date of the task in the format YYYY-MM-DD. Example: '2025-01-01'. "
        "Defaults to None.",
    ] = None,
    due_date: Annotated[
        str | None,
        "The due date of the task in the format YYYY-MM-DD. Example: '2025-01-01'. "
        "Defaults to None.",
    ] = None,
    description: Annotated[str | None, "The description of the task. Defaults to None."] = None,
    parent_task_id: Annotated[str | None, "The ID of the parent task. Defaults to None."] = None,
    workspace_id: Annotated[
        str | None, "The ID of the workspace to associate the task to. Defaults to None."
    ] = None,
    project_id: Annotated[
        str | None, "The ID of the project to associate the task to. Defaults to None."
    ] = None,
    project_name: Annotated[
        str | None, "The name of the project to associate the task to. Defaults to None."
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to assign the task to. "
        "Defaults to 'me', which assigns the task to the current user.",
    ] = "me",
    tag_names: Annotated[
        list[str] | None, "The names of the tags to associate with the task. Defaults to None."
    ] = None,
    tag_ids: Annotated[
        list[str] | None, "The IDs of the tags to associate with the task. Defaults to None."
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Creates a task in Asana",
]:
    """Creates a task in Asana

    Provide none or at most one of the following argument pairs, never both:
    - tag_names and tag_ids
    - project_name and project_id

    The task must be associated to at least one of the following: parent_task_id, project_id, or
    workspace_id. If none of these are provided and the account has only one workspace, the task
    will be associated to that workspace. If the account has multiple workspaces, an error will
    be raised with a list of available workspaces.
    """
    client = AsanaClient(context.get_auth_token_or_empty())

    parent_task_id, project_id, workspace_id = await handle_new_task_associations(
        context, parent_task_id, project_id, project_name, workspace_id
    )

    tag_ids = await handle_new_task_tags(context, tag_names, tag_ids, workspace_id)

    try:
        datetime.strptime(due_date, "%Y-%m-%d")
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise ToolExecutionError(
            "Invalid date format. Use the format YYYY-MM-DD for both start_date and due_date."
        )

    task_data = {
        "data": remove_none_values({
            "name": name,
            "due_on": due_date,
            "start_on": start_date,
            "notes": description,
            "parent": parent_task_id,
            "projects": [project_id] if project_id else None,
            "workspace": workspace_id,
            "assignee": assignee_id,
            "tags": tag_ids,
        }),
    }

    response = await client.post("tasks", json_data=task_data)

    return {
        "status": {"success": True, "message": "task successfully created"},
        "task": response["data"],
    }
