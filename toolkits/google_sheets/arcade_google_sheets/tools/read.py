from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_sheets.decorators import with_filepicker_fallback
from arcade_google_sheets.utils import (
    build_sheets_service,
    get_spreadsheet_with_pagination,
    process_get_spreadsheet_params,
)


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    ),
    requires_metadata=[ToolMetadataKey.CLIENT_ID, ToolMetadataKey.COORDINATOR_URL],
)
@with_filepicker_fallback
async def get_spreadsheet(
    context: ToolContext,
    spreadsheet_id: Annotated[str, "The id of the spreadsheet to get"],
    start_row: Annotated[int, "Starting row number (1-indexed, defaults to 1)"] = 1,
    start_col: Annotated[
        str, "Starting column letter(s) or 1-based column number (defaults to 'A')"
    ] = "A",
    max_rows: Annotated[
        int,
        "Maximum number of rows to fetch for each sheet in the spreadsheet. "
        "Must be between 1 and 1000. Defaults to 1000.",
    ] = 1000,
    max_cols: Annotated[
        int,
        "Maximum number of columns to fetch for each sheet in the spreadsheet. "
        "Must be between 1 and 26. Defaults to 26.",
    ] = 26,
) -> Annotated[
    dict,
    "The spreadsheet properties and data for all sheets in the spreadsheet",
]:
    """
    Get the user entered values and formatted values for all cells in all sheets in the spreadsheet
    along with the spreadsheet's properties.
    """
    start_row, start_col, max_rows, max_cols = process_get_spreadsheet_params(
        start_row, start_col, max_rows, max_cols
    )

    service = build_sheets_service(context.get_auth_token_or_empty())

    return get_spreadsheet_with_pagination(
        service,
        spreadsheet_id,
        start_row,
        start_col,
        max_rows,
        max_cols,
    )
