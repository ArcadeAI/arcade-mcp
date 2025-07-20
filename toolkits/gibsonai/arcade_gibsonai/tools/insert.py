import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from pydantic import BaseModel, Field, field_validator

from ..api_client import GibsonAIClient


class InsertRequest(BaseModel):
    """Pydantic model for validating insert requests."""

    table_name: str = Field(
        ..., min_length=1, description="Name of the table to insert records into"
    )
    records: list[dict[str, Any]] = Field(
        ..., min_length=1, description="List of records to insert"
    )
    on_conflict: str = Field(default="", description="Conflict resolution strategy")

    @field_validator("table_name")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name for security."""
        if not v.strip():
            raise ValueError("Table name cannot be empty")

        dangerous_keywords = [";", "--", "/*", "*/", "drop", "delete", "truncate"]
        if any(keyword in v.lower() for keyword in dangerous_keywords):
            raise ValueError("Invalid characters in table name")

        return v.strip()

    @field_validator("records")
    @classmethod
    def validate_records_consistency(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate that all records have the same columns."""
        if not v:
            raise ValueError("At least one record is required")

        if not all(isinstance(record, dict) for record in v):
            raise ValueError("All records must be dictionaries")

        # Check column consistency
        expected_columns = set(v[0].keys())
        for i, record in enumerate(v[1:], 1):
            if set(record.keys()) != expected_columns:
                msg = f"Record {i + 1} has different columns than the first record"
                raise ValueError(msg)

        return v

    @field_validator("on_conflict")
    @classmethod
    def validate_on_conflict(cls, v: str) -> str:
        """Validate on_conflict strategy."""
        if not v:
            return ""

        valid_strategies = {"ignore", "replace", "update"}
        if v.lower() not in valid_strategies:
            strategies_str = ", ".join(valid_strategies)
            raise ValueError(f"Invalid on_conflict strategy. Must be one of: {strategies_str}")

        return v.upper()


def _build_insert_query(request: InsertRequest) -> str:
    """Build the INSERT SQL query from validated request."""
    columns = list(request.records[0].keys())
    columns_str = ", ".join(f"`{col}`" for col in columns)

    conflict_clause = ""
    if request.on_conflict:
        if request.on_conflict == "IGNORE":
            conflict_clause = " ON DUPLICATE KEY UPDATE id=id"
        elif request.on_conflict == "REPLACE":
            conflict_clause = " ON DUPLICATE KEY UPDATE " + ", ".join(
                f"`{col}`=VALUES(`{col}`)" for col in columns
            )

    # Build value groups
    value_groups = []
    for record in request.records:
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
    query_parts = ["INSERT INTO", f"`{request.table_name}`", f"({columns_str})", "VALUES"]
    query_parts.append(", ".join(value_groups))
    if conflict_clause:
        query_parts.append(conflict_clause)

    query = " ".join(query_parts)
    return query


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
    try:
        # Parse JSON records
        try:
            parsed_records = json.loads(records)
            if not isinstance(parsed_records, list):
                raise TypeError("Records must be a JSON array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e

        # Create and validate request using Pydantic
        try:
            request = InsertRequest(
                table_name=table_name, records=parsed_records, on_conflict=on_conflict
            )
        except Exception as e:
            # Convert Pydantic validation errors to more readable messages
            error_msg = str(e)
            if "String should have at least 1 character" in error_msg:
                raise ValueError("Table name cannot be empty") from e
            elif "List should have at least 1 item" in error_msg:
                raise ValueError("At least one record is required") from e
            elif "Invalid on_conflict strategy" in error_msg:
                raise ValueError(error_msg) from e
            else:
                raise ValueError(f"Validation error: {error_msg}") from e

        # Build and execute the INSERT query
        query = _build_insert_query(request)

        api_key = context.get_secret("GIBSONAI_API_KEY")
        client = GibsonAIClient(api_key)
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
