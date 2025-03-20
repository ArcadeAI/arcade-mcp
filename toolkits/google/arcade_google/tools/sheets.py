from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from arcade.sdk.errors import RetryableToolError

from arcade_google.models import (
    SheetDataInput,
    Spreadsheet,
    SpreadsheetProperties,
)
from arcade_google.utils import (
    build_sheets_service,
    create_sheet,
    parse_get_spreadsheet_response,
)

"""
Possible input data for a sheet:

Option 1:
    data: Annotated[
        Optional[str],
        "The data to write to the spreadsheet. A JSON string representing a dictionary mapping "
        "row numbers to dictionaries mapping column letters to cell values. "
        "For example, data[23]['C'] would be the value of the cell in row 23, column C. "
        "Type hint: dict[int, dict[str, Union[int, float, str, bool]]]",
    ] = None,

Option 2:
    data: Annotated[
        Optional[str],
        "The data to write to the spreadsheet. A list of lists of values, where each inner list "
        "represents a row in the spreadsheet. An empty outer list represents an empty row. An "
        "empty inner list represents an empty cell. For example, data[22][2] would be the value "
        "of the cell in row 23, column C. "
        "Type hint: list[list[Union[int, float, str, bool]]]",
    ] = None,

Option 3:
    data: Annotated[
        Optional[str],
        "The data to write to the spreadsheet. A JSON string representing a dictionary, "
        "where each key is the column letter and row number (as a string) and each value is "
        "the cell value. For example, data['C23'] would be the value of the cell in column C, "
        "row 23. "
        "Type hint: dict[str, Union[int, float, str, bool]]",
    ] = None,
"""


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
)
def create_spreadsheet(
    context: ToolContext,
    title: Annotated[str, "The title of the new spreadsheet"] = "Untitled spreadsheet",
    data: Annotated[
        Optional[str],
        "The data to write to the spreadsheet. A JSON string "
        "(property names enclosed in double quotes) representing a dictionary that "
        "maps row numbers to dictionaries that map column letters to cell values. "
        "For example, data[23]['C'] would be the value of the cell in row 23, column C. "
        "Type hint: dict[int, dict[str, Union[int, float, str, bool]]]",
    ] = None,
) -> Annotated[dict, "The created spreadsheet's id and title"]:
    """Create a new spreadsheet with the provided title and data

    Returns the newly created spreadsheet's id and title
    """
    service = build_sheets_service(context.get_auth_token_or_empty())

    try:
        sheet_data = SheetDataInput(data=data)
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


# @tool(
#     requires_auth=Google(
#         scopes=["https://www.googleapis.com/auth/spreadsheets"],
#     )
# )
# def update_sheet(
#     context: ToolContext,
#     spreadsheet_id: Annotated[str, "The name of the spreadsheet to update"],
#     sheet_name: Annotated[str, "The name of the sheet to update"],
#     start_column: Annotated[str, "The start column of the range to update"],
#     end_column: Annotated[str, "The end column of the range to update"],
#     start_row: Annotated[int, "The start row of the range to update"],
#     end_row: Annotated[int, "The end row of the range to update"],
# ) -> Annotated[dict, "The updated spreadsheet's id and title"]:
#     """Create a new blank spreadsheet with the provided title

#     Returns the newly created spreadsheet's id and title
#     """
#     service = build_sheets_service(context.get_auth_token_or_empty())

#     body = {
#         "requests": [
#             {
#                 "updateCells": {
#                     "rows": [
#                         {
#                             "values": [
#                                 {"userEnteredValue": {"stringValue": "my string!"}},
#                                 {"userEnteredValue": {"numberValue": 123}},
#                                 {},
#                                 {"userEnteredValue": {"boolValue": True}},
#                             ]
#                         },
#                         {
#                             "values": [
#                                 {"userEnteredValue": {"stringValue": "my string2!"}},
#                                 {"userEnteredValue": {"numberValue": 1234}},
#                                 {},
#                                 {"userEnteredValue": {"boolValue": False}},
#                             ]
#                         },
#                     ],
#                     "start": {"rowIndex": start_row, "columnIndex": start_column},
#                     "end": {"rowIndex": end_row, "columnIndex": end_column},
#                 }
#             }
#         ]
#     }

#     response = (
#         service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
#     )

#     print(response)

#     return {"status": "success"}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
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
    Get the user entered data for all sheets in the spreadsheet
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


