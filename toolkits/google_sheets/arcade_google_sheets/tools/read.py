from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_sheets.decorators import with_filepicker_fallback
from arcade_google_sheets.utils import (
    build_sheets_service,
    get_spreadsheet_with_pagination,
    process_get_spreadsheet_params,
    raise_for_large_payload,
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
    sheet_position: Annotated[
        int | None,
        "The position/tab of the sheet in the spreadsheet to get. "
        "A value of 1 represents the first (leftmost/Sheet1) sheet . "
        "Defaults to 1.",
    ] = 1,
    sheet_id_or_name: Annotated[
        str | None,
        "The id or name of the sheet to get. "
        "Defaults to None, which means sheet_position will be used instead.",
    ] = None,
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
    """Gets the specified range of cells from a single sheet in the spreadsheet.

    sheet_id_or_name takes precedence over sheet_position. If a sheet is not mentioned,
    then always assume the default sheet_position is sufficient.
    """
    sheet_identifier, sheet_identifier_type, start_row, start_col, max_rows, max_cols = (
        process_get_spreadsheet_params(
            sheet_position,
            sheet_id_or_name,
            start_row,
            start_col,
            max_rows,
            max_cols,
        )
    )

    service = build_sheets_service(context.get_auth_token_or_empty())

    data = get_spreadsheet_with_pagination(
        service,
        spreadsheet_id,
        sheet_identifier,
        sheet_identifier_type,
        start_row,
        start_col,
        max_rows,
        max_cols,
    )

    raise_for_large_payload(data)
    return data
