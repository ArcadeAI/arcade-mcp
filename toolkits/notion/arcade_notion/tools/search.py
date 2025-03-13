from typing import Annotated, Any, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion
from arcade.sdk.errors import ToolExecutionError

from arcade_notion.enums import ObjectType, SortDirection
from arcade_notion.utils import (
    build_workspace_structure,
    get_headers,
    get_url,
    remove_none_values,
    simplify_search_result,
)


@tool(requires_auth=Notion())
async def search_by_title(
    context: ToolContext,
    query: Annotated[
        Optional[str],
        "A substring to search for within page and database titles. "
        "If not provided (default), all pages and/or databases are returned.",
    ] = None,
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
        "The maximum number of results to return. Defaults to 100. Set to -1 for no limit.",
    ] = 100,
) -> Annotated[
    dict,
    "A dictionary containing minimal information about the pages and/or databases that have "
    "titles that are the best match for the query. Does not include content or location.",
]:
    """Search for similar titles of pages, databases, or both within the user's workspace.
    Does not include content.
    """
    results = []
    current_cursor = None

    url = get_url("search_by_title")
    headers = get_headers(context)
    payload = {
        "query": query,
        "page_size": 100 if limit == -1 else min(100, limit),
        "filter": {"property": "object", "value": select.value} if select else None,
        "sort": {"direction": order_by, "timestamp": "last_edited_time"},
    }
    payload = remove_none_values(payload)

    async with httpx.AsyncClient() as client:
        while True:
            if current_cursor:
                payload["start_cursor"] = current_cursor
            elif "start_cursor" in payload:
                del payload["start_cursor"]

            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            page_results = [simplify_search_result(item) for item in data.get("results", [])]
            results.extend(page_results)

            # If a limit is set and we've reached or exceeded it, truncate the results.
            if limit is not None and len(results) >= limit:
                results = results[:limit]
                break

            if not data.get("has_more", False):
                break

            current_cursor = data.get("next_cursor")

    return {"results": results}


@tool(requires_auth=Notion())
async def get_object_metadata(
    context: ToolContext,
    object_title: Annotated[
        Optional[str], "Title of the page or database whose metadata to get"
    ] = None,
    object_id: Annotated[Optional[str], "ID of the page or database whose metadata to get"] = None,
    object_type: Annotated[
        Optional[ObjectType],
        "The type of object to match title to. Only used if `object_title` is provided. "
        "Defaults to both",
    ] = None,
) -> Annotated[dict[str, Any], "The metadata of the object"]:
    """Get the metadata of a Notion object (page or database) from its title or ID.

    One of `object_title` or `object_id` MUST be provided, but both cannot be provided.
    The title is case-insensitive and outer whitespace is ignored.

    An object's metadata includes it's id, various timestamps, properties, url, and more.
    """

    async def get_metadata_by_title(object_title: str) -> dict[str, Any]:
        candidates_response = await search_by_title(
            context,
            object_title,
            select=object_type,
            order_by=SortDirection.DESCENDING,
            limit=3,
        )

        if object_type:
            candidates: list[dict[str, Any]] = [
                page
                for page in candidates_response["results"]
                if page["object"] == object_type.value
            ]
        else:
            candidates = candidates_response["results"]

        normalized_title = object_title.lower().strip()
        error_msg = (
            f"The {object_type.value if object_type else 'object'} with "
            f"the title '{object_title}' could not be found. "
            "Either it does not exist, or it has not been shared with the integration."
        )

        if not candidates:
            raise ToolExecutionError(message=error_msg)

        for object_ in candidates:
            if object_["title"].lower().strip() == normalized_title:
                # object_ is either a page object: https://developers.notion.com/reference/page
                # or a database object: https://developers.notion.com/reference/database
                return object_

        raise ToolExecutionError(
            message=error_msg,
            developer_message=f"The closest matches are: {candidates}",
        )

    async def get_metadata_by_id(object_id: str) -> dict[str, Any]:
        url = get_url("retrieve_a_page", page_id=object_id)
        headers = get_headers(context)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ToolExecutionError(
                    message="The page or database could not be found.",
                    developer_message=f"The response was: {response.json()}",
                )

            return dict(response.json())

    if object_id is not None and object_id != "":
        return await get_metadata_by_id(object_id)
    elif object_title is not None and object_title != "":
        return await get_metadata_by_title(object_title)
    else:
        raise ToolExecutionError(
            message="Either object_title or object_id must be provided.",
        )


