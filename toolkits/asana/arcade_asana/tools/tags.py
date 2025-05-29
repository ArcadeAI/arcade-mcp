from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Asana
from arcade_tdk.errors import ToolExecutionError

from arcade_asana.constants import TAG_OPT_FIELDS, TagColor
from arcade_asana.models import AsanaClient
from arcade_asana.utils import (
    get_next_page,
    get_unique_workspace_id_or_raise_error,
    remove_none_values,
)


@tool(requires_auth=Asana(scopes=["default"]))
async def get_tag_by_id(
    context: ToolContext,
    tag_id: Annotated[str, "The ID of the Asana tag to get"],
) -> Annotated[dict[str, Any], "Get an Asana tag by its ID"]:
    """Get an Asana tag by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(f"/tags/{tag_id}")
    return {"tag": response["data"]}


@tool(requires_auth=Asana(scopes=["default"]))
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


@tool(requires_auth=Asana(scopes=["default"]))
async def list_tags(
    context: ToolContext,
    workspace_id: Annotated[
        str | None,
        "The workspace ID to retrieve tags from. Defaults to None. If not provided and the user "
        "has only one workspace, it will use that workspace. If not provided and the user has "
        "multiple workspaces, it will raise an error listing the available workspaces.",
    ] = None,
    limit: Annotated[
        int, "The maximum number of tags to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    next_page_token: Annotated[
        str | None,
        "The token to retrieve the next page of tags. Defaults to None (start from the first page "
        "of tags)",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "List tags in an Asana workspace",
]:
    """List tags in an Asana workspace"""
    limit = max(1, min(100, limit))

    workspace_id = workspace_id or await get_unique_workspace_id_or_raise_error(context)

    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        "/tags",
        params=remove_none_values({
            "limit": limit,
            "offset": next_page_token,
            "workspace": workspace_id,
            "opt_fields": TAG_OPT_FIELDS,
        }),
    )

    return {
        "tags": response["data"],
        "count": len(response["data"]),
        "next_page": get_next_page(response),
    }
