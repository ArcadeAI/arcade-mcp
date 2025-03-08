from typing import Annotated

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion

from arcade_notion.enums import SortDirection
from arcade_notion.tools.search import search_by_title
from arcade_notion.utils import get_headers, get_url


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
) -> Annotated[dict, "The content of the page"]:
    """Get the content of a Notion page."""
    url = get_url("retrieve_block_children", block_id=page_id)
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return dict(response.json())


# @tool(requires_auth=Notion())
# async def get_page_content_by_title(
#     context: ToolContext, title: Annotated[str, "Title of the page to get content from"]
# ) -> Annotated[dict, "The content of the page"]:
#     """Get the content of a Notion page."""
#     url = get_url("retrieve_a_page")
#     headers = get_headers(context)


"""
{
    "block": {},
    "has_more": False,
    "next_cursor": None,
    "object": "list",
    "request_id": "85f9afa0-fbc7-4c01-bb80-5b11671626f0",
    "results": [
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:33:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-8065-b9a6-fd392810fb3f",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:33:00.000Z",
            "object": "block",
            "paragraph": {"color": "default", "rich_text": []},
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:33:00.000Z",
            "has_children": False,
            "heading_1": {
                "color": "default",
                "is_toggleable": False,
                "rich_text": [
                    {
                        "annotations": {
                            "bold": False,
                            "code": False,
                            "color": "default",
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "href": None,
                        "plain_text": "Schedule:",
                        "text": {"content": "Schedule:", "link": None},
                        "type": "text",
                    }
                ],
            },
            "id": "1ae7a62b-04d4-8021-8c03-f22c04da776a",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:33:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "heading_1",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:33:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-8071-b97e-f819beab006b",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:33:00.000Z",
            "object": "block",
            "paragraph": {
                "color": "default",
                "rich_text": [
                    {
                        "annotations": {
                            "bold": False,
                            "code": False,
                            "color": "default",
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "href": None,
                        "plain_text": "Every day at 9am PT",
                        "text": {"content": "Every day at 9am PT", "link": None},
                        "type": "text",
                    }
                ],
            },
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
        {
            "archived": False,
            "bulleted_list_item": {
                "color": "default",
                "rich_text": [
                    {
                        "annotations": {
                            "bold": False,
                            "code": False,
                            "color": "default",
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "href": None,
                        "plain_text": "This is a bullet point",
                        "text": {"content": "This is a bullet point", "link": None},
                        "type": "text",
                    }
                ],
            },
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-08T02:01:00.000Z",
            "has_children": True,
            "id": "1b07a62b-04d4-80d6-b0b0-e71f231ad589",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-08T02:02:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "bulleted_list_item",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:29:00.000Z",
            "has_children": False,
            "heading_1": {
                "color": "default",
                "is_toggleable": False,
                "rich_text": [
                    {
                        "annotations": {
                            "bold": False,
                            "code": False,
                            "color": "default",
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "href": None,
                        "plain_text": "Sources:",
                        "text": {"content": "Sources:", "link": None},
                        "type": "text",
                    }
                ],
            },
            "id": "1ae7a62b-04d4-80a1-ae50-d6bee4d60a3e",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:29:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "heading_1",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:29:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-805e-aa6f-d2f0e631faae",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:29:00.000Z",
            "object": "block",
            "paragraph": {"color": "default", "rich_text": []},
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:29:00.000Z",
            "has_children": False,
            "heading_1": {
                "color": "default",
                "is_toggleable": False,
                "rich_text": [
                    {
                        "annotations": {
                            "bold": False,
                            "code": False,
                            "color": "default",
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "href": None,
                        "plain_text": "Subjects:",
                        "text": {"content": "Subjects:", "link": None},
                        "type": "text",
                    }
                ],
            },
            "id": "1ae7a62b-04d4-80f0-9844-ec9b65a202b3",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:29:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "heading_1",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:29:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-808d-b6ce-fb1fb90ad42d",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:29:00.000Z",
            "object": "block",
            "paragraph": {"color": "default", "rich_text": []},
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:29:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-80fc-8ec5-d50478849f59",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:29:00.000Z",
            "object": "block",
            "paragraph": {"color": "default", "rich_text": []},
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
        {
            "archived": False,
            "child_page": {"title": "03/05/2025 - Wednesday, March 5"},
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:26:00.000Z",
            "has_children": True,
            "id": "1ae7a62b-04d4-80ee-b291-fa69701d74d3",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-08T01:49:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "child_page",
        },
        {
            "archived": False,
            "child_page": {"title": "03/04/2025 - Tuesday, March 4"},
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:27:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-8058-b273-ca9f8a88a15e",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:28:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "child_page",
        },
        {
            "archived": False,
            "child_page": {"title": "03/03/2025 - Tuesday, March 3"},
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:28:00.000Z",
            "has_children": True,
            "id": "1ae7a62b-04d4-8064-975b-fb27a6535eac",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:28:00.000Z",
            "object": "block",
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "child_page",
        },
        {
            "archived": False,
            "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "created_time": "2025-03-06T22:34:00.000Z",
            "has_children": False,
            "id": "1ae7a62b-04d4-803d-9971-e3e6f459e375",
            "in_trash": False,
            "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
            "last_edited_time": "2025-03-06T22:34:00.000Z",
            "object": "block",
            "paragraph": {"color": "default", "rich_text": []},
            "parent": {"page_id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0", "type": "page_id"},
            "type": "paragraph",
        },
    ],
    "type": "block",
}
"""
