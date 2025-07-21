from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_sheets.decorators import with_filepicker_fallback
from arcade_google_sheets.utils import (
    build_sheets_service,
    get_spreadsheet_simple,
    get_spreadsheet_with_pagination,
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
    max_rows_per_request: Annotated[
        int, "Maximum rows to fetch per request (defaults to 1000)"
    ] = 1000,
    max_cols_per_request: Annotated[int, "Maximum columns to fetch per request (default: 26)"] = 26,
    start_row: Annotated[int, "Starting row number (1-indexed, defaults to 1)"] = 1,
    start_col: Annotated[str, "Starting column letter (defaults to 'A')"] = "A",
    max_rows: Annotated[
        int | None, "Maximum total rows to fetch (optional, default: None for all rows)"
    ] = None,
    max_cols: Annotated[
        int | None, "Maximum total columns to fetch (optional, default: None for all columns)"
    ] = None,
) -> Annotated[
    dict,
    "The spreadsheet properties and data for all sheets in the spreadsheet",
]:
    """
    Get the user entered values and formatted values for all cells in all sheets in the spreadsheet
    along with the spreadsheet's properties. Supports pagination for large spreadsheets.

    For large spreadsheets, use pagination parameters to control memory usage:
    - max_rows_per_request: Chunk size for rows per API request
    - max_cols_per_request: Chunk size for columns per API request
    - start_row/start_col: Starting position
    - max_rows/max_cols: Optional limits on total data to fetch
    """
    service = build_sheets_service(context.get_auth_token_or_empty())

    is_using_defaults = (
        max_rows_per_request == 1000
        and max_cols_per_request == 26
        and start_row == 1
        and start_col == "A"
        and max_rows is None
        and max_cols is None
    )

    if is_using_defaults:
        return get_spreadsheet_simple(service, spreadsheet_id)
    else:
        return get_spreadsheet_with_pagination(
            service,
            spreadsheet_id,
            max_rows_per_request,
            max_cols_per_request,
            start_row,
            start_col,
            max_rows,
            max_cols,
        )
