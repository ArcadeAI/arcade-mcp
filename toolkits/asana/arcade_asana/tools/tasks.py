import base64
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana
from arcade_tdk.errors import ToolExecutionError

from arcade_asana.constants import TASK_OPT_FIELDS, SortOrder, TaskSortBy
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    build_task_search_query_params,
    get_next_page,
    get_project_by_name_or_raise_error,
    get_tag_ids,
    get_unique_workspace_id_or_raise_error,
    handle_new_task_associations,
    handle_new_task_tags,
    remove_none_values,
    validate_date_format,
)


@tool(requires_auth=Asana(scopes=["default"]))
async def get_tasks_without_id(
    context: ToolContext,
    keywords: Annotated[
        str | None, "Keywords to search for tasks. Matches against the task name and description."
    ] = None,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to search for tasks. Defaults to None. If not provided and the user "
        "has only one workspace, it will use that workspace. If not provided and the user has "
        "multiple workspaces, it will raise an error listing the available workspaces.",
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to filter tasks assigned to. "
        "Defaults to None (does not filter by assignee).",
    ] = None,
    project: Annotated[
        str | None,
        "The ID or name of the project to filter tasks. "
        "Defaults to None (searches tasks associated to any project or no project).",
    ] = None,
    team_id: Annotated[
        str | None,
        "Restricts the search to tasks associated to the given team ID. "
        "Defaults to None (searches tasks associated to any team).",
    ] = None,
    tags: Annotated[
        list[str] | None,
        "Restricts the search to tasks associated to the given tags. "
        "Each item in the list can be a tag name (e.g. 'My Tag') or a tag ID (e.g. '1234567890'). "
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
        bool | None,
        "Match tasks that are completed. Defaults to None (does not filter by completion status).",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of tasks to return. Min of 1, max of 100. Defaults to 100.",
    ] = 100,
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
    limit = max(1, min(100, limit))

    project_id = None

    if project:
        if project.isnumeric():
            project_id = project
        else:
            project_data = await get_project_by_name_or_raise_error(context, project)
            project_id = project_data["id"]
            if not workspace_id:
                workspace_id = project_data["workspace"]["id"]

    tag_ids = await get_tag_ids(context, tags)

    client = AsanaClient(context.get_auth_token_or_empty())

    validate_date_format("due_on", due_on)
    validate_date_format("due_on_or_after", due_on_or_after)
    validate_date_format("due_on_or_before", due_on_or_before)
    validate_date_format("start_on", start_on)
    validate_date_format("start_on_or_after", start_on_or_after)
    validate_date_format("start_on_or_before", start_on_or_before)

    if not any([workspace_id, project_id, team_id]):
        workspace_id = await get_unique_workspace_id_or_raise_error(context)

    if not workspace_id and team_id:
        from arcade_asana.tools.teams import get_team_by_id

        team = await get_team_by_id(context, team_id)
        workspace_id = team["organization"]["id"]

    response = await client.get(
        f"/workspaces/{workspace_id}/tasks/search",
        params=build_task_search_query_params(
            keywords=keywords,
            completed=completed,
            assignee_id=assignee_id,
            project_id=project_id,
            team_id=team_id,
            tag_ids=tag_ids,
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

    tasks_by_id = {task["id"]: task for task in response["data"]}

    tasks = list(tasks_by_id.values())

    return {"tasks": tasks, "count": len(tasks)}


@tool(requires_auth=Asana(scopes=["default"]))
async def get_task_by_id(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to get."],
    max_subtasks: Annotated[
        int,
        "The maximum number of subtasks to return. "
        "Min of 0 (no subtasks), max of 100. Defaults to 100.",
    ] = 100,
) -> Annotated[dict[str, Any], "The task with the given ID."]:
    """Get a task by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/tasks/{task_id}",
        params={"opt_fields": TASK_OPT_FIELDS},
    )
    if max_subtasks > 0:
        max_subtasks = min(max_subtasks, 100)
        subtasks = await get_subtasks_from_a_task(context, task_id=task_id, limit=max_subtasks)
        response["data"]["subtasks"] = subtasks["subtasks"]
    return {"task": response["data"]}


@tool(requires_auth=Asana(scopes=["default"]))
async def get_subtasks_from_a_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to get the subtasks of."],
    limit: Annotated[
        int,
        "The maximum number of subtasks to return. Min of 1, max of 100. Defaults to 100.",
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of subtasks. Defaults to None (start from the first "
        "page of subtasks)",
    ] = None,
) -> Annotated[dict[str, Any], "The subtasks of the task."]:
    """Get the subtasks of a task"""
    limit = max(1, min(100, limit))

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/tasks/{task_id}/subtasks",
        params=remove_none_values({
            "opt_fields": TASK_OPT_FIELDS,
            "limit": limit,
            "offset": next_page_token,
        }),
    )

    return {
        "subtasks": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }


@tool(requires_auth=Asana(scopes=["default"]))
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
            "assignee": assignee_id,
        }),
    }

    response = await client.put(f"/tasks/{task_id}", json_data=task_data)

    return {
        "status": {"success": True, "message": "task updated successfully"},
        "task": response["data"],
    }


@tool(requires_auth=Asana(scopes=["default"]))
async def mark_task_as_completed(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to mark as completed."],
) -> Annotated[dict[str, Any], "The task marked as completed."]:
    """Mark a task in Asana as completed"""
    return await update_task(context, task_id, completed=True)  # type: ignore[no-any-return]


@tool(requires_auth=Asana(scopes=["default"]))
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
    project: Annotated[
        str | None, "The ID or name of the project to associate the task to. Defaults to None."
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to assign the task to. "
        "Defaults to 'me', which assigns the task to the current user.",
    ] = "me",
    tags: Annotated[
        list[str] | None,
        "The tags to associate with the task. Multiple tags can be provided in the list. "
        "Each item in the list can be a tag name (e.g. 'My Tag') or a tag ID (e.g. '1234567890'). "
        "If a tag name does not exist, it will be automatically created with the new task. "
        "Defaults to None (no tags associated).",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Creates a task in Asana",
]:
    """Creates a task in Asana

    The task must be associated to at least one of the following: parent_task_id, project, or
    workspace_id. If none of these are provided and the account has only one workspace, the task
    will be associated to that workspace. If the account has multiple workspaces, an error will
    be raised with a list of available workspaces.
    """
    client = AsanaClient(context.get_auth_token_or_empty())

    parent_task_id, project_id, workspace_id = await handle_new_task_associations(
        context, parent_task_id, project, workspace_id
    )

    tag_ids = await handle_new_task_tags(context, tags, workspace_id)

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


@tool(requires_auth=Asana(scopes=["default"]))
async def attach_file_to_task(
    context: ToolContext,
    task_id: Annotated[str, "The ID of the task to attach the file to."],
    file_name: Annotated[
        str,
        "The name of the file to attach with format extension. E.g. 'Image.png' or 'Report.pdf'.",
    ],
    file_content_str: Annotated[
        str | None,
        "The string contents of the file to attach. Use this if the file is a text file. "
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
        except Exception as exc:
            raise ToolExecutionError(
                f"Failed to encode file content string with {file_encoding} encoding: {exc!s}"
            ) from exc
    elif file_content_base64 is not None:
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as exc:
            raise ToolExecutionError(f"Failed to decode base64 file content: {exc!s}") from exc

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
