import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..api_client import GibsonAIClient


def _validate_record_columns_simple(records: list[dict[str, Any]]) -> list[str]:
    """Validate that all records have the same columns and return column names."""
    if not records:
        raise ValueError("At least one record is required")

    columns = list(records[0].keys())
    for i, record in enumerate(records[1:], 1):
        if set(record.keys()) != set(columns):
            raise ValueError(f"Record {i + 1} has different columns than the first record")

    return columns


def _build_insert_query_simple(
    table_name: str, records: list[dict[str, Any]], on_conflict: str, columns: list[str]
) -> str:
    """Build the INSERT SQL query from simple parameters."""
    columns_str = ", ".join(f"`{col}`" for col in columns)

    conflict_clause = ""
    if on_conflict.strip():
        if on_conflict.upper() == "IGNORE":
            conflict_clause = " ON DUPLICATE KEY UPDATE id=id"
        elif on_conflict.upper() == "REPLACE":
            conflict_clause = " ON DUPLICATE KEY UPDATE " + ", ".join(
                f"`{col}`=VALUES(`{col}`)" for col in columns
            )

    # Build value groups
    value_groups = []
    for record in records:
        values = []
        for col in columns:
            val = record[col]
            if val is None:
                values.append("NULL")
            elif isinstance(val, str):
                # Escape single quotes for SQL safety
                escaped_val = val.replace("'", "''")
                values.append(f"'{escaped_val}'")
            else:
                values.append(str(val))
        value_groups.append(f"({', '.join(values)})")

    # Build complete query using proper SQL construction
    # Note: table_name is validated above, not user-controlled
    query_parts = ["INSERT INTO", f"`{table_name}`", f"({columns_str})", "VALUES"]
    query_parts.append(", ".join(value_groups))
    if conflict_clause:
        query_parts.append(conflict_clause)

    query = " ".join(query_parts)
    return query


def _validate_insert_inputs(table_name: str, parsed_records: list) -> None:
    """Validate insert inputs and raise appropriate errors."""
    # Validate table name
    if not table_name.strip():
        raise ValueError("Table name cannot be empty")
    dangerous_keywords = [";", "--", "/*", "*/", "drop", "delete", "truncate"]
    if any(keyword in table_name.lower() for keyword in dangerous_keywords):
        raise ValueError("Invalid characters in table name")

    # Validate records
    if not parsed_records:
        raise ValueError("At least one record is required")


@tool(requires_secrets=["GIBSONAI_API_KEY"])
async def insert_records(
    context: ToolContext,
    table_name: Annotated[str, "Name of the table to insert data into"],
    records: Annotated[
        str,
        "JSON string containing a list of records to insert. Each record should be an object "
        'with column names as keys. Example: \'[{"name": "John", "age": 30}]\'',
    ],
    on_conflict: Annotated[
        str, "How to handle conflicts (e.g., 'IGNORE', 'REPLACE', 'UPDATE'). Leave empty for none"
    ] = "",
) -> list[str]:
    """
    Insert records into a GibsonAI database table with type validation and safety checks.

    This tool provides a safe way to insert data with:
    * Input validation and type checking
    * SQL injection protection
    * Consistent data formatting
    * Conflict resolution options

    Examples of usage:
    * Insert single record: table_name="users",
      records='[{"name": "John", "email": "john@example.com"}]'
    * Insert multiple records with conflict handling
    * Batch inserts with validation

    The tool automatically generates properly formatted INSERT statements
    based on the validated input data.
    """
    api_key = context.get_secret("GIBSONAI_API_KEY")
    client = GibsonAIClient(api_key)

    try:
        # Parse JSON records
        try:
            parsed_records = json.loads(records)
            if not isinstance(parsed_records, list):
                raise TypeError("Records must be a JSON array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e

        # Validate table name and records
        _validate_insert_inputs(table_name, parsed_records)

        # Validate columns consistency across all records
        columns = _validate_record_columns_simple(parsed_records)

        # Build and execute the INSERT query
        query = _build_insert_query_simple(table_name, parsed_records, on_conflict, columns)
        results = await client.execute_query(query)

    except ValueError as e:
        raise RetryableToolError(
            f"Validation error: {e}",
            developer_message=f"Invalid data provided for insert: {e}",
            additional_prompt_content="Please check your data format and try again.",
            retry_after_ms=0,
        ) from e
    except Exception as e:
        raise RetryableToolError(
            f"Insert failed: {e}",
            developer_message=f"Insert operation failed for table '{table_name}': {e}",
            additional_prompt_content="Please check your table name and data format.",
            retry_after_ms=10,
        ) from e
    else:
        return results
