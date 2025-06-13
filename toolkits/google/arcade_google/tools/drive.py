from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google
from googleapiclient.errors import HttpError

from arcade_google.doc_to_html import convert_document_to_html
from arcade_google.doc_to_markdown import convert_document_to_markdown
from arcade_google.models import DocumentFormat, OrderBy
from arcade_google.tools import get_document_by_id
from arcade_google.utils import (
    build_drive_service,
    build_file_tree,
    build_file_tree_request_params,
    build_files_list_params,
)


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
async def get_file_tree_structure(
    context: ToolContext,
    include_shared_drives: Annotated[
        bool, "Whether to include shared drives in the file tree structure. Defaults to False."
    ] = False,
    restrict_to_shared_drive_id: Annotated[
        str | None,
        "If provided, only include files from this shared drive in the file tree structure. "
        "Defaults to None, which will include files and folders from all drives.",
    ] = None,
    include_organization_domain_documents: Annotated[
        bool,
        "Whether to include documents from the organization's domain. This is applicable to admin "
        "users who have permissions to view organization-wide documents in a Google Workspace "
        "account. Defaults to False.",
    ] = False,
    order_by: Annotated[
        list[OrderBy] | None,
        "Sort order. Defaults to listing the most recently modified documents first",
    ] = None,
    limit: Annotated[
        int | None,
        "The number of files and folders to list. Defaults to None, "
        "which will list all files and folders.",
    ] = None,
) -> Annotated[
    dict,
    "A dictionary containing the file/folder tree structure in the user's Google Drive",
]:
    """
    Get the file/folder tree structure of the user's Google Drive.
    """
    service = build_drive_service(
        context.authorization.token if context.authorization and context.authorization.token else ""
    )

    keep_paginating = True
    page_token = None
    files = {}
    file_tree: dict[str, list[dict]] = {"My Drive": []}

    params = build_file_tree_request_params(
        order_by,
        page_token,
        limit,
        include_shared_drives,
        restrict_to_shared_drive_id,
        include_organization_domain_documents,
    )

    while keep_paginating:
        # Get a list of files
        results = service.files().list(**params).execute()

        # Update page token
        page_token = results.get("nextPageToken")
        params["pageToken"] = page_token
        keep_paginating = page_token is not None

        for file in results.get("files", []):
            files[file["id"]] = file

    if not files:
        return {"drives": []}

    file_tree = build_file_tree(files)

    drives = []

    for drive_id, files in file_tree.items():  # type: ignore[assignment]
        if drive_id == "My Drive":
            drive = {"name": "My Drive", "children": files}
        else:
            try:
                drive_details = service.drives().get(driveId=drive_id).execute()
                drive_name = drive_details.get("name", "Shared Drive (name unavailable)")
            except HttpError as e:
                drive_name = (
                    f"Shared Drive (name unavailable: 'HttpError {e.status_code}: {e.reason}')"
                )

            drive = {"name": drive_name, "id": drive_id, "children": files}

        drives.append(drive)

    return {"drives": drives}


