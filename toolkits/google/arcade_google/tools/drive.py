from typing import Annotated, Any, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google

from arcade_google.doc_to_markdown import convert_document_to_markdown
from arcade_google.tools.docs import get_document_by_id
from arcade_google.utils import build_drive_service, build_files_list_query, remove_none_values

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
    document_contains: Annotated[
        Optional[list[str]],
        "Keywords or phrases that must be in the document title or body. Provide a list of "
        "phrases if needed",
    ] = None,
    document_not_contains: Annotated[
        Optional[list[str]],
        "Keywords or phrases that must NOT be in the document title or body. Provide a list of "
        "phrases if needed",
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

    query = build_files_list_query(
        document_contains=document_contains,
        document_not_contains=document_not_contains,
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


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def search_and_retrieve_documents_in_markdown(
    context: ToolContext,
    corpora: Annotated[Corpora, "The source of files to list"] = Corpora.USER,
    document_contains: Annotated[
        Optional[list[str]],
        "Keywords or phrases that must be in the document title or body. Provide a list of "
        "phrases if needed",
    ] = None,
    document_not_contains: Annotated[
        Optional[list[str]],
        "Keywords or phrases that must NOT be in the document title or body. Provide a list of "
        "phrases if needed",
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
    Provides a list of documents (with content) matching the search criteria.

    Note: use this tool only when the user prompt requires the documents' content. If the user only
    needs a list of documents, use the `list_documents` tool instead.
    """
    response = await list_documents(
        context=context,
        corpora=corpora,
        document_contains=document_contains,
        document_not_contains=document_not_contains,
        order_by=order_by,
        supports_all_drives=supports_all_drives,
        limit=limit,
        pagination_token=pagination_token,
    )

    documents = []

    for item in response["documents"]:
        documents.append(await get_document_by_id(context, document_id=item["id"]))

    return {
        "documents_count": len(documents),
        "documents": [convert_document_to_markdown(doc) for doc in documents],
    }
