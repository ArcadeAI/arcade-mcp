from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana

from arcade_asana.constants import WORKSPACE_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import get_next_page, remove_none_values


@tool(requires_auth=Asana(scopes=["default"]))
async def get_workspace_by_id(
    context: ToolContext,
    workspace_id: Annotated[str, "The ID of the Asana workspace to get"],
) -> Annotated[dict[str, Any], "Get an Asana workspace by its ID"]:
    """Get an Asana workspace by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(f"/workspaces/{workspace_id}")
    return {"workspace": response["data"]}


@tool(requires_auth=Asana(scopes=["default"]))
async def list_workspaces(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of workspaces to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of workspaces. Defaults to None (start from the first "
        "page of workspaces)",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "List workspaces in Asana that are visible to the authenticated user",
]:
    """List workspaces in Asana that are visible to the authenticated user"""
    limit = max(1, min(100, limit))

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/workspaces",
        params=remove_none_values({
            "limit": limit,
            "offset": next_page_token,
            "opt_fields": WORKSPACE_OPT_FIELDS,
        }),
    )

    return {
        "workspaces": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }
