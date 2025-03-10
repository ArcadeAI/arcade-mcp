from typing import Annotated, Any, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion
from arcade.sdk.errors import RetryableToolError, ToolExecutionError

from arcade_notion.enums import BlockType, ObjectType
from arcade_notion.markdown_converter import NotionMarkdownConverter
from arcade_notion.tools.search import get_id_from_title
from arcade_notion.utils import (
    extract_title,
    get_headers,
    get_next_page,
    get_url,
)


@tool(requires_auth=Notion())
async def get_page_metadata(
    context: ToolContext,
    page_id: Annotated[Optional[str], "ID of the page to get metadata from"] = None,
    page_title: Annotated[Optional[str], "Title of the page to get metadata from"] = None,
) -> Annotated[dict[str, Any], "The metadata of the page"]:
    """Get the metadata of a Notion page.

    One of `page_id` or `page_title` MUST be provided, but both cannot be provided.
    """
    if not (bool(page_id) ^ bool(page_title)):
        raise RetryableToolError(
            message="Either page_id or page_title must be provided, but not both.",
            developer_message="Both page_id and page_title were provided.",
        )

    if page_title:
        response = await get_id_from_title(context, page_title, object_type=ObjectType.PAGE)["id"]
        if not response["success"]:
            raise ToolExecutionError(
                message=response["message"],
                developer_message=str(response),
            )
        page_id = response["id"]

    url = get_url("retrieve_a_page", page_id=page_id)
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return dict(response.json())


@tool(requires_auth=Notion())
async def get_page_content_by_id(
    context: ToolContext, page_id: Annotated[str, "ID of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown."""
    headers = get_headers(context)
    params = {"page_size": 100}
    converter = NotionMarkdownConverter(context)

    async with httpx.AsyncClient() as client:

        async def fetch_markdown_recursive(block_id: str, indent: str = "") -> str:
            """
            Gets the markdown content of a Notion page.

            Performs DFS while paginating through the page's block children, converting
            each block to markdown and conserving the page's indentation level.
            """
            markdown_pieces = []
            url = get_url("retrieve_block_children", block_id=block_id)
            cursor = None

            while True:
                data, has_more, cursor = await get_next_page(client, url, headers, params, cursor)
                for block in data.get("results", []):
                    block_markdown = await converter.convert_block(block)
                    if block_markdown:
                        # Append each line with indent as a separate piece
                        for line in block_markdown.rstrip("\n").splitlines():
                            markdown_pieces.append(indent + line + "\n")

                    # If the block has children and is not a child page, recurse.
                    # We don't recurse into child page content, as this would result in fetching
                    # the children pages' content, which the Notion UI does not show.
                    if (
                        block.get("has_children", False)
                        and block.get("type") != BlockType.CHILD_PAGE.value
                    ):
                        markdown_pieces.append(
                            await fetch_markdown_recursive(block["id"], indent + "    ")
                        )
                if not has_more:
                    break

            return "".join(markdown_pieces)

        # Get the title
        page_metadata = await get_page_metadata(context, page_id=page_id)
        markdown_title = f"# {extract_title(page_metadata)}\n"

        # Get the content
        markdown_content = await fetch_markdown_recursive(page_id, "")

        return markdown_title + markdown_content


@tool(requires_auth=Notion())
async def get_page_content_by_title(
    context: ToolContext, title: Annotated[str, "Title of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown."""
    response = await get_id_from_title(context, title, object_type=ObjectType.PAGE)

    if not response["success"]:
        raise ToolExecutionError(
            message=response["message"],
            developer_message=str(response),
        )

    return await get_page_content_by_id(context, response["id"])
