import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.constants import TEAM_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import clean_request_params


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def get_team_by_id(
    context: ToolContext,
    team_id: Annotated[str, "The ID of the Asana team to get"],
) -> Annotated[dict[str, Any], "Get an Asana team by its ID"]:
    """Get an Asana team by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/teams/{team_id}", params=clean_request_params({"opt_fields": TEAM_OPT_FIELDS})
    )
    return {"team": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def list_teams_the_current_user_is_a_member_of(
    context: ToolContext,
    workspace_ids: Annotated[
        list[str] | None,
        "The IDs of the workspaces to get teams from. "
        "Defaults to None (get teams from all workspaces the user is a member of).",
    ] = None,
    limit: Annotated[
        int, "The maximum number of teams to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[
        int | None,
        "The pagination offset of teams to skip in the results. "
        "Defaults to 0 (first page of results)",
    ] = 0,
) -> Annotated[
    dict[str, Any],
    "List teams in Asana that the current user is a member of",
]:
    """List teams in Asana that the current user is a member of"""
    limit = max(1, min(100, limit))

    if not workspace_ids:
        # Importing here to avoid circular imports
        from arcade_asana.tools.workspaces import list_workspaces

        response = await list_workspaces(context)
        workspace_ids = [workspace["id"] for workspace in response["workspaces"]]

    client = AsanaClient(context.get_auth_token_or_empty())
    responses = await asyncio.gather(*[
        client.get(
            "/users/me/teams",
            params=clean_request_params({
                "limit": limit,
                "offset": offset,
                "opt_fields": TEAM_OPT_FIELDS,
                "organization": workspace_id,
            }),
        )
        for workspace_id in workspace_ids
    ])

    teams = [team for response in responses for team in response["data"]]

    return {
        "teams": teams,
        "count": len(teams),
    }
