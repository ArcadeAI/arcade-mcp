import base64
import json
from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google
from arcade_tdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google_drive.enums import OrderBy
from arcade_google_drive.templates import optional_file_picker_instructions_template
from arcade_google_drive.utils import (
    build_drive_service,
    build_file_tree,
    build_file_tree_request_params,
)


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    ),
    requires_metadata=[ToolMetadataKey.CLIENT_ID, ToolMetadataKey.COORDINATOR_URL],
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
    service = build_drive_service(context.get_auth_token_or_empty())

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

    file_picker_response = generate_google_file_picker_url(
        context,
    )

    return {
        "drives": drives,
        "file_picker": {
            "url": file_picker_response["url"],
            "llm_instructions": optional_file_picker_instructions_template.format(
                url=file_picker_response["url"]
            ),
        },
    }


@tool(
    requires_auth=Google(),
    requires_metadata=[ToolMetadataKey.CLIENT_ID, ToolMetadataKey.COORDINATOR_URL],
)
def generate_google_file_picker_url(
    context: ToolContext,
) -> Annotated[dict, "Google File Picker URL for user file selection and permission granting"]:
    """Generate a Google File Picker URL for user-driven file selection and authorization.

    This tool generates a URL that directs the end-user to a Google File Picker interface where
    where they can select or upload Google Drive files. Users can grant permission to access their
    Drive files, providing a secure and authorized way to interact with their files.

    This is particularly useful when prior tools (e.g., those accessing or modifying
    Google Docs, Google Sheets, etc.) encountered failures due to file non-existence
    (Requested entity was not found) or permission errors. Once the user completes the file
    picker flow, the prior tool can be retried.
    """
    client_id = context.get_metadata(ToolMetadataKey.CLIENT_ID)
    client_id_parts = client_id.split("-")
    if not client_id_parts:
        raise ToolExecutionError(
            message="Invalid Google Client ID",
            developer_message=f"Google Client ID '{client_id}' is not valid",
        )
    app_id = client_id_parts[0]
    cloud_coordinator_url = context.get_metadata(ToolMetadataKey.COORDINATOR_URL).strip("/")

    config = {
        "auth": {
            "client_id": client_id,
            "app_id": app_id,
        },
    }
    config_json = json.dumps(config)
    config_base64 = base64.urlsafe_b64encode(config_json.encode("utf-8")).decode("utf-8")
    url = f"{cloud_coordinator_url}/google/drive_picker?config={config_base64}"

    return {
        "url": url,
        "llm_instructions": (
            "Instruct the user to click the following link to open the Google Drive File Picker. "
            "This will allow them to select files and grant access permissions: {url}"
        ),
    }
