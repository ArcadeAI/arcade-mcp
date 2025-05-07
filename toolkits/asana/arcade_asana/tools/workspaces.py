from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.constants import WORKSPACE_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import clean_request_params


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def list_workspaces(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of workspaces to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[
        int | None, "The offset of workspaces to return. Defaults to 0 (first page of results)"
    ] = 0,
) -> Annotated[
    dict[str, Any],
    "List workspaces in Asana that are visible to the authenticated user",
]:
    """List workspaces in Asana that are visible to the authenticated user"""
    limit = max(1, min(100, limit))

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/workspaces",
        params=clean_request_params({
            "limit": limit,
            "offset": offset,
            "opt_fields": WORKSPACE_OPT_FIELDS,
        }),
    )

    return {
        "workspaces": response["data"],
        "count": len(response["data"]),
    }
