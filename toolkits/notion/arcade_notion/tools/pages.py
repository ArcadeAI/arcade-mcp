from typing import Annotated

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion

from arcade_notion.enums import BlockType, SortDirection
from arcade_notion.tools.search import search_by_title
from arcade_notion.utils import (
    convert_block_to_markdown,
    get_headers,
    get_next_page,
    get_url,
)


@tool(requires_auth=Notion())
async def get_id_from_title(
    context: ToolContext, title: Annotated[str, "Title of the page to find"]
) -> Annotated[str, "Success message with page ID or error message"]:
    """Get the ID of a Notion object (page or database) by searching for its title."""
    candidates = await search_by_title(context, title, order_by=SortDirection.DESCENDING, limit=3)
    candidates = [{"id": page["id"], "title": page["title"]} for page in candidates["results"]]
    if not candidates:
        return {"success": False, "message": "The page you are looking for does not exist."}

    for page in candidates:
        if page["title"].lower() == title.lower():
            return {
                "success": True,
                "id": page["id"],
                "message": f"The ID for '{title}' is {page['id']}",
            }

    return {
        "success": False,
        "message": (
            f"There is no object with the title '{title}'. The closest matches are: {candidates}"
        ),
    }


@tool(requires_auth=Notion())
async def get_page_content_by_id(
    context: ToolContext, page_id: Annotated[str, "ID of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown."""
    headers = get_headers(context)
    params = {"page_size": 100}

    async with httpx.AsyncClient() as client:

        async def fetch_markdown_recursive(block_id: str, indent: str = "") -> str:
            markdown_pieces = []
            url = get_url("retrieve_block_children", block_id=block_id)
            cursor = None

            while True:
                data, has_more, cursor = await get_next_page(client, url, headers, params, cursor)
                for block in data.get("results", []):
                    block_markdown = await convert_block_to_markdown(context, block)
                    if block_markdown:
                        # Append each line with indent as a separate piece
                        for line in block_markdown.rstrip("\n").splitlines():
                            markdown_pieces.append(indent + line + "\n")

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

        markdown_content = await fetch_markdown_recursive(page_id, "")
        return markdown_content


@tool(requires_auth=Notion())
async def get_page_content_by_title(
    context: ToolContext, title: Annotated[str, "Title of the page to get content from"]
) -> Annotated[str, "The markdown content of the page"]:
    """Get the content of a Notion page as markdown."""
    id_ = await get_id_from_title(context, title)
    if not id_["success"]:
        return {"success": False, "message": id_["message"]}

    return await get_page_content_by_id(context, id_["id"])
