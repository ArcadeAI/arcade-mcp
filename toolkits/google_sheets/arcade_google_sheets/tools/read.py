from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_sheets.decorators import with_filepicker_fallback
from arcade_google_sheets.utils import (
    build_sheets_service,
    enforce_data_size_limit,
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
    sheet_identifier: Annotated[
        str,
        "The identifier of the sheet to get. This can be the order it appears "
        "in the spreadsheet (1-based), the sheet name, or the sheet id. Defaults to '1', "
        "which represents the first sheet in the spreadsheet.",
    ] = "1",
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
        "Must be between 1 and 100. Defaults to 100.",
    ] = 100,
) -> Annotated[
    dict,
    "The spreadsheet properties and data for the specified sheet in the spreadsheet",
]:
    """Gets the specified range of cells from a single sheet in the spreadsheet."""
    start_row, start_col, max_rows, max_cols = process_get_spreadsheet_params(
        start_row, start_col, max_rows, max_cols
    )

    service = build_sheets_service(context.get_auth_token_or_empty())

    data = get_spreadsheet_with_pagination(
        service,
        spreadsheet_id,
        sheet_identifier,
        start_row,
        start_col,
        max_rows,
        max_cols,
    )

    enforce_data_size_limit(data)
    return data
