from typing import Annotated, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion

from arcade_notion.enums import ObjectType, SortDirection
from arcade_notion.utils import get_headers, get_url, remove_none_values


@tool(requires_auth=Notion())
async def search_by_title(
    context: ToolContext,
    title_includes: Annotated[
        Optional[str], "The text to compare against page and database titles."
    ] = "",
    select: Annotated[
        Optional[ObjectType],
        "Limit the results to either only pages or only databases. Defaults to both.",
    ] = None,
    order_by: Annotated[
        SortDirection,
        "The direction to sort search results by last edited time. Defaults to 'descending'.",
    ] = SortDirection.DESCENDING,
    limit: Annotated[
        int,
        "The maximum number of results to return. Defaults to 100.",
    ] = 100,
) -> Annotated[dict, "A dictionary containing the aggregated search results."]:
    """
    Search for Notion pages, databases, or both by title.
    """
    page_size = min(100, limit)
    results = []

    url = get_url("search_by_title")
    headers = get_headers(context)
    payload = {
        "query": title_includes,
        "page_size": page_size,
        "filter": {"property": "object", "value": select.value} if select else None,
        "sort": {"direction": order_by, "timestamp": "last_edited_time"},
    }
    payload = remove_none_values(payload)

    current_cursor = None

    async with httpx.AsyncClient() as client:
        while True:
            if current_cursor:
                payload["start_cursor"] = current_cursor
            elif "start_cursor" in payload:
                del payload["start_cursor"]

            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results.extend(data.get("results", []))

            if len(results) >= limit:
                results = results[:limit]
                break

            if not data.get("has_more", False):
                break

            current_cursor = data.get("next_cursor")

    def simplify_result(item: dict) -> dict:
        properties = item.get("properties", {})
        title = ""
        if properties.get("object") == "database":
            title = properties["title"][0]["plain_text"]
        elif properties.get("object") == "page":
            title = (
                item.get("properties", {})
                .get("title", {})
                .get("title", [{}])[0]
                .get("plain_text", "")
            )

        return {
            "id": item.get("id"),
            "object": item.get("object"),
            "parent": item.get("parent"),
            # "properties": item.get(
            #     "properties"
            # ),  # this essentially contains the database schema
            "created_time": item.get("created_time"),
            "last_edited_time": item.get("last_edited_time"),
            "title": title,
            "url": item.get("url"),
            "public_url": item.get("public_url"),
        }

    simple_results = [simplify_result(item) for item in results]
    return {"results": simple_results}


# a = {
#     "results": [
#         {
#             "created_time": "2025-03-06T22:40:00.000Z",
#             "id": "1ae7a62b-04d4-808f-983c-f82f49250af5",
#             "last_edited_time": "2025-03-07T01:45:00.000Z",
#             "object": "database",
#             "parent": {"type": "workspace", "workspace": true},
#             "public_url": null,
#             "title": "",
#             "url": "https://www.notion.so/1ae7a62b04d4808f983cf82f49250af5",
#         }
#     ]
# }

# # Example full response for a database
# a = {
#     "results": [
#         {
#             "archived": false,
#             "cover": {
#                 "external": {"url": "https://www.notion.so/images/page-cover/gradients_10.jpg"},
#                 "type": "external",
#             },
#             "created_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
#             "created_time": "2025-03-06T22:40:00.000Z",
#             "description": [],
#             "icon": null,
#             "id": "1ae7a62b-04d4-808f-983c-f82f49250af5",
#             "in_trash": false,
#             "is_inline": false,
#             "last_edited_by": {"id": "1add872b-594c-812b-a3bc-0002ba39f531", "object": "user"},
#             "last_edited_time": "2025-03-07T01:45:00.000Z",
#             "object": "database",
#             "parent": {"type": "workspace", "workspace": true},
#             "properties": {
#                 "Date": {"date": {}, "id": "__%3CC", "name": "Date", "type": "date"},
#                 "Read": {
#                     "id": "RB%7BM",
#                     "name": "Read",
#                     "status": {
#                         "groups": [
#                             {
#                                 "color": "gray",
#                                 "id": "38f95373-73c3-4916-8553-a03d6fce13e4",
#                                 "name": "To-do",
#                                 "option_ids": ["735f341b-ea7b-4b20-ad80-4f518093041a"],
#                             },
#                             {
#                                 "color": "blue",
#                                 "id": "00ade36d-829d-4c11-9015-fef165bff77c",
#                                 "name": "In progress",
#                                 "option_ids": ["a060f279-d01e-45c5-824e-cd0494c51dd3"],
#                             },
#                             {
#                                 "color": "green",
#                                 "id": "41726a26-29cc-497e-baa8-520c8ac501b7",
#                                 "name": "Complete",
#                                 "option_ids": ["ed4449fc-43f8-44a6-9691-7019784f7da6"],
#                             },
#                         ],
#                         "options": [
#                             {
#                                 "color": "default",
#                                 "description": null,
#                                 "id": "735f341b-ea7b-4b20-ad80-4f518093041a",
#                                 "name": "Not started",
#                             },
#                             {
#                                 "color": "blue",
#                                 "description": null,
#                                 "id": "a060f279-d01e-45c5-824e-cd0494c51dd3",
#                                 "name": "In progress",
#                             },
#                             {
#                                 "color": "green",
#                                 "description": null,
#                                 "id": "ed4449fc-43f8-44a6-9691-7019784f7da6",
#                                 "name": "Done",
#                             },
#                         ],
#                     },
#                     "type": "status",
#                 },
#                 "Summary": {
#                     "id": "rn~%3A",
#                     "name": "Summary",
#                     "rich_text": {},
#                     "type": "rich_text",
#                 },
#                 "Title": {"id": "title", "name": "Title", "title": {}, "type": "title"},
#             },
#             "public_url": null,
#             "title": [
#                 {
#                     "annotations": {
#                         "bold": false,
#                         "code": false,
#                         "color": "default",
#                         "italic": false,
#                         "strikethrough": false,
#                         "underline": false,
#                     },
#                     "href": null,
#                     "plain_text": "Table: Daily News by Arcade.dev",
#                     "text": {"content": "Table: Daily News by Arcade.dev", "link": null},
#                     "type": "text",
#                 }
#             ],
#             "url": "https://www.notion.so/1ae7a62b04d4808f983cf82f49250af5",
#         }
#     ]
# }
