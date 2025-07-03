from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_sheets.decorators import with_filepicker_fallback
from arcade_google_sheets.utils import (
    build_sheets_service,
    parse_get_spreadsheet_response,
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
) -> Annotated[
    dict,
    "The spreadsheet properties and data for all sheets in the spreadsheet",
]:
    """
    Get the user entered values and formatted values for all cells in all sheets in the spreadsheet
    along with the spreadsheet's properties
    """
    service = build_sheets_service(context.get_auth_token_or_empty())

    response = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            fields="spreadsheetId,spreadsheetUrl,properties/title,sheets/properties,sheets/data/rowData/values/userEnteredValue,sheets/data/rowData/values/formattedValue,sheets/data/rowData/values/effectiveValue",
        )
        .execute()
    )
    return parse_get_spreadsheet_response(response)
