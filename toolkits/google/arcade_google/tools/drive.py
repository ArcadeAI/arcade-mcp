from typing import Annotated, Optional

from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_drive_service, remove_none_values

from .models import Corpora, OrderBy


# Implements: https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list
# TODO: Support pagination.
# TODO: Support query with natural language. Currently, the tool expects a fully formed query string as input with the syntax defined here: https://developers.google.com/drive/api/guides/search-files
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def list_documents(
    context: ToolContext,
    corpora: Annotated[Optional[Corpora], "The source of files to list"] = Corpora.USER,
    order_by: Annotated[
        Optional[OrderBy],
        "Sort order. Defaults to listing the most recently updated documents first",
    ] = OrderBy.UPDATED_TIME_DESC,
    supports_all_drives: Annotated[
        Optional[bool],
        "Whether the requesting application supports both My Drives and shared drives",
    ] = False,
    limit: Annotated[Optional[int], "The number of documents to list"] = 25,
) -> Annotated[
    dict,
    "A dictionary containing 'documents_count' (number of documents returned) and 'documents' (a list of document details including 'kind', 'mimeType', 'id', and 'name' for each document)",
]:
    """
    List documents in the user's Google Drive.
    """
    page_size = min(10, limit)
    page_token = None  # The page token is used for continuing a previous request on the next page
    files = []

    try:
        service = build_drive_service(context.authorization.token)

        # Prepare the request parameters
        params = {
            "q": "mimeType = 'application/vnd.google-apps.document' and trashed = false",
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

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{list_documents.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{list_documents.__name__}' tool.",
            str(e),
        )
