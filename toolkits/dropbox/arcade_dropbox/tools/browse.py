from typing import Annotated, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Dropbox
from arcade_tdk.errors import ToolExecutionError

from arcade_dropbox.constants import Endpoint, ItemCategory
from arcade_dropbox.exceptions import DropboxApiError
from arcade_dropbox.utils import (
    build_dropbox_json,
    clean_dropbox_entries,
    parse_dropbox_path,
    send_dropbox_request,
)


@tool(
    requires_auth=Dropbox(
        scopes=["files.metadata.read"],
    )
)
async def list_items_in_folder(
    context: ToolContext,
    folder_path: Annotated[
        str,
        "The path to the folder to list the contents of. E.g. '/AcmeInc/Reports'. "
        "Defaults to an empty string (list items in the Dropbox root folder).",
    ] = "",
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 100. Maximum allowed is 2000.",
    ] = 100,
    cursor: Annotated[
        Optional[str],
        "The cursor token for the next page of results. "
        "Defaults to None (returns the first page of results).",
    ] = None,
) -> Annotated[
    dict, "Dictionary containing the list of files and folders in the specified folder path"
]:
    """Provides a dictionary containing the list of items in the specified folder path.

    Note 1: when paginating, it is not necessary to provide any other argument besides the cursor.
    Note 2: when paginating, any given item (file or folder) may be returned in multiple pages.
    """
    limit = min(limit, 2000)

    try:
        result = await send_dropbox_request(
            context.get_auth_token_or_empty(),
            endpoint=Endpoint.LIST_FOLDER,
            path=parse_dropbox_path(folder_path),
            limit=limit,
            cursor=cursor,
        )
    except DropboxApiError as api_error:
        return {"error": api_error.message}

    return {
        "items": clean_dropbox_entries(result["entries"]),
        "cursor": result.get("cursor"),
        "has_more": result.get("has_more", False),
    }


@tool(
    requires_auth=Dropbox(
        scopes=["files.metadata.read"],
    )
)
async def search_files_and_folders(
    context: ToolContext,
    keywords: Annotated[
        str,
        "The keywords to search for. E.g. 'quarterly report'. "
        "Maximum length allowed by the Dropbox API is 1000 characters. ",
    ],
    search_in_folder_path: Annotated[
        Optional[str],
        "Restricts the search to the specified folder path. E.g. '/AcmeInc/Reports'. "
        "Defaults to None (search in the entire Dropbox).",
    ] = None,
    filter_by_category: Annotated[
        Optional[list[ItemCategory]],
        "Restricts the search to the specified category(ies) of items. "
        "Provide None, one or multiple, if needed. Defaults to None (returns all categories).",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 100. Maximum allowed is 1000.",
    ] = 100,
    cursor: Annotated[
        Optional[str],
        "The cursor token for the next page of results. Defaults to None (first page of results).",
    ] = None,
) -> Annotated[dict, "List of items in the specified folder path matching the search criteria"]:
    """Returns a list of items in the specified folder path matching the search criteria.

    Note 1: the Dropbox API will return up to 10,000 (ten thousand) items cumulatively across
    multiple pagination requests using the cursor token.
    Note 2: when paginating, it is not necessary to provide any other argument besides the cursor.
    Note 3: when paginating, any given item (file or folder) may be returned in multiple pages.
    """
    if len(keywords) > 1000:
        raise ToolExecutionError(
            "The keywords argument must be a string with up to 1000 characters."
        )

    limit = min(limit, 1000)

    filter_by_category = filter_by_category or []

    options = build_dropbox_json(
        file_status="active",
        filename_only=False,
        path=parse_dropbox_path(search_in_folder_path),
        max_results=limit,
        file_categories=[category.value for category in filter_by_category],
    )

    try:
        result = await send_dropbox_request(
            context.get_auth_token_or_empty(),
            endpoint=Endpoint.SEARCH_FILES,
            query=keywords,
            options=options,
            cursor=cursor,
        )
    except DropboxApiError as api_error:
        return {"error": api_error.message}

    return {
        "items": clean_dropbox_entries([
            match["metadata"]["metadata"] for match in result["matches"]
        ]),
        "cursor": result.get("cursor"),
        "has_more": result.get("has_more", False),
    }
