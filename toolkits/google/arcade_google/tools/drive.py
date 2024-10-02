import json
from typing import Annotated, Optional

from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_drive_service, remove_none_values

from .models import Corpora, OrderBy

"""
Implements: https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list

TODO: Support pagination.
TODO: Support query with natural language. Currently, the tool expects a fully formed query string as input with the syntax defined here: https://developers.google.com/drive/api/guides/search-files
TODO: This returns all files including trashed ones. Dont include them by default, but add ability to add them.
"""


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
)
async def list_drive_files(
    context: ToolContext,
    corpora: Annotated[Corpora, "The source of files to list"] = Corpora.USER,
    order_by: Annotated[list[OrderBy] | None, "Sort order"] = None,
    page_size: Annotated[int, "Number of files to return per page"] = 10,
    page_token: Annotated[Optional[str], "A token for requesting the next page of results"] = None,
    q: Annotated[
        Optional[str],
        "A query for filtering the file result. Return all files and folders if None. See https://developers.google.com/drive/api/guides/search-files for supported syntax.",
    ] = None,
    supports_all_drives: Annotated[
        bool, "Whether the requesting application supports both My Drives and shared drives"
    ] = False,
    limit: Annotated[int, "The number of files to return"] = 10,
) -> Annotated[
    str,
    "A JSON string containing a list of file details including 'kind', 'mimeType', 'id', and 'name' for each file",
]:
    """
    List files in the user's Google Drive.
    """
    page_size = 10
    # page_token = None

    try:
        service = build_drive_service(context.authorization.token)

        # Prepare the request parameters
        params = {
            "q": q,
            "pageSize": page_size,
            "orderBy": ",".join(sort_key.value for sort_key in order_by) if order_by else None,
            "corpora": corpora.value,
            "supportsAllDrives": supports_all_drives,
        }
        params = remove_none_values(params)

        # Execute the files().list() method
        # TODO: Implement pagination. Continue to call the method with the page_token until the limit is reached.
        results = service.files().list(**params).execute()
        # next_page_token = results.get("nextPageToken")
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


# """
# only works if the file is stored in Drive. To download Google Docs, Sheets, and Slides use files.export
# """


# @tool(
#     requires_auth=Google(
#         scopes=["https://www.googleapis.com/auth/drive.readonly"],
#     )
# )
# async def get_file(
#     context: ToolContext,
#     file_id: Annotated[str, "The ID of the file to retrieve"],
#     acknowledge_abuse: Annotated[
#         Optional[bool], "Acknowledge the risk of downloading known malware or other abusive files"
#     ] = None,
#     include_labels: Annotated[
#         Optional[str], "A comma-separated list of IDs of labels to include in the response"
#     ] = None,
#     include_permissions_for_view: Annotated[
#         Optional[str], "Specifies which additional view's permissions to include in the response"
#     ] = None,
#     supports_all_drives: Annotated[
#         Optional[bool],
#         "Whether the requesting application supports both My Drives and shared drives",
#     ] = None,
# ) -> Annotated[str, "The media object as a string"]:
#     """
#     Get a file's metadata or content by ID.
#     """
#     try:
#         service = build_drive_service(context.authorization.token)

#         # Prepare the request parameters
#         params = {
#             "acknowledgeAbuse": acknowledge_abuse,
#             "includeLabels": include_labels,
#             "includePermissionsForView": include_permissions_for_view,
#             "supportsAllDrives": supports_all_drives,
#             "alt": "media",
#         }
#         params = remove_none_values(params)

#         # Execute the files().get_media() method
#         request = service.files().get(
#             fileId=file_id, **params
#         )  # Returns File object https://developers.google.com/drive/api/reference/rest/v3/files#File
#         response = request.execute()

#         return json.dumps(response)

#     except HttpError as e:
#         raise ToolExecutionError(
#             f"HttpError during execution of '{get_file.__name__}' tool.",
#             str(e),
#         )
#     except Exception as e:
#         raise ToolExecutionError(
#             f"Unexpected Error encountered during execution of '{get_file.__name__}' tool.",
#             str(e),
#         )


# @tool(
#     requires_auth=Google(
#         scopes=[
#             "https://www.googleapis.com/auth/drive.readonly",
#         ],
#     )
# )
# async def export_file(
#     context: ToolContext,
#     file_id: Annotated[str, "The ID of the file to export"],
#     mime_type: Annotated[str, "The MIME type of the format requested for this export"],
# ) -> Annotated[str, "The exported file content as bytes"]:
#     """
#     Export a Google Workspace document to the requested MIME type.
#     """
#     try:
#         service = build_drive_service(context.authorization.token)

#         # Execute the files().export() method
#         request = service.files().export(fileId=file_id, mimeType=mime_type)
#         response = request.execute()

#         return json.dumps(response)

#     except HttpError as e:
#         raise ToolExecutionError(
#             f"HttpError during execution of '{export_file.__name__}' tool.",
#             str(e),
#         )
#     except Exception as e:
#         raise ToolExecutionError(
#             f"Unexpected Error encountered during execution of '{export_file.__name__}' tool.",
#             str(e),
#         )
