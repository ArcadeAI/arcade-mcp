from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_confluence.client import ConfluenceClientV2
from arcade_confluence.enums import AttachmentSortOrder
from arcade_confluence.utils import remove_none_values


@tool(
    requires_auth=Atlassian(
        scopes=["read:attachment:confluence"],
    )
)
async def list_attachments(
    context: ToolContext,
    sort_order: Annotated[
        AttachmentSortOrder,
        "The order of the attachments to sort by. Defaults to created-date-newest-to-oldest",
    ] = AttachmentSortOrder.CREATED_DATE_DESCENDING,
    limit: Annotated[
        int, "The maximum number of attachments to return. Defaults to 25. Max is 250"
    ] = 25,
    pagination_token: Annotated[
        str | None,
        "The pagination token to use for the next page of results",
    ] = None,
) -> Annotated[dict, "The attachments"]:
    """List attachments in a workspace"""
    client = ConfluenceClientV2(context.get_auth_token_or_empty())
    params = remove_none_values({
        "sort": sort_order.to_api_value(),
        "limit": max(1, min(limit, 250)),
        "cursor": pagination_token,
    })
    attachments = await client.get("attachments", params=params)
    return client.transform_get_attachments_response(attachments)


@tool(
    requires_auth=Atlassian(
        scopes=["read:attachment:confluence"],
    )
)
async def get_attachments_for_page(
    context: ToolContext,
    page_identifier: Annotated[str, "The ID or title of the page to get attachments for"],
    limit: Annotated[
        int, "The maximum number of attachments to return. Defaults to 25. Max is 250"
    ] = 25,
    pagination_token: Annotated[
        str | None,
        "The pagination token to use for the next page of results",
    ] = None,
) -> Annotated[dict, "The attachments"]:
    """Get attachments for a page by its ID or title.

    If a page title is provided, then the first page with an exact matching title will be returned.
    """
    client = ConfluenceClientV2(context.get_auth_token_or_empty())
    page_id = await client.get_page_id(page_identifier)

    params = remove_none_values({
        "limit": max(1, min(limit, 250)),
        "cursor": pagination_token,
    })
    attachments = await client.get(f"pages/{page_id}/attachments", params=params)
    return client.transform_get_attachments_response(attachments)
