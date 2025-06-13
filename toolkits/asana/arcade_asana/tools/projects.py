from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana

from arcade_asana.constants import PROJECT_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    get_next_page,
    get_unique_workspace_id_or_raise_error,
    remove_none_values,
)


@tool(requires_auth=Asana(scopes=["default"]))
async def get_project_by_id(
    context: ToolContext,
    project_id: Annotated[str, "The ID of the project."],
) -> Annotated[
    dict[str, Any],
    "Get a project by its ID",
]:
    """Get an Asana project by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/projects/{project_id}",
        params={"opt_fields": PROJECT_OPT_FIELDS},
    )
    return {"project": response["data"]}


@tool(requires_auth=Asana(scopes=["default"]))
async def list_projects(
    context: ToolContext,
    team_id: Annotated[
        str | None,
        "The team ID to get projects from. Defaults to None (does not filter by team).",
    ] = None,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to get projects from. Defaults to None. If not provided and the user "
        "has only one workspace, it will use that workspace. If not provided and the user has "
        "multiple workspaces, it will raise an error listing the available workspaces.",
    ] = None,
    limit: Annotated[
        int, "The maximum number of projects to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of projects. Defaults to None (start from the first "
        "page of projects).",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "List projects in Asana associated to teams the current user is a member of",
]:
    """List projects in Asana"""
    # Note: Asana recommends filtering by team to avoid timeout in large domains.
    # Ref: https://developers.asana.com/reference/getprojects
    limit = max(1, min(100, limit))

    workspace_id = workspace_id or await get_unique_workspace_id_or_raise_error(context)

    client = AsanaClient(context.get_auth_token_or_empty())

    response = await client.get(
        "/projects",
        params=remove_none_values({
            "limit": limit,
            "offset": next_page_token,
            "team": team_id,
            "workspace": workspace_id,
            "opt_fields": PROJECT_OPT_FIELDS,
        }),
    )

    return {
        "projects": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }
