from typing import Any, Optional

import httpx
from arcade.sdk import ToolContext

from arcade_notion.constants import ENDPOINTS, NOTION_API_URL
from arcade_notion.enums import BlockType


def get_url(endpoint: str, **kwargs: Any) -> str:
    """
    Constructs the full URL for a specified notion endpoint.

    Args:
        endpoint (str): The endpoint key from ENDPOINTS.
        **kwargs: Additional parameters to format the URL.

    Returns:
        str: The complete URL for the specified endpoint.
    """
    return f"{NOTION_API_URL}{ENDPOINTS[endpoint].format(**kwargs)}"


def get_headers(context: ToolContext) -> dict[str, str]:
    """
    Retrieves the headers for a given context.

    Args:
        context (ToolContext): The context containing authorization and other information.

    Returns:
        dict[str, str]: A dictionary containing the headers for the Notion API request.
    """
    return {
        "Authorization": context.get_auth_token_or_empty(),
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def remove_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Removes all keys with None values from a dictionary.

    Args:
        payload (dict[str, Any]): The dictionary to remove None values from.

    Returns:
        dict[str, Any]: A dictionary with all None values removed.
    """
    return {k: v for k, v in payload.items() if v is not None}


def extract_title(item):
    """
    Extracts a human-readable title from a page, database, or a block if possible.
    """
    properties = item.get("properties", {})
    if item["object"] == "database" and "title" in item:
        return "".join([t["plain_text"] for t in item.get("title", [])])

    if item["object"] == "page" and "title" in properties:
        return "".join([t["plain_text"] for t in properties["title"].get("title", [])])

    # For blocks (like child_page blocks).
    if item.get("object") == "block":
        block_type = item.get("type")
        if block_type == "child_page":
            return item.get("child_page", {}).get("title", "Untitled Child Page")
        # For text-based blocks, try extracting rich_text.
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
            rich_text = item.get(block_type, {}).get("rich_text", [])
            return "".join([t.get("plain_text", "") for t in rich_text]) or block_type

    return ""


def _simplify_search_result(item: dict) -> dict:
    """
    Simplifies a search result from the Notion API.

    Args:
        item (dict): The search result to simplify.

    Returns:
        dict: A simplified search result.
    """
    title = extract_title(item)
    # properties = item.get("properties", {})
    # title = ""
    # if item["object"] == "database" and "title" in item:
    #     title = "".join([t["plain_text"] for t in item.get("title", [])])
    # elif item["object"] == "page" and "title" in properties:
    #     title = "".join([t["plain_text"] for t in properties["title"].get("title", [])])

    return {
        "id": item.get("id"),
        "object": item.get("object"),
        "parent": item.get("parent"),
        "created_time": item.get("created_time"),
        "last_edited_time": item.get("last_edited_time"),
        "title": title,
        "url": item.get("url"),
        "public_url": item.get("public_url"),
    }


async def get_next_page(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    params: Optional[dict] = None,
    cursor: Optional[str] = None,
) -> tuple[dict, bool, str]:
    """
    Retrieves the next page of results from a Notion API endpoint.

    Args:
        client (httpx.AsyncClient): The HTTP client to use for the request.
        url (str): The URL of the endpoint to request.
        headers (dict): The headers to use for the request.
        params (Optional[dict]): The parameters to use for the request.
        cursor (Optional[str]): The cursor to use for the request.

    Returns:
        tuple[dict, bool, str]: A tuple containing the results, a boolean indicating if there is a
        next page, and the next cursor.
    """
    if cursor:
        params["start_cursor"] = cursor
    elif "start_cursor" in params:
        del params["start_cursor"]

    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data, data.get("has_more", False), data.get("next_cursor")


async def get_page_url(context: ToolContext, page_id: str) -> str:
    """
    Retrieves the URL of a page from the Notion API.

    Args:
        context (ToolContext): The context containing authorization and other information.
        page_id (str): The ID of the page to get the URL of.

    Returns:
        str: The URL of the page or an empty string if the page's metadata cannot be retrieved.
    """
    url = get_url("retrieve_a_page", page_id=page_id)
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return ""
        data = response.json()
        return data.get("url")


def rich_text_to_markdown(rich_text_items: list) -> str:  # noqa: C901
    """
    Convert a list of rich text items (from a Notion block) into Markdown.
    This function handles formatting annotations such as bold, italic, strikethrough,
    underline (using HTML since Markdown does not natively support it), inline code,
    text color, hyperlinks, and supports rich text types including text, mention, and equation.

    To learn more about rich text, see https://developers.notion.com/reference/rich-text

    Args:
        rich_text_items (list): A list of rich text objects.

    Returns:
        str: The markdown string.
    """
    md = ""
    for item in rich_text_items:
        annotations = item.get("annotations", {})
        type_val = item.get("type", "text")
        link = None
        text = ""

        if type_val == "text":
            # Extract text content from the 'text' field.
            content = item.get("text", {}).get("content", "")
            text = content
            # Extract hyperlink from the 'text' field; fallback to top-level href.
            link_obj = item.get("text", {}).get("link")
            link = (
                link_obj.get("url")
                if (link_obj and isinstance(link_obj, dict))
                else item.get("href")
            )

        elif type_val == "mention":
            # For mentions, use the plain text and the provided href.
            text = item.get("plain_text", "")
            link = item.get("href")

        elif type_val == "equation":
            # For inline equations, render using inline math delimiters.
            expression = item.get("equation", {}).get("expression", "")
            md += f"${expression}$"
            continue  # Skip further annotation formatting for equations.

        else:
            # Fallback for unknown types: use plain_text and href.
            text = item.get("plain_text", "")
            link = item.get("href")

        # Apply annotation formatting.
        if annotations.get("code"):
            text = f"`{text}`"
        else:
            prefix = ""
            suffix = ""
            if annotations.get("bold"):
                prefix += "**"
                suffix = "**" + suffix
            if annotations.get("italic"):
                prefix += "*"
                suffix = "*" + suffix
            if annotations.get("strikethrough"):
                prefix += "~~"
                suffix = "~~" + suffix
            text = prefix + text + suffix

            if annotations.get("underline"):
                text = f"<u>{text}</u>"

            # Apply text color if specified and not the default.
            color = annotations.get("color", "default")
            if color != "default":
                text = f'<span style="color: {color};">{text}</span>'

        # Wrap in a Markdown hyperlink if a valid URL is provided.
        if link:
            text = f"[{text}]({link})"
        md += text
    return md


def get_plaintext(block: dict) -> str:
    """
    Extracts and returns the plain text from a Notion block.
    This serves as a fallback for block types whose conversion logic hasn't been implemented yet.
    """
    block_type = block.get("type")
    # Try to obtain the content corresponding to the block type.
    content = block.get(block_type, {})
    if isinstance(content, dict):
        rich_text_items = content.get("rich_text", [])
        # Concatenate the plain text from each rich text item.
        plain_text = "".join(item.get("plain_text", "") for item in rich_text_items)
        return plain_text
    return ""


def create_bulleted_list_item(block: dict) -> str:
    rich_text_items = block.get("bulleted_list_item", {}).get("rich_text", [])
    list_text = rich_text_to_markdown(rich_text_items)
    return "- " + list_text + "  \n"


async def create_child_page(context: ToolContext, block: dict) -> str:
    page_url = await get_page_url(context, block.get("id"))
    rich_text_items = block.get("child_page", {}).get("rich_text", [])
    if rich_text_items:
        title = rich_text_to_markdown(rich_text_items)
    else:
        title = block.get("child_page", {}).get("title", "")
    return f"[{title}]({page_url})  \n"


def create_equation(block: dict) -> str:
    expression = block.get("equation", {}).get("expression", "")
    return f"$$ {expression} $$  \n"


def create_heading_1(block: dict) -> str:
    rich_text_items = block.get("heading_1", {}).get("rich_text", [])
    heading_text = rich_text_to_markdown(rich_text_items)
    return "# " + heading_text + "  \n"


def create_heading_2(block: dict) -> str:
    rich_text_items = block.get("heading_2", {}).get("rich_text", [])
    heading_text = rich_text_to_markdown(rich_text_items)
    return "## " + heading_text + "  \n"


def create_heading_3(block: dict) -> str:
    rich_text_items = block.get("heading_3", {}).get("rich_text", [])
    heading_text = rich_text_to_markdown(rich_text_items)
    return "### " + heading_text + "  \n"


def create_numbered_list_item(block: dict) -> str:
    rich_text_items = block.get("numbered_list_item", {}).get("rich_text", [])
    numbered_text = rich_text_to_markdown(rich_text_items)
    return "1. " + numbered_text + "  \n"


def create_paragraph(block: dict) -> str:
    rich_text_items = block.get("paragraph", {}).get("rich_text", [])
    paragraph_text = rich_text_to_markdown(rich_text_items)
    return paragraph_text + "  \n"


async def convert_block_to_markdown(context: ToolContext, block: dict) -> str:
    """Convert a Notion block to a markdown string.

    Args:
        context (ToolContext): The context in case we need to get the
                               URL of a page in child_page blocks.
        block (dict): The block to convert to markdown.

    Returns:
        str: The markdown string.
    """
    markdown = ""
    block_type = block.get("type")

    # block types whose conversion logic has been implemented
    # TODO: implement conversion logic for more block types
    handlers = {
        BlockType.BULLETED_LIST_ITEM.value: create_bulleted_list_item,
        BlockType.EQUATION.value: create_equation,
        BlockType.HEADING_1.value: create_heading_1,
        BlockType.HEADING_2.value: create_heading_2,
        BlockType.HEADING_3.value: create_heading_3,
        BlockType.NUMBERED_LIST_ITEM.value: create_numbered_list_item,
        BlockType.PARAGRAPH.value: create_paragraph,
    }

    if block_type in handlers:
        markdown = handlers[block_type](block)
    elif block_type == BlockType.CHILD_PAGE.value:  # child page is a special case
        markdown = await create_child_page(context, block)
    else:
        markdown = get_plaintext(block)

    return markdown


def assemble_markdown(blocks: list, indent: str = "") -> str:
    """Recursively assembles the markdown string from a list of blocks.

    Each block's markdown content is prefixed with the given indent. If a block contains
    children, then they are processed with additional indentation.
    """
    markdown_str = ""
    for block in blocks:
        block_md = block.get("markdown", "").rstrip("\n")
        if block_md:
            for line in block_md.splitlines():
                markdown_str += indent + line + "\n"
        if block.get("children"):
            markdown_str += assemble_markdown(block["children"], indent + "    ")
    return markdown_str
