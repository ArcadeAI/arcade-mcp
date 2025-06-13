import asyncio
import json
from collections.abc import Awaitable
from datetime import datetime
from typing import Any, Callable, TypeVar, cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_asana.constants import (
    ASANA_MAX_TIMEOUT_SECONDS,
    MAX_PROJECTS_TO_SCAN_BY_NAME,
    MAX_TAGS_TO_SCAN_BY_NAME,
    TASK_OPT_FIELDS,
    SortOrder,
    TaskSortBy,
)
from arcade_asana.exceptions import PaginationTimeoutError

ToolResponse = TypeVar("ToolResponse", bound=dict[str, Any])


def remove_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


def validate_date_format(name: str, date_str: str | None) -> None:
    if not date_str:
        return

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ToolExecutionError(f"Invalid {name} date format. Use the format YYYY-MM-DD.")


def build_task_search_query_params(
    keywords: str | None,
    completed: bool | None,
    assignee_id: str | None,
    project_id: str | None,
    team_id: str | None,
    tag_ids: list[str] | None,
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
        "text": keywords,
        "opt_fields": TASK_OPT_FIELDS,
        "sort_by": sort_by.value,
        "sort_ascending": sort_order == SortOrder.ASCENDING,
        "limit": limit,
    }
    if completed is not None:
        query_params["completed"] = completed
    if assignee_id:
        query_params["assignee.any"] = assignee_id
    if project_id:
        query_params["projects.any"] = project_id
    if team_id:
        query_params["team.any"] = team_id
    if tag_ids:
        query_params["tags.any"] = ",".join(tag_ids)

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
    project: str | None,
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
    project_id, project_name = (None, None)

    if project:
        if project.isnumeric():
            project_id = project
        else:
            project_name = project

    if project_name:
        project_data = await get_project_by_name_or_raise_error(context, project_name)
        project_id = project_data["id"]
        workspace_id = project_data["workspace"]["id"]

    if not any([parent_task_id, project_id, workspace_id]):
        workspace_id = await get_unique_workspace_id_or_raise_error(context)

    if not workspace_id and parent_task_id:
        from arcade_asana.tools.tasks import get_task_by_id  # avoid circular imports

        response = await get_task_by_id(context, parent_task_id)
        workspace_id = response["task"]["workspace"]["id"]

    return parent_task_id, project_id, workspace_id


async def get_project_by_name_or_raise_error(
    context: ToolContext,
    project_name: str,
    max_items_to_scan: int = MAX_PROJECTS_TO_SCAN_BY_NAME,
) -> dict[str, Any]:
    response = await find_projects_by_name(
        context=context,
        names=[project_name],
        response_limit=100,
        max_items_to_scan=max_items_to_scan,
        return_projects_not_matched=True,
    )

    if not response["matches"]["projects"]:
        projects = response["not_matched"]["projects"]
        projects = [{"name": project["name"], "id": project["id"]} for project in projects]
        message = (
            f"Project with name '{project_name}' was not found. The search scans up to "
            f"{max_items_to_scan} projects. If the user account has a larger number of projects, "
            "it's possible that it exists, but the search didn't find it."
        )
        additional_prompt = f"Projects available: {json.dumps(projects)}"
        raise RetryableToolError(
            message=message,
            developer_message=f"{message} {additional_prompt}",
            additional_prompt_content=additional_prompt,
        )

    elif response["matches"]["count"] > 1:
        projects = [
            {"name": project["name"], "id": project["id"]}
            for project in response["matches"]["projects"]
        ]
        message = "Multiple projects found with the same name. Please provide a project ID instead."
        additional_prompt = f"Projects matching the name '{project_name}': {json.dumps(projects)}"
        raise RetryableToolError(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )

    return cast(dict, response["matches"]["projects"][0])


async def handle_new_task_tags(
    context: ToolContext,
    tags: list[str] | None,
    workspace_id: str | None,
) -> list[str] | None:
    if not tags:
        return None

    tag_ids = []
    tag_names = []
    for tag in tags:
        if tag.isnumeric():
            tag_ids.append(tag)
        else:
            tag_names.append(tag)

    if tag_names:
        response = await find_tags_by_name(context, tag_names)
        tag_ids.extend([tag["id"] for tag in response["matches"]["tags"]])

        if response["not_found"]["tags"]:
            from arcade_asana.tools.tags import create_tag  # avoid circular imports

            responses = await asyncio.gather(*[
                create_tag(context, name=name, workspace_id=workspace_id)
                for name in response["not_found"]["tags"]
            ])
            tag_ids.extend([response["tag"]["id"] for response in responses])

    return tag_ids


async def get_tag_ids(
    context: ToolContext,
    tags: list[str] | None,
    max_items_to_scan: int = MAX_TAGS_TO_SCAN_BY_NAME,
) -> list[str] | None:
    """
    Returns the IDs of the tags provided in the tags list, which can be either tag IDs or tag names.

    If the tags list is empty, it returns None.
    """
    tag_ids = []
    tag_names = []

    if tags:
        for tag in tags:
            if tag.isnumeric():
                tag_ids.append(tag)
            else:
                tag_names.append(tag)

    if tag_names:
        searched_tags = await find_tags_by_name(
            context=context,
            names=tag_names,
            max_items_to_scan=max_items_to_scan,
        )

        if searched_tags["not_found"]["tags"]:
            tag_names_not_found = ", ".join(searched_tags["not_found"]["tags"])
            raise ToolExecutionError(
                f"Tags not found: {tag_names_not_found}. The search scans up to "
                f"{max_items_to_scan} tags. If the user account has a larger number of tags, "
                "it's possible that the tags exist, but the search didn't find them."
            )

        tag_ids.extend([tag["id"] for tag in searched_tags["matches"]["tags"]])

    return tag_ids if tag_ids else None


async def paginate_tool_call(
    tool: Callable[[ToolContext, Any], Awaitable[ToolResponse]],
    context: ToolContext,
    response_key: str,
    max_items: int = 300,
    timeout_seconds: int = ASANA_MAX_TIMEOUT_SECONDS,
    next_page_token: str | None = None,
    **tool_kwargs: Any,
) -> list[ToolResponse]:
    results: list[ToolResponse] = []

    async def paginate_loop() -> None:
        nonlocal results
        keep_paginating = True

        if "limit" not in tool_kwargs:
            tool_kwargs["limit"] = 100

        while keep_paginating:
            response = await tool(context, **tool_kwargs)  # type: ignore[call-arg]
            results.extend(response[response_key])
            next_page = get_next_page(response)
            next_page_token = next_page["next_page_token"]
            if not next_page_token or len(results) >= max_items:
                keep_paginating = False
            else:
                tool_kwargs["next_page_token"] = next_page_token

    try:
        await asyncio.wait_for(paginate_loop(), timeout=timeout_seconds)
    except TimeoutError:
        raise PaginationTimeoutError(timeout_seconds, tool.__tool_name__)  # type: ignore[attr-defined]
    else:
        return results


async def get_unique_workspace_id_or_raise_error(context: ToolContext) -> str:
    # Importing here to avoid circular imports
    from arcade_asana.tools.workspaces import list_workspaces

    workspaces = await list_workspaces(context)
    if len(workspaces["workspaces"]) == 1:
        return cast(str, workspaces["workspaces"][0]["id"])
    else:
        message = "User has multiple workspaces. Please provide a workspace ID."
        additional_prompt = f"Workspaces available: {json.dumps(workspaces['workspaces'])}"
        raise RetryableToolError(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )


