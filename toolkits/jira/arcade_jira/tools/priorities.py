import asyncio
from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

import arcade_jira.cache as cache
from arcade_jira.client import JiraClient
from arcade_jira.constants import JIRA_API_REQUEST_TIMEOUT, PrioritySchemeOrderBy
from arcade_jira.exceptions import JiraToolExecutionError, MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    clean_priority_dict,
    clean_priority_scheme_dict,
    clean_project_dict,
    find_priorities_by_project,
    find_unique_project,
    remove_none_values,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_priority_by_id(
    context: ToolContext,
    priority_id: Annotated[str, "The ID of the priority to retrieve."],
) -> Annotated[dict[str, Any], "The priority"]:
    """Get the details of a priority by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        response = await client.get(f"/priority/{priority_id}")
    except NotFoundError:
        return {"error": f"Priority not found with id '{priority_id}'"}
    return {"priority": clean_priority_dict(response)}


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priority_schemes(
    context: ToolContext,
    scheme_name: Annotated[
        str | None, "Filter by scheme name. Defaults to None (returns all scheme names)."
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of priority schemes to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of priority schemes to skip. Defaults to 0 (start from the first scheme)."
    ] = 0,
    order_by: Annotated[
        PrioritySchemeOrderBy,
        "The order in which to return the priority schemes. Defaults to name ascending.",
    ] = PrioritySchemeOrderBy.NAME_ASCENDING,
) -> Annotated[dict[str, Any], "The priority schemes available"]:
    """Browse the priority schemes available in Jira."""
    limit = max(min(limit, 50), 1)
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        "/priorityscheme",
        params=remove_none_values({
            "startAt": offset,
            "maxResults": limit,
            "schemeName": scheme_name,
            "orderBy": order_by.to_api_value(),
        }),
    )
    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    schemes = [clean_priority_scheme_dict(scheme, cloud_name) for scheme in api_response["values"]]
    response = {
        "priority_schemes": schemes,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, schemes, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_associated_with_a_priority_scheme(
    context: ToolContext,
    scheme_id: Annotated[str, "The ID of the priority scheme to retrieve priorities for."],
    limit: Annotated[
        int,
        "The maximum number of priority schemes to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of priority schemes to skip. Defaults to 0 (start from the first scheme)."
    ] = 0,
) -> Annotated[dict[str, Any], "The priorities associated with the priority scheme"]:
    """Browse the priorities associated with a priority scheme."""
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        f"/priorityscheme/{scheme_id}/priorities",
        params={
            "startAt": offset,
            "maxResults": limit,
        },
    )
    priorities = [clean_priority_dict(priority) for priority in api_response["values"]]
    response = {
        "priorities": priorities,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, priorities, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_projects_associated_with_a_priority_scheme(
    context: ToolContext,
    scheme_id: Annotated[str, "The ID of the priority scheme to retrieve projects for."],
    project: Annotated[
        str | None, "Filter by project ID, key or name. Defaults to None (returns all projects)."
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of projects to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of projects to skip. Defaults to 0 (start from the first project)."
    ] = 0,
) -> Annotated[dict[str, Any], "The projects associated with the priority scheme"]:
    """Browse the projects associated with a priority scheme."""
    if project:
        try:
            project_data = await find_unique_project(context, project)
        except (NotFoundError, MultipleItemsFoundError) as exc:
            return {"error": exc.message}
        else:
            project = project_data["id"]

    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        f"/priorityscheme/{scheme_id}/projects",
        params=remove_none_values({
            "startAt": offset,
            "maxResults": limit,
            "projectId": project,
        }),
    )
    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    projects = [clean_project_dict(project, cloud_name) for project in api_response["values"]]
    response = {
        "projects": projects,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, projects, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_available_to_a_project(
    context: ToolContext,
    project: Annotated[str, "The ID, key or name of the project to retrieve priorities for."],
) -> Annotated[
    dict[str, Any],
    "The priorities available to be used in issues in the specified Jira project",
]:
    """Browse the priorities available to be used in issues in the specified Jira project.

    This tool may need to loop through several API calls to get all priorities associated with
    a specific project. In Jira environments with too many Projects or Priority Schemes,
    the search may take too long, and the tool call will timeout.
    """
    try:
        project_data = await find_unique_project(context, project)
    except (NotFoundError, MultipleItemsFoundError) as exc:
        return {"error": exc.message}

    try:
        return await asyncio.wait_for(
            find_priorities_by_project(context, project_data),
            timeout=JIRA_API_REQUEST_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return {"error": f"The operation timed out after {JIRA_API_REQUEST_TIMEOUT} seconds."}
    except JiraToolExecutionError as error:
        return {"error": error.message}


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_available_to_an_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve priorities for."],
) -> Annotated[dict[str, Any], "The priorities available to be used in the specified Jira issue"]:
    """Browse the priorities available to be used in the specified Jira issue."""
    from arcade_jira.tools.issues import get_issue_by_id

    issue_response = await get_issue_by_id(context, issue)
    if issue_response.get("error"):
        return cast(dict[str, Any], issue_response)

    issue_data = issue_response["issue"]
    project = issue_data["project"]["id"]

    response = await list_priorities_available_to_a_project(context, project)

    return {
        "issue": {
            "id": issue_data["id"],
            "key": issue_data["key"],
            "title": issue_data["title"],
        },
        "project": response["project"],
        "priorities_available": response["priorities_available"],
    }
