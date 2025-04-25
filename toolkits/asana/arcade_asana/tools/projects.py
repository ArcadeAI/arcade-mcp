import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.models import AsanaClient
from arcade_asana.tools.teams import list_teams_the_current_user_is_a_member_of


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["projects:read"]))
async def list_projects(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of projects to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[int, "The offset of projects to return. Defaults to 0"] = 0,
) -> Annotated[
    dict[str, Any],
    "List projects in Asana associated to teams the current user is a member of",
]:
    """List projects in Asana associated to teams the current user is a member of"""
    # Note: Asana recommends filtering by team to avoid timeout in large domains.
    # Ref: https://developers.asana.com/reference/getprojects
    user_teams = await list_teams_the_current_user_is_a_member_of(context)

    client = AsanaClient(context.get_auth_token_or_empty())

    responses = await asyncio.gather(*[
        client.get(
            "/projects",
            params={
                "limit": limit,
                "offset": offset,
                "team": team["gid"],
                "opt_fields": [
                    "gid",
                    "name",
                    "current_status_update",
                    "due_date",
                    "start_on",
                    "notes",
                    "members",
                    "completed",
                    "completed_at",
                    "completed_by",
                    "owner",
                    "team",
                    "workspace",
                    "permalink_url",
                ],
            },
        )
        for team in user_teams["teams"]
    ])

    return {"projects": [project for response in responses for project in response["data"]]}
