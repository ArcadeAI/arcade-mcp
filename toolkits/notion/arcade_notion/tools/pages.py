from typing import Annotated, Any, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion
from arcade.sdk.errors import ToolExecutionError

from arcade_notion.block_to_markdown_converter import BlockToMarkdownConverter
from arcade_notion.enums import BlockType, ObjectType
from arcade_notion.markdown_to_block_converter import convert_markdown_to_blocks
from arcade_notion.tools.search import get_object_metadata
from arcade_notion.types import DatabaseParent, PageWithPageParentProperties, create_parent
from arcade_notion.utils import (
    extract_title,
    get_headers,
    get_next_page,
    get_url,
)


@tool(requires_auth=Notion())
async def get_page_content_by_id(
    context: ToolContext, page_id: Annotated[str, "ID of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown with the page's ID"""
    headers = get_headers(context)
    params = {"page_size": 100}
    converter = BlockToMarkdownConverter(context)

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
        page_metadata = await get_object_metadata(context, object_id=page_id)
        markdown_title = f"# {extract_title(page_metadata)}\n"

        # Get the content
        markdown_content = await fetch_markdown_recursive(page_id, "")

        return markdown_title + markdown_content


@tool(requires_auth=Notion())
async def get_page_content_by_title(
    context: ToolContext, title: Annotated[str, "Title of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown with the page's title"""
    page_metadata = await get_object_metadata(
        context, object_title=title, object_type=ObjectType.PAGE
    )

    page_content: str = await get_page_content_by_id(context, page_metadata["id"])
    return page_content


@tool(requires_auth=Notion())
async def create_page(
    context: ToolContext,
    parent_title: Annotated[
        str,
        "Title of an existing page/database within which the new page will be created. ",
    ],
    title: Annotated[str, "Title of the new page"],
    content: Annotated[Optional[str], "The content of the new page"] = None,
) -> Annotated[str, "The ID of the new page"]:
    """Create a new Notion page by the title of the new page's parent."""
    # Notion API does not support creating a page at the root of the workspace... sigh
    parent_metadata = await get_object_metadata(
        context,
        parent_title,
        object_type=ObjectType.PAGE,
    )
    parent_type = parent_metadata["object"] + "_id"
    parent = create_parent({"type": parent_type, parent_type: parent_metadata["id"]})

    properties: dict[str, Any] = {}
    if isinstance(parent, DatabaseParent):
        # TODO: Support creating a page within a database
        raise ToolExecutionError(
            message="Creating a page within a database is not supported.",
            developer_message="Database is not supported as a parent of a new page at this time.",
        )
    else:
        properties = PageWithPageParentProperties(title=title).to_dict()

    children = convert_markdown_to_blocks(content) if content else None

    body = {
        "parent": parent.to_dict(),
        "properties": properties,
        "children": children,
    }

    url = get_url("create_a_page")
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return f"Successfully created page with ID: {response.json()['id']}"
