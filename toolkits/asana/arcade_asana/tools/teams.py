from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana

from arcade_asana.constants import TEAM_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    get_next_page,
    get_unique_workspace_id_or_raise_error,
    remove_none_values,
)


@tool(requires_auth=Asana(scopes=["default"]))
async def get_team_by_id(
    context: ToolContext,
    team_id: Annotated[str, "The ID of the Asana team to get"],
) -> Annotated[dict[str, Any], "Get an Asana team by its ID"]:
    """Get an Asana team by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/teams/{team_id}",
        params=remove_none_values({"opt_fields": TEAM_OPT_FIELDS}),
    )
    return {"team": response["data"]}


@tool(requires_auth=Asana(scopes=["default"]))
async def list_teams_the_current_user_is_a_member_of(
    context: ToolContext,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to list teams from. Defaults to None. If no workspace ID is provided, "
        "it will use the current user's workspace , if there's only one. If the user has multiple "
        "workspaces, it will raise an error.",
    ] = None,
    limit: Annotated[
        int, "The maximum number of teams to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of teams. Defaults to None (start from the first page "
        "of teams)",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "List teams in Asana that the current user is a member of",
]:
    """List teams in Asana that the current user is a member of"""
    limit = max(1, min(100, limit))

    workspace_id = workspace_id or await get_unique_workspace_id_or_raise_error(context)

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/users/me/teams",
        params=remove_none_values({
            "limit": limit,
            "offset": next_page_token,
            "opt_fields": TEAM_OPT_FIELDS,
            "organization": workspace_id,
        }),
    )

    return {
        "teams": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }


@tool(requires_auth=Asana(scopes=["default"]))
async def list_teams(
    context: ToolContext,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to list teams from. Defaults to None. If no workspace ID is provided, "
        "it will use the current user's workspace, if there's only one. If the user has multiple "
        "workspaces, it will raise an error listing the available workspaces.",
    ] = None,
    limit: Annotated[
        int, "The maximum number of teams to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of teams. Defaults to None (start from the first page "
        "of teams)",
    ] = None,
) -> Annotated[dict[str, Any], "List teams in an Asana workspace"]:
    """List teams in an Asana workspace"""
    limit = max(1, min(100, limit))

    workspace_id = workspace_id or await get_unique_workspace_id_or_raise_error(context)

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/workspaces/{workspace_id}/teams",
        params=remove_none_values({
            "limit": limit,
            "offset": next_page_token,
            "opt_fields": TEAM_OPT_FIELDS,
        }),
    )

    return {
        "teams": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }
