import asyncio
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Notion
from arcade_tdk.errors import ToolExecutionError

from arcade_notion_toolkit.block_to_markdown_converter import BlockToMarkdownConverter
from arcade_notion_toolkit.enums import BlockType, ObjectType
from arcade_notion_toolkit.markdown_to_block_converter import convert_markdown_to_blocks
from arcade_notion_toolkit.tools.search import get_object_metadata
from arcade_notion_toolkit.types import DatabaseParent, PageWithPageParentProperties, create_parent
from arcade_notion_toolkit.utils import (
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

        async def fetch_blocks(block_id: str) -> list:
            """Fetch all immediate children blocks for a given block ID, handling pagination"""
            all_blocks = []
            url = get_url("retrieve_block_children", block_id=block_id)
            cursor = None

            while True:
                data, has_more, cursor = await get_next_page(client, url, headers, params, cursor)
                all_blocks.extend(data.get("results", []))
                if not has_more:
                    break

            return all_blocks

        async def process_blocks_to_markdown(blocks: list, indent: str = "") -> str:
            """Process a list of blocks into markdown.

            If a block has children, we recurse into the children blocks.
            """
            markdown_pieces = []

            for block in blocks:
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
                    # Fetch all child blocks first
                    child_blocks = await fetch_blocks(block["id"])
                    # Then process them all at once
                    child_markdown = await process_blocks_to_markdown(child_blocks, indent + "    ")
                    markdown_pieces.append(child_markdown)

            return "".join(markdown_pieces)

        # Get the title
        page_metadata = await get_object_metadata(context, object_id=page_id)
        markdown_title = f"# {extract_title(page_metadata)}\n"

        # Get all top-level blocks
        top_level_blocks = await fetch_blocks(page_id)

        chunk_size = max(1, len(top_level_blocks) // 5)
        chunks = [
            top_level_blocks[i : i + chunk_size]
            for i in range(0, len(top_level_blocks), chunk_size)
        ]

        # Process all block content into markdown
        results = await asyncio.gather(*[process_blocks_to_markdown(chunk, "") for chunk in chunks])
        markdown_content = "".join(results)

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
    content: Annotated[str | None, "The content of the new page"] = None,
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
