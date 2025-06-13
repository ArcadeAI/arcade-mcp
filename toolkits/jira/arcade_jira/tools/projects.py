from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

import arcade_jira.cache as cache
from arcade_jira.client import JiraClient
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    clean_project_dict,
    remove_none_values,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_projects(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of projects to return. Min of 1, Max of 50. Defaults to 50."
    ] = 50,
    offset: Annotated[
        int, "The number of projects to skip. Defaults to 0 (starts from the first project)"
    ] = 0,
) -> Annotated[dict[str, Any], "Information about the projects"]:
    """Browse projects available in Jira."""
    return cast(
        dict[str, Any], await search_projects(context, keywords=None, limit=limit, offset=offset)
    )


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def search_projects(
    context: ToolContext,
    keywords: Annotated[
        str | None,
        "The keywords to search for projects. Matches against project name and key "
        "(case insensitive). Defaults to None (no keywords filter).",
    ] = None,
    limit: Annotated[
        int, "The maximum number of projects to return. Min of 1, Max of 50. Defaults to 50."
    ] = 50,
    offset: Annotated[
        int, "The number of projects to skip. Defaults to 0 (starts from the first project)"
    ] = 0,
) -> Annotated[dict[str, Any], "Information about the projects"]:
    """Get the details of all Jira projects."""
    limit = max(min(limit, 50), 1)
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        "/project/search",
        params=remove_none_values({
            "expand": ",".join([
                "description",
                "url",
            ]),
            "maxResults": limit,
            "startAt": offset,
            "query": keywords,
        }),
    )
    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    projects = [clean_project_dict(project, cloud_name) for project in api_response["values"]]
    response = {
        "projects": projects,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, projects, limit, offset)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_project_by_id(
    context: ToolContext,
    project: Annotated[str, "The ID or key of the project to retrieve"],
) -> Annotated[dict[str, Any], "Information about the project"]:
    """Get the details of a Jira project by its ID or key."""
    client = JiraClient(context.get_auth_token_or_empty())

    try:
        response = await client.get(f"project/{project}")
    except NotFoundError:
        return {"error": f"Project not found: {project}"}

    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    return {"project": clean_project_dict(response, cloud_name)}
