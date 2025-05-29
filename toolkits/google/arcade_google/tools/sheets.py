from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google
from arcade_tdk.errors import RetryableToolError

from arcade_google.models import (
    SheetDataInput,
    Spreadsheet,
    SpreadsheetProperties,
)
from arcade_google.utils import (
    build_sheets_service,
    create_sheet,
    parse_get_spreadsheet_response,
    parse_write_to_cell_response,
    validate_write_to_cell_params,
)


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
def create_spreadsheet(
    context: ToolContext,
    title: Annotated[str, "The title of the new spreadsheet"] = "Untitled spreadsheet",
    data: Annotated[
        str | None,
        "The data to write to the spreadsheet. A JSON string "
        "(property names enclosed in double quotes) representing a dictionary that "
        "maps row numbers to dictionaries that map column letters to cell values. "
        "For example, data[23]['C'] would be the value of the cell in row 23, column C. "
        "Type hint: dict[int, dict[str, Union[int, float, str, bool]]]",
    ] = None,
) -> Annotated[dict, "The created spreadsheet's id and title"]:
    """Create a new spreadsheet with the provided title and data in its first sheet

    Returns the newly created spreadsheet's id and title
    """
    service = build_sheets_service(context.get_auth_token_or_empty())

    try:
        sheet_data = SheetDataInput(data=data)  # type: ignore[arg-type]
    except Exception as e:
        msg = "Invalid JSON or unexpected data format for parameter `data`"
        raise RetryableToolError(
            message=msg,
            additional_prompt_content=f"{msg}: {e}",
            retry_after_ms=100,
        )

    spreadsheet = Spreadsheet(
        properties=SpreadsheetProperties(title=title),
        sheets=[create_sheet(sheet_data)],
    )

    body = spreadsheet.model_dump()

    response = (
        service.spreadsheets()
        .create(body=body, fields="spreadsheetId,spreadsheetUrl,properties/title")
        .execute()
    )

    return {
        "title": response["properties"]["title"],
        "spreadsheetId": response["spreadsheetId"],
        "spreadsheetUrl": response["spreadsheetUrl"],
    }


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
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


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
)
def write_to_cell(
    context: ToolContext,
    spreadsheet_id: Annotated[str, "The id of the spreadsheet to write to"],
    column: Annotated[str, "The column string to write to. For example, 'A', 'F', or 'AZ'"],
    row: Annotated[int, "The row number to write to"],
    value: Annotated[str, "The value to write to the cell"],
    sheet_name: Annotated[
        str, "The name of the sheet to write to. Defaults to 'Sheet1'"
    ] = "Sheet1",
) -> Annotated[dict, "The status of the operation"]:
    """
    Write a value to a single cell in a spreadsheet.
    """
    service = build_sheets_service(context.get_auth_token_or_empty())
    validate_write_to_cell_params(service, spreadsheet_id, sheet_name, column, row)

    range_ = f"'{sheet_name}'!{column.upper()}{row}"
    body = {
        "range": range_,
        "majorDimension": "ROWS",
        "values": [[value]],
    }

    sheet_properties = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            includeValuesInResponse=True,
            body=body,
        )
        .execute()
    )

    return parse_write_to_cell_response(sheet_properties)
