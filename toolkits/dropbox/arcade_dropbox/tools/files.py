from typing import Annotated, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Dropbox
from arcade_tdk.errors import ToolExecutionError

from arcade_dropbox.constants import Endpoint
from arcade_dropbox.exceptions import DropboxApiError
from arcade_dropbox.utils import parse_dropbox_path, send_dropbox_request


@tool(
    requires_auth=Dropbox(
        scopes=["files.content.read"],
    )
)
async def download_file(
    context: ToolContext,
    file_path: Annotated[
        Optional[str],
        "The path of the file to download. E.g. '/AcmeInc/Reports/Q1_2025.txt'. Defaults to None.",
    ] = None,
    file_id: Annotated[
        Optional[str],
        "The ID of the file to download. E.g. 'id:a4ayc_80_OEAAAAAAAAAYa'. Defaults to None.",
    ] = None,
) -> Annotated[dict, "Contents of the specified file"]:
    """Downloads the specified file.

    Note: either one of `file_path` or `file_id` must be provided.
    """
    if not file_path and not file_id:
        raise ToolExecutionError("Either `file_path` or `file_id` must be provided.")

    if file_path and file_id:
        raise ToolExecutionError("Only one of `file_path` or `file_id` can be provided.")

    try:
        result = await send_dropbox_request(
            context.get_auth_token_or_empty(),
            endpoint=Endpoint.DOWNLOAD_FILE,
            path=parse_dropbox_path(file_path) or file_id,
        )
    except DropboxApiError as api_error:
        return {"error": api_error.message}

    return {"file": result}