async def find_projects_by_name(
    context: ToolContext,
    names: list[str],
    team_id: list[str] | None = None,
    response_limit: int = 100,
    max_items_to_scan: int = MAX_PROJECTS_TO_SCAN_BY_NAME,
    return_projects_not_matched: bool = False,
) -> dict[str, Any]:
    """Find projects by name using exact match

    This function will paginate the list_projects tool call and return the projects that match
    the names provided. If the names provided are not found, it will return the names searched for
    that did not match any projects.

    If return_projects_not_matched is True, it will also return the projects that were scanned,
    but did not match any of the names searched for.

    Args:
        context: The tool context to use in the list_projects tool call.
        names: The names of the projects to search for.
        team_id: The ID of the team to search for projects in.
        response_limit: The maximum number of matched projects to return.
        max_items_to_scan: The maximum number of projects to scan while looking for matches.
        return_projects_not_matched: Whether to return the projects that were scanned, but did not
            match any of the names searched for.
    """
    from arcade_asana.tools.projects import list_projects  # avoid circular imports

    names_lower = {name.casefold() for name in names}

    projects = await paginate_tool_call(
        tool=list_projects,
        context=context,
        response_key="projects",
        max_items=max_items_to_scan,
        timeout_seconds=15,
        team_id=team_id,
    )

    matches: list[dict[str, Any]] = []
    not_matched: list[str] = []

    for project in projects:
        project_name_lower = project["name"].casefold()
        if len(matches) >= response_limit:
            break
        if project_name_lower in names_lower:
            matches.append(project)
            names_lower.remove(project_name_lower)
        else:
            not_matched.append(project)

    not_found = [name for name in names if name.casefold() in names_lower]

    response = {
        "matches": {
            "projects": matches,
            "count": len(matches),
        },
        "not_found": {
            "names": not_found,
            "count": len(not_found),
        },
    }

    if return_projects_not_matched:
        response["not_matched"] = {
            "projects": not_matched,
            "count": len(not_matched),
        }

    return response


async def find_tags_by_name(
    context: ToolContext,
    names: list[str],
    workspace_id: list[str] | None = None,
    response_limit: int = 100,
    max_items_to_scan: int = MAX_TAGS_TO_SCAN_BY_NAME,
    return_tags_not_matched: bool = False,
) -> dict[str, Any]:
    """Find tags by name using exact match

    This function will paginate the list_tags tool call and return the tags that match the names
    provided. If the names provided are not found, it will return the names searched for that did
    not match any tags.

    If return_tags_not_matched is True, it will also return the tags that were scanned, but did not
    match any of the names searched for.

    Args:
        context: The tool context to use in the list_tags tool call.
        names: The names of the tags to search for.
        workspace_id: The ID of the workspace to search for tags in.
        response_limit: The maximum number of matched tags to return.
        max_items_to_scan: The maximum number of tags to scan while looking for matches.
        return_tags_not_matched: Whether to return the tags that were scanned, but did not match
            any of the names searched for.
    """
    from arcade_asana.tools.tags import list_tags  # avoid circular imports

    names_lower = {name.casefold() for name in names}

    tags = await paginate_tool_call(
        tool=list_tags,
        context=context,
        response_key="tags",
        max_items=max_items_to_scan,
        timeout_seconds=15,
        workspace_id=workspace_id,
    )

    matches: list[dict[str, Any]] = []
    not_matched: list[str] = []
    for tag in tags:
        tag_name_lower = tag["name"].casefold()
        if len(matches) >= response_limit:
            break
        if tag_name_lower in names_lower:
            matches.append(tag)
            names_lower.remove(tag_name_lower)
        else:
            not_matched.append(tag["name"])

    not_found = [name for name in names if name.casefold() in names_lower]

    response = {
        "matches": {
            "tags": matches,
            "count": len(matches),
        },
        "not_found": {
            "tags": not_found,
            "count": len(not_found),
        },
    }

    if return_tags_not_matched:
        response["not_matched"] = {
            "tags": not_matched,
            "count": len(not_matched),
        }

    return response


def get_next_page(response: dict[str, Any]) -> dict[str, Any]:
    try:
        token = response["next_page"]["offset"]
    except (KeyError, TypeError):
        token = None

    return {"has_more_pages": token is not None, "next_page_token": token}
