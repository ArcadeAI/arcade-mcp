from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_drive_service, remove_none_values

from .models import Corpora, OrderBy


# Implements: https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list
# Example `arcade chat` query: `list my 5 most recently modified documents`
# TODO: Support query with natural language. Currently, the tool expects a fully formed query string as input with the syntax defined here: https://developers.google.com/drive/api/guides/search-files
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def list_documents(
    context: ToolContext,
    corpora: Annotated[Optional[Corpora], "The source of files to list"] = Corpora.USER,
    title_keywords: Annotated[
        Optional[list[str]], "Keywords or phrases that must be in the document title"
    ] = None,
    order_by: Annotated[
        Optional[OrderBy],
        "Sort order. Defaults to listing the most recently modified documents first",
    ] = OrderBy.MODIFIED_TIME_DESC,
    supports_all_drives: Annotated[
        Optional[bool],
        "Whether the requesting application supports both My Drives and shared drives",
    ] = False,
    limit: Annotated[Optional[int], "The number of documents to list"] = 50,
) -> Annotated[
    dict,
    "A dictionary containing 'documents_count' (number of documents returned) and 'documents' (a list of document details including 'kind', 'mimeType', 'id', and 'name' for each document)",
]:
    """
    List documents in the user's Google Drive. Excludes documents that are in the trash.
    """
    page_size = min(10, limit)
    page_token = None  # The page token is used for continuing a previous request on the next page
    files = []

    service = build_drive_service(context.authorization.token)

    query = "mimeType = 'application/vnd.google-apps.document' and trashed = false"
    if title_keywords:
        # Escape single quotes in title_keywords
        title_keywords = [keyword.replace("'", "\\'") for keyword in title_keywords]
        # Only support logically ANDed keywords in query for now
        keyword_queries = [f"name contains '{keyword}'" for keyword in title_keywords]
        query += " and " + " and ".join(keyword_queries)

    # Prepare the request parameters
    params = {
        "q": query,
        "pageSize": page_size,
        "orderBy": order_by.value,
        "corpora": corpora.value,
        "supportsAllDrives": supports_all_drives,
    }
    params = remove_none_values(params)

    # Paginate through the results until the limit is reached
    while len(files) < limit:
        if page_token:
            params["pageToken"] = page_token
        else:
            params.pop("pageToken", None)

        results = service.files().list(**params).execute()
        batch = results.get("files", [])
        files.extend(batch[: limit - len(files)])

        page_token = results.get("nextPageToken")
        if not page_token or len(batch) < page_size:
            break

    return {"documents_count": len(files), "documents": files}
