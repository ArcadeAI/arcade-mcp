from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.constants import USER_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import clean_request_params, get_unique_workspace_id_or_raise_error


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def list_users(
    context: ToolContext,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to list users from. Defaults to None (list users from all workspaces).",
    ] = None,
    limit: Annotated[
        int, "The maximum number of users to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[
        int | None, "The offset of users to return. Defaults to 0 (first page of results)"
    ] = 0,
) -> Annotated[
    dict[str, Any],
    "List users in Asana",
]:
    """List users in Asana"""
    limit = max(1, min(100, limit))

    if not workspace_id:
        workspace_id = await get_unique_workspace_id_or_raise_error(context)

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/users",
        params=clean_request_params({
            "workspace": workspace_id,
            "limit": limit,
            "offset": offset,
            "opt_fields": USER_OPT_FIELDS,
        }),
    )

    return {
        "users": response["data"],
        "count": len(response["data"]),
    }


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def get_user_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The user ID to get."],
) -> Annotated[dict[str, Any], "The user information."]:
    """Get a user by ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(f"/users/{user_id}", params={"opt_fields": USER_OPT_FIELDS})
    return {"user": response}
