import base64
import json

from arcade_tdk import ToolContext, ToolMetadataKey
from arcade_tdk.errors import ToolExecutionError


def generate_google_file_picker_url(context: ToolContext) -> dict:
    """Generate a Google File Picker URL for user-driven file selection and authorization.

    Generates a URL that directs the end-user to a Google File Picker interface where
    where they can select or upload Google Drive files. Users can grant permission to access their
    Drive files, providing a secure and authorized way to interact with their files.

    This is particularly useful when prior tools (e.g., those accessing or modifying
    Google Docs, Google Sheets, etc.) encountered failures due to file non-existence
    (Requested entity was not found) or permission errors. Once the user completes the file
    picker flow, the prior tool can be retried.

    Returns:
        A dictionary containing the URL and instructions for the llm to instruct the user.
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
            f"This will allow them to select files and grant access permissions: {url}"
        ),
    }