# @tool(
#     requires_auth=Google(
#         scopes=["https://www.googleapis.com/auth/drive"],  # TODO: Change to drive.file
#     )
# )
# def write_to_cell(
#     context: ToolContext,
#     spreadsheet_name: Annotated[str, "The name of the spreadsheet to write to"],
#     column: Annotated[str, "The column to write to"],
#     row: Annotated[int, "The row to write to"],
#     value: Annotated[str, "The value to write to the cell"],
#     sheet_name: Annotated[Optional[str], "The name of the sheet to write to"] = "Sheet1",
# ) -> Annotated[dict, "The status of the operation"]:
#     """
#     Write a value to a cell in a spreadsheet.
#     """
#     # TODO: Validate column is a valid column name
#     # TODO: Validate row is a valid row number
#     # TODO: Figure out how to support multiple types of values e.g., strings, numbers, booleans,..
#     # TODO: Get the spreadsheet id from the spreadsheet name
#     spreadsheet_id = "1v4Gp6-a3hWdR-dc4kCUdM0D4vV1OmL7mMgV5g76jL4U"
#     range_ = f"'{sheet_name}'!{column}{row}"

#     service = build_sheets_service(context.get_auth_token_or_empty())

#     # TODO: Create enum for valueInputOption?
#     service.spreadsheets().values().update(
#         spreadsheetId=spreadsheet_id,
#         range=range_,
#         valueInputOption="USER_ENTERED",
#         body={
#             "range": range_,
#             "majorDimension": "ROWS",
#             "values": [[value]],
#         },
#     ).execute()

#     # TODO: Should we return the updated spreadsheet data? I think we should.
#     return {"status": "success"}


# @tool(
#     requires_auth=Google(
#         scopes=["https://www.googleapis.com/auth/drive"],  # TODO: Change to drive.file
#     )
# )
# def write_to_range(
#     context: ToolContext,
#     values: Annotated[list[list[str]], "The values to write to the range"],
#     start_column: Annotated[str, "The start column of the range to get"],
#     end_column: Annotated[str, "The end column of the range to get"],
#     start_row: Annotated[int, "The start row of the range to get"],
#     end_row: Annotated[int, "The end row of the range to get"],
#     spreadsheet_name: Annotated[
#         Optional[str], "The name of the spreadsheet to get"
#     ] = "1v4Gp6-a3hWdR-dc4kCUdM0D4vV1OmL7mMgV5g76jL4U",
#     sheet_name: Annotated[Optional[str], "The name of the sheet to get"] = "Sheet1",
# ) -> Annotated[dict, "The status of the operation"]:
#     """
#     Write a values to a range in a spreadsheet.
#     """
#     # TODO: Validate start_column and end_column are valid column names
#     # TODO: Validate start_row and end_row are valid row numbers
#     # TODO: Get the spreadsheet id from the spreadsheet name
#     spreadsheet_id = "1v4Gp6-a3hWdR-dc4kCUdM0D4vV1OmL7mMgV5g76jL4U"
#     range_ = f"'{sheet_name}'!{start_column}{start_row}:{end_column}{end_row}"

#     service = build_sheets_service(
#         context.authorization.token
#         if context.authorization and context.authorization.token
#         else ""
#     )

#     # TODO: Create enum for valueInputOption?
#     service.spreadsheets().values().update(
#         spreadsheetId=spreadsheet_id,
#         range=range_,
#         valueInputOption="USER_ENTERED",
#         body={"values": values},
#     ).execute()

#     return {"status": "success"}


# def column_index_to_letter(n):
#     """Convert a 0-indexed column number to its corresponding Google Sheets column letter."""
#     result = ""
#     while n >= 0:
#         #  65 is 'A' in ASCII & 26 is the number of letters in the alphabet
#         result = chr(n % 26 + 65) + result
#         n = n // 26 - 1
#     return result


# def convert_to_a1(sheet_data: dict) -> dict:
#     """
#     Convert sheet data in the form of:
#     {
#       "majorDimension": "ROWS",
#       "range": "Sheet1!A1:Z1000",
#       "values": [
#           [...],
#           [...]
#       ]
#     }
#     to a dictionary in the form of:
#     {
#         "A1": "value",
#         "A2": "value",
#         "B2": "value",
#         "C13": "value",
#         ...
#     }
#     """
#     a1_dict = {}
#     values = sheet_data.get("values", [])

