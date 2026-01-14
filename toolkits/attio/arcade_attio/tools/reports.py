"""Attio reporting operations - export data to Google Sheets."""

import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool

from arcade_attio.tools.records import _attio_request, _flatten_record


@tool(requires_secrets=["ATTIO_API_KEY"])
async def create_report(
    context: ToolContext,
    object_type: Annotated[str, "Object slug: 'people', 'companies', 'deals', or custom"],
    filter_json: Annotated[
        list[str] | None,
        'Filter strings: {"attribute": "x", "operator": "equals", "value": "y"}',
    ] = None,
    attributes: Annotated[
        list[str] | None,
        "Attributes to include in report (None = all available)",
    ] = None,
    sort_by: Annotated[str | None, "Attribute to sort by"] = None,
    sort_direction: Annotated[str, "'asc' or 'desc'"] = "desc",
    limit: Annotated[int, "Max records to include (1-500)"] = 100,
) -> Annotated[dict[str, Any], "Report data ready for Google Sheets export"]:
    """
    Generate a report from Attio records for export to Google Sheets.

    Returns data formatted for easy insertion into a spreadsheet:
    - headers: Column names for the first row
    - rows: List of row data (values aligned with headers)
    - data: Dict format for Google Sheets API {row: {col: value}}

    Use this output with Google Sheets tools to create a spreadsheet.
    """
    body: dict[str, Any] = {"limit": min(limit, 500)}
    if filter_json:
        body["filter"] = {"filters": [json.loads(f) for f in filter_json]}
    if sort_by:
        body["sorts"] = [{"attribute": sort_by, "direction": sort_direction}]

    response = await _attio_request("POST", f"/objects/{object_type}/records/query", body)
    records = response.get("data", [])

    # Flatten all records
    flat_records = [_flatten_record(r) for r in records]

    # Determine headers - either specified attributes or all found attributes
    if attributes:
        headers = ["record_id"] + [a for a in attributes if a != "record_id"]
    else:
        # Collect all unique keys across all records
        all_keys: set[str] = set()
        for rec in flat_records:
            all_keys.update(rec.keys())
        # Ensure record_id is first, then sort the rest
        all_keys.discard("record_id")
        headers = ["record_id", *sorted(all_keys)]

    # Build rows aligned with headers
    rows: list[list[Any]] = []
    for rec in flat_records:
        row = [rec.get(h, "") for h in headers]
        rows.append(row)

    # Build Google Sheets compatible data format
    # {row_number: {column_letter: value}}
    sheets_data: dict[int, dict[str, Any]] = {}

    # Row 1 is headers
    sheets_data[1] = {_col_letter(i): h for i, h in enumerate(headers)}

    # Rows 2+ are data
    for row_idx, row_values in enumerate(rows, start=2):
        sheets_data[row_idx] = {_col_letter(i): v for i, v in enumerate(row_values)}

    return {
        "object_type": object_type,
        "total_records": len(flat_records),
        "headers": headers,
        "rows": rows,
        "sheets_data": json.dumps(sheets_data),
    }


def _col_letter(index: int) -> str:
    """Convert 0-based column index to Excel-style letter (A, B, ... Z, AA, AB...)."""
    result = ""
    while True:
        result = chr(ord("A") + (index % 26)) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result
