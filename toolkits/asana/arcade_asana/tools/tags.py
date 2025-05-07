import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2
from arcade.sdk.errors import ToolExecutionError

from arcade_asana.constants import TAG_OPT_FIELDS, TagColor
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    clean_request_params,
    get_unique_workspace_id_or_raise_error,
    remove_none_values,
)


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def create_tag(
    context: ToolContext,
    name: Annotated[str, "The name of the tag to create. Length must be between 1 and 100."],
    description: Annotated[
        str | None, "The description of the tag to create. Defaults to None (no description)."
    ] = None,
    color: Annotated[
        TagColor | None, "The color of the tag to create. Defaults to None (no color)."
    ] = None,
    workspace_id: Annotated[
        str | None,
        "The ID of the workspace to create the tag in. If not provided, it will associated the tag "
        "to a current workspace, if there's only one. Otherwise, it will raise an error.",
    ] = None,
) -> Annotated[dict[str, Any], "The created tag."]:
    """Create a tag in Asana"""
    if not 1 <= len(name) <= 100:
        raise ToolExecutionError("Tag name must be between 1 and 100 characters long.")

    workspace_id = workspace_id or await get_unique_workspace_id_or_raise_error(context)

    data = remove_none_values({
        "name": name,
        "notes": description,
        "color": color.value if color else None,
        "workspace": workspace_id,
    })

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.post("/tags", json_data={"data": data})
    return {"tag": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=[]))
async def list_tags(
    context: ToolContext,
    workspace_ids: Annotated[
        list[str] | None,
        "The IDs of the workspaces to search for tags in. "
        "If not provided, it will search across all workspaces.",
    ] = None,
    limit: Annotated[
        int, "The maximum number of tags to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[
        int | None, "The offset of tags to return. Defaults to 0 (first page of results)"
    ] = 0,
) -> Annotated[
    dict[str, Any],
    "List tags in Asana that are visible to the authenticated user",
]:
    """List tags in Asana that are visible to the authenticated user"""
    if not workspace_ids:
        from arcade_asana.tools.workspaces import list_workspaces  # avoid circular import

        workspaces = await list_workspaces(context)
        workspace_ids = [workspace["id"] for workspace in workspaces["workspaces"]]

    client = AsanaClient(context.get_auth_token_or_empty())
    responses = await asyncio.gather(*[
        client.get(
            "/tags",
            params=clean_request_params({
                "limit": limit,
                "offset": offset,
                "workspace": workspace_id,
                "opt_fields": TAG_OPT_FIELDS,
            }),
        )
        for workspace_id in workspace_ids
    ])

    tags = [tag for response in responses for tag in response["data"]]

    return {"tags": tags, "count": len(tags)}
