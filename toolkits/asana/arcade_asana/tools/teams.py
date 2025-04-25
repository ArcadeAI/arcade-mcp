from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.models import AsanaClient


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["teams:read"]))
async def list_teams_the_current_user_is_a_member_of(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of teams to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[int, "The offset of teams to return. Defaults to 0"] = 0,
) -> Annotated[
    dict[str, Any],
    "List teams in Asana that the current user is a member of",
]:
    """List teams in Asana that the current user is a member of"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/users/me/teams",
        params={
            "limit": limit,
            "offset": offset,
            "opt_fields": ["gid", "name", "description", "organization", "permalink_url"],
        },
    )
    return {"teams": response["data"]}