@tool(requires_auth=Notion())
async def get_workspace_structure(
    context: ToolContext,
) -> Annotated[dict[str, Any], "The workspace structure"]:
    """Get the workspace structure of the user's Notion workspace.
    Ideal for finding where an object is located in the workspace.
    """
    # Retrieve the complete flat list of all pages and databases.
    results = await search_by_title(context, None, limit=-1)

    # Remove database rows from results
    # They're returned from the search results because they're
    # technically child pages of the database, but since they're not displayed in the UI's
    # sidebar workspace structure, we do not include them in this tool's response.
    results["results"] = [
        item
        for item in results.get("results", [])
        if not (
            item.get("object", "") == "page"
            and item.get("parent", {}).get("type", "") == "database_id"
        )
    ]

    async with httpx.AsyncClient() as client:
        headers = get_headers(context)
        orphaned_items = []
        for item in results.get("results", []):
            # This condition will only be met for databases that are 'child_pages' of a page.
            # Notion API wraps these databases in a block object, so we need to unwrap it to
            # link the parent page to the database. Sometimes it takes multiple unwrappings
            # to get to the parent page.
            while (
                item.get("parent", {}).get("type", "") == "block_id"
                and item.get("type", "database") == "database"
            ):
                parent = item.get("parent", {})
                block_id = parent["block_id"]
                url = get_url("retrieve_a_block", block_id=block_id)
                block_response = await client.get(url, headers=headers)
                if block_response.status_code != 200:
                    # unable to attach the database to the parent page
                    orphaned_items.append(item["id"])
                    break
                block_data = block_response.json()
                if "parent" in block_data:
                    item["parent"] = block_data["parent"]

        # Drop orphaned items from results since we were unable to attach them to a parent page.
        results["results"] = [
            item for item in results.get("results", []) if item["id"] not in orphaned_items
        ]

    items = results.get("results", [])
    workspace_tree = build_workspace_structure(items)

    return workspace_tree


