import asyncio
import base64
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2
from arcade.sdk.errors import ToolExecutionError

from arcade_asana.constants import TASK_OPT_FIELDS, SortOrder, TaskSortBy
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    build_task_search_query_params,
    clean_request_params,
    handle_new_task_associations,
    handle_new_task_tags,
    remove_none_values,
    validate_date_format,
)


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def get_task_by_id(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to get."],
    max_subtasks: Annotated[
        int,
        "The maximum number of subtasks to return. Min of 1, max of 100. Defaults to 100.",
    ] = 100,
) -> Annotated[dict[str, Any], "The task with the given ID."]:
    """Get a task by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/tasks/{task_id}",
        params={"opt_fields": TASK_OPT_FIELDS},
    )
    subtasks = await get_subtasks_from_a_task(context, task_id=task_id, limit=max_subtasks)
    response["data"]["subtasks"] = subtasks["subtasks"]
    return {"task": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def get_subtasks_from_a_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to get the subtasks of."],
    limit: Annotated[
        int,
        "The maximum number of subtasks to return. Min of 1, max of 100. Defaults to 100.",
    ] = 100,
    offset: Annotated[
        int,
        "The offset of the subtasks to return. Defaults to 0.",
    ] = 0,
) -> Annotated[dict[str, Any], "The subtasks of the task."]:
    """Get the subtasks of a task"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/tasks/{task_id}/subtasks",
        params=clean_request_params({
            "opt_fields": TASK_OPT_FIELDS,
            "limit": limit,
            "offset": offset,
        }),
    )
    return {"subtasks": response["data"], "count": len(response["data"])}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def search_tasks(
    context: ToolContext,
    keywords: Annotated[
        str, "Keywords to search for tasks. Matches against the task name and description."
    ],
    workspace_ids: Annotated[
        list[str] | None,
        "The IDs of the workspaces to search for tasks. "
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
    limit: Annotated[
        int,
        "The maximum number of tasks to return. Min of 1, max of 20. Defaults to 20.",
    ] = 20,
    sort_by: Annotated[
        TaskSortBy,
        "The field to sort the tasks by. Defaults to TaskSortBy.MODIFIED_AT.",
    ] = TaskSortBy.MODIFIED_AT,
    sort_order: Annotated[
        SortOrder,
        "The order to sort the tasks by. Defaults to SortOrder.DESCENDING.",
    ] = SortOrder.DESCENDING,
) -> Annotated[dict[str, Any], "The tasks that match the query."]:
    """Search for tasks"""
    from arcade_asana.tools.workspaces import list_workspaces  # Avoid circular import

    workspace_ids = workspace_ids or await list_workspaces(context)

    client = AsanaClient(context.get_auth_token_or_empty())

    validate_date_format("due_on", due_on)
    validate_date_format("due_on_or_after", due_on_or_after)
    validate_date_format("due_on_or_before", due_on_or_before)
    validate_date_format("start_on", start_on)
    validate_date_format("start_on_or_after", start_on_or_after)
    validate_date_format("start_on_or_before", start_on_or_before)

    responses = await asyncio.gather(*[
        client.get(
            f"/workspaces/{workspace_id}/tasks/search",
            params=build_task_search_query_params(
                workspace_id=workspace_id,
                keywords=keywords,
                completed=completed,
                assignee_ids=assignee_ids,
                project_ids=project_ids,
                team_ids=team_ids,
                tags=tags,
                due_on=due_on,
                due_on_or_after=due_on_or_after,
                due_on_or_before=due_on_or_before,
                start_on=start_on,
                start_on_or_after=start_on_or_after,
                start_on_or_before=start_on_or_before,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
            ),
        )
        for workspace_id in workspace_ids
    ])

    tasks_by_id = {task["gid"]: task for response in responses for task in response["data"]}

    subtasks = await asyncio.gather(*[
        get_subtasks_from_a_task(context, task_id=task["gid"]) for task in tasks_by_id.values()
    ])

    for response in subtasks:
        for subtask in response["subtasks"]:
            parent_task = tasks_by_id[subtask["parent"]["gid"]]
            parent_task["subtasks"].append(subtask)

    tasks = list(tasks_by_id.values())

    return {"tasks": tasks, "count": len(tasks)}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def update_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to update."],
    name: Annotated[
        str | None,
        "The new name of the task. Defaults to None (does not change the current name).",
    ] = None,
    completed: Annotated[
        bool | None,
        "The new completion status of the task. "
        "Provide True to mark the task as completed, False to mark it as not completed. "
        "Defaults to None (does not change the current completion status).",
    ] = None,
    start_date: Annotated[
        str | None,
        "The new start date of the task in the format YYYY-MM-DD. Example: '2025-01-01'. "
        "Defaults to None (does not change the current start date).",
    ] = None,
    due_date: Annotated[
        str | None,
        "The new due date of the task in the format YYYY-MM-DD. Example: '2025-01-01'. "
        "Defaults to None (does not change the current due date).",
    ] = None,
    description: Annotated[
        str | None,
        "The new description of the task. "
        "Defaults to None (does not change the current description).",
    ] = None,
    parent_task_id: Annotated[
        str | None,
        "The ID of the new parent task. "
        "Defaults to None (does not change the current parent task).",
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the new user to assign the task to. "
        "Provide 'me' to assign the task to the current user. "
        "Defaults to None (does not change the current assignee).",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Updates a task in Asana",
]:
    """Updates a task in Asana"""
    client = AsanaClient(context.get_auth_token_or_empty())

    validate_date_format("start_date", start_date)
    validate_date_format("due_date", due_date)

    task_data = {
        "data": remove_none_values({
            "name": name,
            "completed": completed,
            "due_on": due_date,
            "start_on": start_date,
            "notes": description,
            "parent": parent_task_id,
            "assignee": assignee_id,
        }),
    }

    response = await client.put(f"/tasks/{task_id}", json_data=task_data)

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

    validate_date_format("start_date", start_date)
    validate_date_format("due_date", due_date)

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


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def attach_file_to_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to attach the file to."],
    file_name: Annotated[
        str,
        "The name of the file to attach with format extension. E.g. 'Image.png' or 'Report.pdf'.",
    ],
    file_content_str: Annotated[
        str | None,
        "The string contents of the file to attach. Use this if the file IS a text file. "
        "Defaults to None.",
    ] = None,
    file_content_base64: Annotated[
        str | None,
        "The base64-encoded binary contents of the file. "
        "Use this for binary files like images or PDFs. Defaults to None.",
    ] = None,
    file_content_url: Annotated[
        str | None,
        "The URL of the file to attach. Use this if the file is hosted on an external URL. "
        "Defaults to None.",
    ] = None,
    file_encoding: Annotated[
        str,
        "The encoding of the file to attach. Only used with file_content_str. Defaults to 'utf-8'.",
    ] = "utf-8",
) -> Annotated[dict[str, Any], "The task with the file attached."]:
    """Attaches a file to an Asana task

    Provide exactly one of file_content_str, file_content_base64, or file_content_url, never more
    than one.

    - Use file_content_str for text files (will be encoded using file_encoding)
    - Use file_content_base64 for binary files like images, PDFs, etc.
    - Use file_content_url if the file is hosted on an external URL
    """
    client = AsanaClient(context.get_auth_token_or_empty())

    if sum([bool(file_content_str), bool(file_content_base64), bool(file_content_url)]) != 1:
        raise ToolExecutionError(
            "Provide exactly one of file_content_str, file_content_base64, or file_content_url"
        )

    data = {
        "parent": task_id,
        "name": file_name,
        "resource_subtype": "asana",
    }

    if file_content_url is not None:
        data["url"] = file_content_url
        data["resource_subtype"] = "external"
        file_content = None
    elif file_content_str is not None:
        try:
            file_content = file_content_str.encode(file_encoding)
        except LookupError as exc:
            raise ToolExecutionError(f"Unknown encoding: {file_encoding}") from exc
    elif file_content_base64 is not None:
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as exc:
            raise ToolExecutionError(f"Invalid base64 encoding: {exc!s}") from exc

    if file_content:
        if file_name.lower().endswith(".pdf"):
            files = {"file": (file_name, file_content, "application/pdf")}
        else:
            files = {"file": (file_name, file_content)}  # type: ignore[dict-item]
    else:
        files = None

    response = await client.post("/attachments", data=data, files=files)

    return {
        "status": {"success": True, "message": f"file successfully attached to task {task_id}"},
        "response": response["data"],
    }
