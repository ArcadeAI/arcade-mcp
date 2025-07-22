from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    clean_project_dict,
    remove_none_values,
    resolve_cloud_id,
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
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the projects"]:
    """Browse projects available in Jira."""
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    return cast(
        dict[str, Any],
        await search_projects(
            context=context,
            keywords=None,
            limit=limit,
            offset=offset,
            atlassian_cloud_id=atlassian_cloud_id,
        ),
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
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the projects"]:
    """Get the details of all Jira projects."""
    limit = max(min(limit, 50), 1)
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)
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

    projects = [clean_project_dict(project) for project in api_response["values"]]
    response = {
        "projects": projects,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, projects, limit, offset)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_project_by_id(
    context: ToolContext,
    project: Annotated[str, "The ID or key of the project to retrieve"],
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the project"]:
    """Get the details of a Jira project by its ID or key."""
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)

    try:
        response = await client.get(f"project/{project}")
    except NotFoundError:
        return {"error": f"Project not found: {project}"}

    return {"project": clean_project_dict(response)}