# {
#     "workspace": [
#         {
#             "children": [
#                 {
#                     "id": "1b47a62b-04d4-800c-a6d4-e471ae371237",
#                     "title": "NextSteps",
#                     "type": "page",
#                     "url": "https://www.notion.so/Next-Steps-1b47a62b04d4800ca6d4e471ae371237",
#                 }
#             ],
#             "id": "1b37a62b-04d4-8079-a902-ce69ed7e7240",
#             "title": "ArcadeNotes",
#             "type": "page",
#             "url": "https://www.notion.so/Arcade-Notes-1b37a62b04d48079a902ce69ed7e7240",
#         },
#         {
#             "children": [
#                 {
#                     "id": "1b47a62b-04d4-8075-bf2d-c17daca86d2c",
#                     "title": "this is my subpage ofmy todos",
#                     "type": "page",
#                     "url": "https://www.notion.so/this-is-my-subpage-of-my-todos-1b47a62b04d48075bf2dc17daca86d2c",
#                 }
#             ],
#             "id": "1ad7a62b-04d4-8063-bbb9-dce59136e08d",
#             "title": "Weekly To-doList",
#             "type": "page",
#             "url": "https://www.notion.so/Weekly-To-do-List-1ad7a62b04d48063bbb9dce59136e08d",
#         },
#         {
#             "id": "1b27a62b-04d4-80d7-b372-e18300e71052",
#             "title": "A pagehere!!",
#             "type": "page",
#             "url": "https://www.notion.so/A-page-here-1b27a62b04d480d7b372e18300e71052",
#         },
#         {
#             "children": [
#                 {
#                     "children": [
#                         {
#                             "children": [
#                                 {
#                                     "children": [
#                                         {
#                                             "id": "1b37a62b-04d4-80b5-a7a2-f0c65cb3bf4d",
#                                             "title": "Tooth",
#                                             "type": "page",
#                                             "url": "https://www.notion.so/Tooth-1b37a62b04d480b5a7a2f0c65cb3bf4d",
#                                         }
#                                     ],
#                                     "id": "1b37a62b-04d4-80f8-b3b6-e5aef644b8ec",
#                                     "title": "Teeth",
#                                     "type": "page",
#                                     "url": "https://www.notion.so/Teeth-1b37a62b04d480f8b3b6e5aef644b8ec",
#                                 }
#                             ],
#                             "id": "1b37a62b-04d4-8096-94e2-ff9db2e5c2c5",
#                             "title": "Morning",
#                             "type": "page",
#                             "url": "https://www.notion.so/Morning-1b37a62b04d4809694e2ff9db2e5c2c5",
#                         }
#                     ],
#                     "id": "1ae7a62b-04d4-80ee-b291-fa69701d74d3",
#                     "title": "03/05/2025 - Wednesday, March5",
#                     "type": "page",
#                     "url": "https://www.notion.so/03-05-2025-Wednesday-March-5-1ae7a62b04d480eeb291fa69701d74d3",
#                 },
#                 {
#                     "id": "1b37a62b-04d4-80ee-b3da-d49d1ea043ac",
#                     "title": "how to call atool",
#                     "type": "page",
#                     "url": "https://www.notion.so/how-to-call-a-tool-1b37a62b04d480eeb3dad49d1ea043ac",
#                 },
#                 {
#                     "id": "1b37a62b-04d4-8103-a179-d27bef02c4b5",
#                     "title": "Atree",
#                     "type": "page",
#                     "url": "https://www.notion.so/A-tree-1b37a62b04d48103a179d27bef02c4b5",
#                 },
#                 {
#                     "id": "1b27a62b-04d4-8024-ae1a-db8d3deab4c8",
#                     "title": "adatabase",
#                     "type": "database",
#                     "url": "https://www.notion.so/1b27a62b04d48024ae1adb8d3deab4c8",
#                 },
#                 {
#                     "id": "1ae7a62b-04d4-8064-975b-fb27a6535eac",
#                     "title": "03/03/2025 - Tuesday, March3",
#                     "type": "page",
#                     "url": "https://www.notion.so/03-03-2025-Tuesday-March-3-1ae7a62b04d48064975bfb27a6535eac",
#                 },
#                 {
#                     "id": "1ae7a62b-04d4-8058-b273-ca9f8a88a15e",
#                     "title": "03/04/2025 - Tuesday,March 4",
#                     "type": "page",
#                     "url": "https://www.notion.so/03-04-2025-Tuesday-March-4-1ae7a62b04d48058b273ca9f8a88a15e",
#                 },
#             ],
#             "id": "1ae7a62b-04d4-80cd-8f30-fe64b5354cc0",
#             "title": "Daily News byArcade.dev",
#             "type": "page",
#             "url": "https://www.notion.so/Daily-News-by-Arcade-dev-1ae7a62b04d480cd8f30fe64b5354cc0",
#         },
#         {
#             "id": "1b27a62b-04d4-807f-8c69-d9c7c2d78255",
#             "title": "sdf",
#             "type": "page",
#             "url": "https://www.notion.so/sdf-1b27a62b04d4807f8c69d9c7c2d78255",
#         },
#         {
#             "children": [
#                 {
#                     "id": "1ae7a62b-04d4-8140-926b-eb5580022c27",
#                     "title": "HabitTracker",
#                     "type": "database",
#                     "url": "https://www.notion.so/1ae7a62b04d48140926beb5580022c27",
#                 },
#                 {
#                     "id": "1ae7a62b-04d4-818a-b1cc-d9a37b8f2fbb",
#                     "title": "Tasklist",
#                     "type": "database",
#                     "url": "https://www.notion.so/1ae7a62b04d4818ab1ccd9a37b8f2fbb",
#                 },
#                 {
#                     "id": "1ae7a62b-04d4-81d6-ae33-c14127f47b39",
#                     "title": "Schedule",
#                     "type": "database",
#                     "url": "https://www.notion.so/1ae7a62b04d481d6ae33c14127f47b39",
#                 },
#             ],
#             "id": "1ae7a62b-04d4-8068-918d-d39ade9183a3",
#             "title": "D A I L Y  P L A N N ER",
#             "type": "page",
#             "url": "https://www.notion.so/D-A-I-L-Y-P-L-A-N-N-E-R-1ae7a62b04d48068918dd39ade9183a3",
#         },
#         {
#             "id": "1ae7a62b-04d4-808f-983c-f82f49250af5",
#             "title": "Table: Daily News byArcade.dev",
#             "type": "database",
#             "url": "https://www.notion.so/1ae7a62b04d4808f983cf82f49250af5",
#         },
#         {
#             "children": [
#                 {
#                     "id": "1ad7a62b-04d4-8169-92bd-d3232cae5e35",
#                     "title": "Income(Monthly)",
#                     "type": "database",
#                     "url": "https://www.notion.so/1ad7a62b04d4816992bdd3232cae5e35",
#                 }
#             ],
#             "id": "1ad7a62b-04d4-803d-855e-fa9d5adef96b",
#             "title": "MonthlyBudget",
#             "type": "page",
#             "url": "https://www.notion.so/Monthly-Budget-1ad7a62b04d4803d855efa9d5adef96b",
#         },
#     ]
# }