# Implements: https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list
# Example `arcade chat` query: `list my 5 most recently modified documents`
# TODO: Support query with natural language. Currently, the tool expects a fully formed query
#       string as input with the syntax defined here: https://developers.google.com/drive/api/guides/search-files
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
async def search_documents(
    context: ToolContext,
    document_contains: Annotated[
        list[str] | None,
        "Keywords or phrases that must be in the document title or body. Provide a list of "
        "keywords or phrases if needed.",
    ] = None,
    document_not_contains: Annotated[
        list[str] | None,
        "Keywords or phrases that must NOT be in the document title or body. Provide a list of "
        "keywords or phrases if needed.",
    ] = None,
    search_only_in_shared_drive_id: Annotated[
        str | None,
        "The ID of the shared drive to restrict the search to. If provided, the search will only "
        "return documents from this drive. Defaults to None, which searches across all drives.",
    ] = None,
    include_shared_drives: Annotated[
        bool,
        "Whether to include documents from shared drives. Defaults to False (searches only in "
        "the user's 'My Drive').",
    ] = False,
    include_organization_domain_documents: Annotated[
        bool,
        "Whether to include documents from the organization's domain. This is applicable to admin "
        "users who have permissions to view organization-wide documents in a Google Workspace "
        "account. Defaults to False.",
    ] = False,
    order_by: Annotated[
        list[OrderBy] | None,
        "Sort order. Defaults to listing the most recently modified documents first",
    ] = None,
    limit: Annotated[int, "The number of documents to list"] = 50,
    pagination_token: Annotated[
        str | None, "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[
    dict,
    "A dictionary containing 'documents_count' (number of documents returned) and 'documents' "
    "(a list of document details including 'kind', 'mimeType', 'id', and 'name' for each document)",
]:
    """
    Searches for documents in the user's Google Drive. Excludes documents that are in the trash.
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

    params = build_files_list_params(
        mime_type="application/vnd.google-apps.document",
        document_contains=document_contains,
        document_not_contains=document_not_contains,
        page_size=page_size,
        order_by=order_by,
        pagination_token=pagination_token,
        include_shared_drives=include_shared_drives,
        search_only_in_shared_drive_id=search_only_in_shared_drive_id,
        include_organization_domain_documents=include_organization_domain_documents,
    )

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
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
async def search_and_retrieve_documents(
    context: ToolContext,
    return_format: Annotated[
        DocumentFormat,
        "The format of the document to return. Defaults to Markdown.",
    ] = DocumentFormat.MARKDOWN,
    document_contains: Annotated[
        list[str] | None,
        "Keywords or phrases that must be in the document title or body. Provide a list of "
        "keywords or phrases if needed.",
    ] = None,
    document_not_contains: Annotated[
        list[str] | None,
        "Keywords or phrases that must NOT be in the document title or body. Provide a list of "
        "keywords or phrases if needed.",
    ] = None,
    search_only_in_shared_drive_id: Annotated[
        str | None,
        "The ID of the shared drive to restrict the search to. If provided, the search will only "
        "return documents from this drive. Defaults to None, which searches across all drives.",
    ] = None,
    include_shared_drives: Annotated[
        bool,
        "Whether to include documents from shared drives. Defaults to False (searches only in "
        "the user's 'My Drive').",
    ] = False,
    include_organization_domain_documents: Annotated[
        bool,
        "Whether to include documents from the organization's domain. This is applicable to admin "
        "users who have permissions to view organization-wide documents in a Google Workspace "
        "account. Defaults to False.",
    ] = False,
    order_by: Annotated[
        list[OrderBy] | None,
        "Sort order. Defaults to listing the most recently modified documents first",
    ] = None,
    limit: Annotated[int, "The number of documents to list"] = 50,
    pagination_token: Annotated[
        str | None, "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[
    dict,
    "A dictionary containing 'documents_count' (number of documents returned) and 'documents' "
    "(a list of documents with their content).",
]:
    """
    Searches for documents in the user's Google Drive and returns a list of documents (with text
    content) matching the search criteria. Excludes documents that are in the trash.

    Note: use this tool only when the user prompt requires the documents' content. If the user only
    needs a list of documents, use the `search_documents` tool instead.
    """
    response = await search_documents(
        context=context,
        document_contains=document_contains,
        document_not_contains=document_not_contains,
        search_only_in_shared_drive_id=search_only_in_shared_drive_id,
        include_shared_drives=include_shared_drives,
        include_organization_domain_documents=include_organization_domain_documents,
        order_by=order_by,
        limit=limit,
        pagination_token=pagination_token,
    )

    documents = []

    for item in response["documents"]:
        document = await get_document_by_id(context, document_id=item["id"])

        if return_format == DocumentFormat.MARKDOWN:
            document = convert_document_to_markdown(document)
        elif return_format == DocumentFormat.HTML:
            document = convert_document_to_html(document)

        documents.append(document)

    return {"documents_count": len(documents), "documents": documents}
