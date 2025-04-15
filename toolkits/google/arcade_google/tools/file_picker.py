import base64
import json
from typing import Annotated

from arcade.sdk import ToolContext, ToolMetadataKey, tool
from arcade.sdk.auth import Google
from arcade.sdk.errors import ToolExecutionError


@tool(
    requires_auth=Google(),
    requires_metadata=[ToolMetadataKey.CLIENT_ID, ToolMetadataKey.COORDINATOR_URL],
)
def generate_google_file_picker_url(
    context: ToolContext,
) -> Annotated[str, "Google File Picker URL for user file selection and permission granting"]:
    """Generate a Google File Picker URL for user-driven file selection and authorization.

    This tool generates a URL that directs the end-user to a Google File Picker interface where
    they can select specific files to grant Arcade the necessary permissions.
    This is particularly useful when subsequent tools (e.g., those accessing or modifying
    Google Docs, spreadsheets, etc.) encounter failures due to file non-existenceor permission
    errors. Once the user completes the file picker flow, the original tool can be retried.
    """
    client_id = context.get_metadata(ToolMetadataKey.CLIENT_ID)
    client_id_parts = client_id.split("-")
    if not client_id_parts:
        raise ToolExecutionError(
            message="Invalid Google Client ID",
            developer_message=f"Google Client ID {client_id} is not valid",
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
    config_base64 = (
        base64.urlsafe_b64encode(config_json.encode("utf-8")).decode("utf-8").rstrip("=")
    )

    return f"{cloud_coordinator_url}/drive_picker?config={config_base64}"