#     if sheet_data.get("majorDimension") == "ROWS":
#         for row_index, row in enumerate(values):
#             # Ensure row is a list, even if empty
#             if not isinstance(row, list):
#                 continue
#             for col_index, cell in enumerate(row):
#                 if cell:  # only include non-empty cells
#                     col_letter = column_index_to_letter(col_index)
#                     cell_ref = f"{col_letter}{row_index + 1}"
#                     a1_dict[cell_ref] = cell
#     # TODO: Implement column-major conversion
#     return a1_dict


# def convert_to_column_dict(sheet_data: dict) -> dict:
#     """
#     Convert sheet data in the form of:
#     {
#         "majorDimension": "ROWS",
#         "range": "Sheet1!A1:Z1000",
#         "values": [
#             [...],
#             [...],
#             [...],
#             ...
#         ]
#     }
#     to a dictionary in the form of:
#     {
#         "A": {"1": "value", "2": "value", "13": "value"},
#         "B": {"4": "value", "5": "value", "16": "value"},
#         "X": {"1": "value", "78": "value", "23": "value"},
#     }

#     The resultant dictionary is a mapping of column letters
#     to a dictionary of row numbers to cell values.
#     """
#     result = {}
#     values = sheet_data.get("values", [])
#     major_dimension = sheet_data.get("majorDimension", "ROWS")

#     if major_dimension == "ROWS":
#         for row_index, row in enumerate(values):
#             # Ensure row is a list, even if empty
#             if not isinstance(row, list):
#                 continue
#             for col_index, cell in enumerate(row):
#                 # Only include non-empty cells (adjust this logic if 0 or False are valid values)
#                 if cell:
#                     col_letter = column_index_to_letter(col_index)
#                     if col_letter not in result:
#                         result[col_letter] = {}
#                     # Use row numbers as strings
#                     result[col_letter][str(row_index + 1)] = cell
#     elif major_dimension == "COLUMNS":
#         # If the data is column-major, each item in 'values' represents a column.
#         for col_index, col in enumerate(values):
#             if not isinstance(col, list):
#                 continue
#             col_letter = column_index_to_letter(col_index)
#             for row_index, cell in enumerate(col):
#                 if cell:
#                     if col_letter not in result:
#                         result[col_letter] = {}
#                     result[col_letter][str(row_index + 1)] = cell

#     return {"range": sheet_data.get("range"), "values": result}


# def convert_to_row_dct(sheet_data: dict) -> dict:
#     """
#     Convert sheet data in the form of:
#         {
#             "majorDimension": "ROWS",
#             "range": "Sheet1!A1:Z1000",
#             "values": [
#                 [...],
#                 [...],
#                 [...],
#                 ...
#             ]
#         }
#     or with "majorDimension" set as "COLUMNS", to a dictionary mapping row numbers
#     (as strings) to dictionaries mapping column letters to cell values.

#     For example, a possible output is:

#         {
#             "1": {"A": "value", "B": "value"},
#             "2": {"A": "value"},
#             ...
#         }

#     The returned dictionary also includes the original range.
#     """
#     result = {}
#     values = sheet_data.get("values", [])
#     major_dimension = sheet_data.get("majorDimension", "ROWS")

#     if major_dimension == "ROWS":
#         for row_index, row in enumerate(values):
#             # Ensure row is a list, even if empty
#             if not isinstance(row, list):
#                 continue
#             row_key = str(row_index + 1)
#             for col_index, cell in enumerate(row):
#                 # Only include non-empty cells (adjust logic if 0 or False are valid values)
#                 if cell:
#                     col_letter = column_index_to_letter(col_index)
#                     if row_key not in result:
#                         result[row_key] = {}
#                     result[row_key][col_letter] = cell
#     elif major_dimension == "COLUMNS":
#         # If the incoming data is column-major, each item in 'values' represents a column.
#         for col_index, col in enumerate(values):
#             if not isinstance(col, list):
#                 continue
#             col_letter = column_index_to_letter(col_index)
#             for row_index, cell in enumerate(col):
#                 if cell:
#                     row_key = str(row_index + 1)
#                     if row_key not in result:
#                         result[row_key] = {}
#                     result[row_key][col_letter] = cell

#     return {"range": sheet_data.get("range"), "values": result}
