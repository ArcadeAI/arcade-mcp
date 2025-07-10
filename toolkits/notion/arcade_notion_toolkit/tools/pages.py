from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Notion
from arcade_tdk.errors import ToolExecutionError

from arcade_notion_toolkit.block_to_structured_converter import BlockToStructuredConverter
from arcade_notion_toolkit.enums import ObjectType
from arcade_notion_toolkit.markdown_to_block_converter import convert_markdown_to_blocks
from arcade_notion_toolkit.tools.search import get_object_metadata
from arcade_notion_toolkit.types import DatabaseParent, PageWithPageParentProperties, create_parent
from arcade_notion_toolkit.utils import (
    extract_title,
    get_headers,
    get_next_page,
    get_page_url,
    get_url,
    is_page_id,
)


@tool(requires_auth=Notion())
async def get_page_content_by_id(
    context: ToolContext, page_id: Annotated[str, "ID of the page to get content from"]
) -> Annotated[dict[str, Any], "The structured content of the page with block IDs and hierarchy"]:
    """Get the content of a Notion page as a structured dictionary with the page's ID.

    DO NOT CALL THIS TOOL IF YOU ALREADY HAVE THE PAGE CONTENT IN YOUR HISTORY.
    """
    headers = get_headers(context)
    params = {"page_size": 100}
    structured_converter = BlockToStructuredConverter(context)

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

        page_metadata = await get_object_metadata(context, object_id=page_id)
        title = extract_title(page_metadata)

        # Get all top-level blocks
        top_level_blocks = await fetch_blocks(page_id)

        structured_blocks = await structured_converter.convert_blocks_to_structured(
            top_level_blocks, fetch_blocks
        )

        return {"page_id": page_id, "title": title, "blocks": structured_blocks}


@tool(requires_auth=Notion())
async def get_page_content_by_title(
    context: ToolContext, title: Annotated[str, "Title of the page to get content from"]
) -> Annotated[dict[str, Any], "The structured content of the page with block IDs and hierarchy"]:
    """Get the content of a Notion page as a structured dictionary with the page's title.

    DO NOT CALL THIS TOOL IF YOU ALREADY HAVE THE PAGE CONTENT IN YOUR HISTORY.
    """
    page_metadata = await get_object_metadata(
        context, object_title=title, object_type=ObjectType.PAGE
    )

    page_content = await get_page_content_by_id(context, page_metadata["id"])
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

    children = convert_markdown_to_blocks(content) if content else []

    # Split children into chunks of 100 due to Notion API limit
    chunk_size = 100
    first_chunk = children[:chunk_size] if children else []
    remaining_chunks = [
        children[i : i + chunk_size] for i in range(chunk_size, len(children), chunk_size)
    ]

    body = {
        "parent": parent.to_dict(),
        "properties": properties,
        "children": first_chunk,
    }

    url = get_url("create_a_page")
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        page_id = response.json()["id"]

        # Append remaining chunks if any
        if remaining_chunks:
            append_url = get_url("append_block_children", block_id=page_id)
            for chunk in remaining_chunks:
                chunk_body = {"children": chunk}
                append_response = await client.patch(append_url, headers=headers, json=chunk_body)
                append_response.raise_for_status()

        return f"Successfully created page with ID: {page_id}"


@tool(requires_auth=Notion())
async def append_content_to_end_of_page(
    context: ToolContext,
    page_id_or_title: Annotated[str, "ID or title of the page to append content to"],
    content: Annotated[str, "The markdown content to append to the end of the page"],
) -> Annotated[dict[str, str], "A dictionary containing a success message and the URL to the page"]:
    """Append markdown content to the end of a Notion page by its ID or title"""
    # Determine if the provided identifier is an ID or a title
    page_id = page_id_or_title
    if not is_page_id(page_id_or_title):
        page_metadata = await get_object_metadata(
            context,
            object_title=page_id_or_title,
            object_type=ObjectType.PAGE,
        )
        page_id = page_metadata["id"]

    headers = get_headers(context)
    # the Notion API endpoint conveniently also accepts page ID for the block_id path parameter
    url = get_url("append_block_children", block_id=page_id)

    children = convert_markdown_to_blocks(content)

    # Split children into chunks of 100 due to Notion API limit
    chunk_size = 100
    async with httpx.AsyncClient() as client:
        for i in range(0, len(children), chunk_size):
            chunk = children[i : i + chunk_size]
            body = {"children": chunk}

            response = await client.patch(url, headers=headers, json=body)
            response.raise_for_status()

        page_url = await get_page_url(context, page_id)

        return {
            "message": f"Successfully appended content to page with ID: {page_id}",
            "url": page_url,
        }


