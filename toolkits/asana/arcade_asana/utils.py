import asyncio
import json
from typing import Any, Callable

from arcade.sdk import ToolContext
from arcade.sdk.errors import RetryableToolError, ToolExecutionError

from arcade_asana.constants import TASK_OPT_FIELDS, SortOrder, TaskSortBy
from arcade_asana.exceptions import PaginationTimeoutError


def remove_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


def clean_request_params(params: dict[str, Any]) -> dict[str, Any]:
    params = remove_none_values(params)
    if "offset" in params and params["offset"] == 0:
        del params["offset"]

    return params


def build_task_search_query_params(
    workspace_id: str,
    keywords: str,
    completed: bool,
    assignee_ids: list[str] | None,
    project_ids: list[str] | None,
    team_ids: list[str] | None,
    tags: list[str] | None,
    due_on: str | None,
    due_on_or_after: str | None,
    due_on_or_before: str | None,
    start_on: str | None,
    start_on_or_after: str | None,
    start_on_or_before: str | None,
    limit: int,
    sort_by: TaskSortBy,
    sort_order: SortOrder,
) -> dict[str, Any]:
    query_params: dict[str, Any] = {
        "workspace": workspace_id,
        "text": keywords,
        "opt_fields": TASK_OPT_FIELDS,
        "completed": completed,
        "sort_by": sort_by.value,
        "sort_ascending": sort_order == SortOrder.ASCENDING,
        "limit": limit,
    }
    if assignee_ids:
        query_params["assignee.any"] = ",".join(assignee_ids)
    if project_ids:
        query_params["projects.any"] = ",".join(project_ids)
    if team_ids:
        query_params["team.any"] = ",".join(team_ids)
    if tags:
        query_params["tags.any"] = ",".join(tags)

    query_params = add_task_search_date_params(
        query_params,
        due_on,
        due_on_or_after,
        due_on_or_before,
        start_on,
        start_on_or_after,
        start_on_or_before,
    )

    return query_params


def add_task_search_date_params(
    query_params: dict[str, Any],
    due_on: str | None,
    due_on_or_after: str | None,
    due_on_or_before: str | None,
    start_on: str | None,
    start_on_or_after: str | None,
    start_on_or_before: str | None,
) -> dict[str, Any]:
    """
    Builds the date-related query parameters for task search.

    If a date is provided, it will be added to the query parameters. If not, it will be ignored.
    """
    if due_on:
        query_params["due_on"] = due_on
    if due_on_or_after:
        query_params["due_on.after"] = due_on_or_after
    if due_on_or_before:
        query_params["due_on.before"] = due_on_or_before
    if start_on:
        query_params["start_on"] = start_on
    if start_on_or_after:
        query_params["start_on.after"] = start_on_or_after
    if start_on_or_before:
        query_params["start_on.before"] = start_on_or_before

    return query_params


