from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana

from arcade_asana.constants import USER_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    get_next_page,
    get_unique_workspace_id_or_raise_error,
    remove_none_values,
)


@tool(requires_auth=Asana(scopes=["default"]))
async def list_users(
    context: ToolContext,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to list users from. Defaults to None. If no workspace ID is provided, "
        "it will use the current user's workspace , if there's only one. If the user has multiple "
        "workspaces, it will raise an error.",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of users to retrieve. Min is 1, max is 100. Defaults to 100.",
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of users. Defaults to None (start from the first page "
        "of users)",
    ] = None,
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
        params=remove_none_values({
            "workspace": workspace_id,
            "limit": limit,
            "offset": next_page_token,
            "opt_fields": USER_OPT_FIELDS,
        }),
    )

    return {
        "users": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }


@tool(requires_auth=Asana(scopes=["default"]))
async def get_user_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The user ID to get."],
) -> Annotated[dict[str, Any], "The user information."]:
    """Get a user by ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(f"/users/{user_id}", params={"opt_fields": USER_OPT_FIELDS})
    return {"user": response}
