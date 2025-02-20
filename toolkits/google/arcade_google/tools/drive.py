from typing import Annotated, Any, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google

from arcade_google.utils import build_drive_service, build_file_query, remove_none_values

from ..models import Corpora, OrderBy


# Implements: https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list
# Example `arcade chat` query: `list my 5 most recently modified documents`
# TODO: Support query with natural language. Currently, the tool expects a fully formed query
#       string as input with the syntax defined here: https://developers.google.com/drive/api/guides/search-files
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def list_documents(
    context: ToolContext,
    corpora: Annotated[Corpora, "The source of files to list"] = Corpora.USER,
    name_contains: Annotated[
        Optional[list[str]], "Keywords or phrases that must be in the document name"
    ] = None,
    name_not_contains: Annotated[
        Optional[list[str]], "Keywords or phrases that must NOT be in the document name"
    ] = None,
    content_contains: Annotated[
        Optional[list[str]], "Keywords or phrases that must be in the document content"
    ] = None,
    content_not_contains: Annotated[
        Optional[list[str]], "Keywords or phrases that must NOT be in the document content"
    ] = None,
    order_by: Annotated[
        Optional[list[OrderBy]],
        "Sort order. Defaults to listing the most recently modified documents first",
    ] = None,
    supports_all_drives: Annotated[
        bool,
        "Whether the requesting application supports both My Drives and shared drives",
    ] = False,
    limit: Annotated[int, "The number of documents to list"] = 50,
    pagination_token: Annotated[
        Optional[str], "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[
    dict,
    "A dictionary containing 'documents_count' (number of documents returned) and 'documents' "
    "(a list of document details including 'kind', 'mimeType', 'id', and 'name' for each document)",
]:
    """
    List documents in the user's Google Drive. Excludes documents that are in the trash.
    """
    if order_by is None:
        order_by = [OrderBy.MODIFIED_TIME_DESC]
    elif isinstance(order_by, OrderBy):
        order_by = [order_by]

    page_size = min(10, limit)
    files: list[dict[str, Any]] = []

    service = build_drive_service(
        context.authorization.token if context.authorization and context.authorization.token else ""
    )

    query = build_file_query(
        name_contains=name_contains,
        name_not_contains=name_not_contains,
        content_contains=content_contains,
        content_not_contains=content_not_contains,
    )

    params = {
        "q": query,
        "pageSize": page_size,
        "orderBy": ",".join([item.value for item in order_by]),
        "corpora": corpora.value,
        "supportsAllDrives": supports_all_drives,
        "pageToken": pagination_token,
    }
    params = remove_none_values(params)

    while len(files) < limit:
        if pagination_token:
            params["pageToken"] = pagination_token
        else:
            params.pop("pageToken", None)

        results = service.files().list(**params).execute()
        batch = results.get("files", [])
        files.extend(batch[: limit - len(files)])

        pagination_token = results.get("nextPageToken")
        if not pagination_token or len(batch) < page_size:
            break

    return {"documents_count": len(files), "documents": files}


# @tool(
#     requires_auth=Google(
#         scopes=["https://www.googleapis.com/auth/drive.file"],
#     )
# )
# async def search_and_retrieve_documents():
