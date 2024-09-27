import json
from typing import Annotated, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google

from .models import Corpora, OrderBy


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def list_drive_files(
    context: ToolContext,
    q: Annotated[
        Optional[str], "A query for filtering the file result. Return all files and folders if None"
    ] = None,
    page_size: Annotated[int, "Number of files to return per page"] = 10,
    orderBy: Annotated[list[OrderBy] | None, "Sort order"] = None,
    corpora: Annotated[Corpora, "The source of files to list"] = Corpora.USER,
    supports_all_drives: Annotated[
        bool, "Whether the requesting application supports both My Drives and shared drives"
    ] = False,
) -> Annotated[str, "A JSON string containing a list of file details"]:
    """
    List files in the user's Google Drive.
    """
    try:
        service = build("drive", "v3", credentials=Credentials(context.authorization.token))

        # Prepare the request parameters
        params = {
            "pageSize": page_size,
            "supportsAllDrives": supports_all_drives,
        }
        if q:
            params["q"] = q
        if orderBy:
            params["orderBy"] = ",".join(sort_key.value for sort_key in orderBy)
        if corpora:
            params["corpora"] = corpora.value

        # Execute the files().list() method
        results = service.files().list(**params).execute()
        files = results.get("files", [])

        return json.dumps({"files": files})

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{list_drive_files.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{list_drive_files.__name__}' tool.",
            str(e),
        )