@tool(requires_auth=Notion())
async def edit_block(
    context: ToolContext,
    block_id: Annotated[str, "The ID of the block to edit (extracted from HTML comment metadata)"],
    new_content: Annotated[str, "The new markdown content for the block"],
) -> Annotated[dict[str, str], "A dictionary containing a success message and the block ID"]:
    """Edit a specific block in a Notion page by its block ID.

    If you have the block ID in your conversation history, then there is no need to get the page content again.

    The 'block type' of the block to update cannot be changed. For example, a list item
    cannot be updated to a heading. An error will be raised if the provided block type differs
    from the original block type.

    The block ID should be extracted from the HTML comment metadata (<!-- notion-block-id: ... -->) in the page content.
    The new content will replace the entire content of the block.
    """  # noqa: E501
    headers = get_headers(context)
    update_url = get_url("update_a_block", block_id=block_id)
    retrieve_url = get_url("retrieve_a_block", block_id=block_id)

    async with httpx.AsyncClient() as client:
        # Determine the original block type
        retrieve_response = await client.get(retrieve_url, headers=headers)
        retrieve_response.raise_for_status()
        block_data = retrieve_response.json()
        original_block_type = block_data.get("type")

        # TODO: Can this even happen?
        if not original_block_type:
            raise ToolExecutionError(
                message="Could not determine block type",
                developer_message=f"Block {block_id} returned no type information",
            )

        updated_blocks = convert_markdown_to_blocks(new_content)

        # TODO: Is this possible? If it is then I should probably raise an error.
        if not updated_blocks:
            # If no blocks were created, create an empty paragraph
            updated_blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}}]

        updated_block = updated_blocks[0]

        # Build the update payload based on the original block type
        update_payload = {"type": original_block_type}

        # Map the content from the converted block to the original block type
        # If the converted type matches the original, use it directly
        if updated_block["type"] == original_block_type:
            update_payload[original_block_type] = updated_block[updated_block["type"]]
        else:  # TODO: We might just be able to skip this if we want to throw error instead
            # Otherwise, we need to extract the rich_text and apply it to the original type
            # Most text-based blocks have a similar structure with rich_text
            converted_type = updated_block["type"]
            if converted_type in updated_block and "rich_text" in updated_block[converted_type]:
                rich_text = updated_block[converted_type]["rich_text"]

                # Apply the rich_text to the original block type
                if original_block_type in [
                    "paragraph",
                    "heading_1",
                    "heading_2",
                    "heading_3",
                    "bulleted_list_item",
                    "numbered_list_item",
                    "quote",
                ]:
                    update_payload[original_block_type] = {"rich_text": rich_text}
                else:
                    # For other block types, attempt to update with rich_text if applicable
                    # This is a best-effort approach
                    update_payload[original_block_type] = {"rich_text": rich_text}
            else:
                # If we can't extract rich_text, raise an error
                raise ToolExecutionError(
                    message=f"Cannot convert content to block type '{original_block_type}'",
                    developer_message=f"Unable to map converted block type '{converted_type}' to original type '{original_block_type}'",  # noqa: E501
                )

        # Send the update request
        response = await client.patch(update_url, headers=headers, json=update_payload)
        response.raise_for_status()

        return {"message": f"Successfully updated block with ID: {block_id}", "block_id": block_id}