async def handle_new_task_associations(
    context: ToolContext,
    parent_task_id: str | None,
    project_id: str | None,
    project_name: str | None,
    workspace_id: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Handles the association of a new task to a parent task, project, or workspace.

    If no association is provided, it will try to find a workspace in the user's account.
    In case the user has only one workspace, it will use that workspace.
    Otherwise, it will raise an error.

    If a workspace_id is not provided, but a parent_task_id or a project_id is provided, it will try
    to find the workspace associated with the parent task or project.

    In each of the two cases explained above, if a workspace is found, the function will return this
    value, even if the workspace_id argument was None.

    Returns a tuple of (parent_task_id, project_id, workspace_id).
    """
    if project_id and project_name:
        raise RetryableToolError(
            "Provide none or at most one of project_id and project_name, never both."
        )

    if not any([parent_task_id, project_id, project_name, workspace_id]):
        workspace_id = await get_unique_workspace_id_or_raise_error(context)

    if not workspace_id:
        if parent_task_id:
            from arcade_asana.tools.tasks import get_task_by_id  # avoid circular imports

            response = await get_task_by_id(context, parent_task_id)
            workspace_id = response["task"]["workspace"]["gid"]
        else:
            project_id, workspace_id = await handle_task_project_association(
                context, project_id, project_name, workspace_id
            )

    return parent_task_id, project_id, workspace_id


async def handle_task_project_association(
    context: ToolContext,
    project_id: str | None,
    project_name: str | None,
    workspace_id: str | None,
) -> tuple[str | None, str | None]:
    if all([project_id, project_name]):
        raise ToolExecutionError(
            "Provide none or at most one of project_id and project_name, never both."
        )

    if project_id:
        from arcade_asana.tools.projects import get_project_by_id  # avoid circular imports

        response = await get_project_by_id(context, project_id)
        workspace_id = response["project"]["workspace"]["gid"]

    elif project_name:
        project = await get_project_by_name_or_raise_error(context, project_name)
        project_id = project["gid"]
        workspace_id = project["workspace"]["gid"]

    return project_id, workspace_id


async def get_project_by_name_or_raise_error(
    context: ToolContext, project_name: str
) -> dict[str, Any]:
    # Avoid circular imports
    from arcade_asana.tools.projects import search_projects_by_name

    response = await search_projects_by_name(
        context, names=[project_name], limit=1, return_projects_not_matched=True
    )

    if not response["matches"]["projects"]:
        projects = response["not_matched"]["projects"]
        projects = [{"name": project["name"], "gid": project["gid"]} for project in projects]
        message = f"Project with name '{project_name}' not found."
        additional_prompt = f"Projects available: {json.dumps(projects)}"
        raise RetryableToolError(
            message=message,
            developer_message=f"{message} {additional_prompt}",
            additional_prompt_content=additional_prompt,
        )

    return response["matches"]["projects"][0]


async def handle_new_task_tags(
    context: ToolContext,
    tag_names: list[str] | None,
    tag_ids: list[str] | None,
    workspace_id: str | None,
) -> list[str]:
    if tag_ids and tag_names:
        raise ToolExecutionError(
            "Provide none or at most one of tag_names and tag_ids, never both."
        )

    if tag_names:
        from arcade_asana.tools.tags import create_tag, search_tags_by_name

        response = await search_tags_by_name(context, tag_names)
        tag_ids = [tag["gid"] for tag in response["matches"]["tags"]]

        if response["not_found"]["names"]:
            responses = await asyncio.gather(*[
                create_tag(context, name=name, workspace_id=workspace_id)
                for name in response["not_found"]["names"]
            ])
            tag_ids = [response["tag"]["gid"] for response in responses]

    return tag_ids


async def paginate_tool_call(
    tool: Callable[[ToolContext, Any], dict],
    context: ToolContext,
    response_key: str,
    max_items: int = 300,
    timeout_seconds: int = 10,
    **tool_kwargs: Any,
) -> dict:
    results: list[dict[str, Any]] = []

    async def paginate_loop() -> None:
        nonlocal results
        keep_paginating = True

        if "limit" not in tool_kwargs:
            tool_kwargs["limit"] = 100

        while keep_paginating:
            response = await tool(context, **tool_kwargs)
            results.extend(response[response_key])
            if "offset" not in tool_kwargs:
                tool_kwargs["offset"] = 0
            if "next_page" not in response or len(results) >= max_items:
                keep_paginating = False
            else:
                tool_kwargs["offset"] += tool_kwargs["limit"]

    try:
        await asyncio.wait_for(paginate_loop(), timeout=timeout_seconds)
    except TimeoutError:
        raise PaginationTimeoutError(timeout_seconds, tool.__tool_name__)
    else:
        return results


async def get_unique_workspace_id_or_raise_error(context: ToolContext) -> str:
    # Importing here to avoid circular imports
    from arcade_asana.tools.workspaces import list_workspaces

    workspaces = await list_workspaces(context)
    if len(workspaces["workspaces"]) == 1:
        return workspaces["workspaces"][0]["gid"]
    else:
        message = "User has multiple workspaces. Please provide a workspace ID."
        additional_prompt = f"Workspaces available: {json.dumps(workspaces['workspaces'])}"
        raise RetryableToolError(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )
