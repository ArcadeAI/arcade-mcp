import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from pydantic import BaseModel, Field, field_validator

from ..api_client import GibsonAIClient


class UpdateCondition(BaseModel):
    """Pydantic model for update WHERE conditions."""

    column: str = Field(..., min_length=1, description="Column name for the condition")
    operator: str = Field(..., description="SQL operator for the condition")
    value: Any = Field(..., description="Value for the condition")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate SQL operator."""
        valid_operators = {
            "=",
            "!=",
            "<>",
            "<",
            "<=",
            ">",
            ">=",
            "LIKE",
            "NOT LIKE",
            "IN",
            "NOT IN",
            "IS NULL",
            "IS NOT NULL",
        }
        if v not in valid_operators:
            operators_str = ", ".join(sorted(valid_operators))
            raise ValueError(f"Invalid operator '{v}'. Valid operators: {operators_str}")
        return v


class UpdateRequest(BaseModel):
    """Pydantic model for validating update requests."""

    table_name: str = Field(..., min_length=1, description="Name of the table to update records in")
    updates: dict[str, Any] = Field(
        ..., min_length=1, description="Dictionary of column-value pairs to update"
    )
    conditions: list[UpdateCondition] = Field(
        ..., min_length=1, description="List of WHERE conditions for safety"
    )
    limit: int = Field(default=0, ge=0, description="Optional LIMIT for safety")

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

    @field_validator("updates")
    @classmethod
    def validate_updates(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate updates dictionary."""
        if not v:
            raise ValueError("Updates must be a non-empty dictionary")

        # Check for dangerous column names
        for column in v:
            if not isinstance(column, str) or not column.strip():
                raise ValueError("Column names must be non-empty strings")

        return v


def _build_update_query(request: UpdateRequest) -> tuple[str, list[Any]]:
    """Build UPDATE query with parameterized values from validated request."""
    # Build SET clause
    set_parts = []
    values: list[Any] = []

    for column, value in request.updates.items():
        set_parts.append(f"{column} = ?")
        values.append(value)

    set_clause = "SET " + ", ".join(set_parts)

    # Build WHERE clause
    where_parts = []
    for condition in request.conditions:
        column = condition.column
        operator = condition.operator
        value = condition.value

        if operator in ("IS NULL", "IS NOT NULL"):
            where_parts.append(f"{column} {operator}")
        elif operator in ("IN", "NOT IN"):
            if isinstance(value, list | tuple):
                placeholders = ", ".join("?" * len(value))
                where_parts.append(f"{column} {operator} ({placeholders})")
                values.extend(value)
            else:
                raise ValueError(f"Value for {operator} must be a list or tuple")
        else:
            where_parts.append(f"{column} {operator} ?")
            values.append(value)

    where_clause = "WHERE " + " AND ".join(where_parts)

    # Build complete query
    query = f"UPDATE {request.table_name} {set_clause} {where_clause}"
    if request.limit > 0:
        query += f" LIMIT {request.limit}"

    return query, values


def _create_update_request(
    table_name: str, parsed_updates: dict, parsed_conditions: list, limit: int
) -> UpdateRequest:
    """Create and validate UpdateRequest from parsed data."""
    try:
        # Convert conditions to UpdateCondition models
        condition_models = [
            UpdateCondition(column=cond["column"], operator=cond["operator"], value=cond["value"])
            for cond in parsed_conditions
        ]

        return UpdateRequest(
            table_name=table_name,
            updates=parsed_updates,
            conditions=condition_models,
            limit=limit,
        )
    except Exception as e:
        # Convert Pydantic validation errors to more readable messages
        error_msg = str(e)
        if "String should have at least 1 character" in error_msg:
            raise ValueError("Table name cannot be empty") from e
        elif "List should have at least 1 item" in error_msg:
            msg = "Update operations require at least one WHERE condition for safety"
            raise ValueError(msg) from e
        elif "Updates must be a non-empty dictionary" in error_msg:
            raise ValueError("Updates must be a non-empty dictionary") from e
        else:
            raise ValueError(f"Validation error: {error_msg}") from e


@tool(requires_secrets=["GIBSONAI_API_KEY"])
async def update_records(
    context: ToolContext,
    table_name: Annotated[str, "Name of the table to update records in"],
    updates: Annotated[
        str,
        "JSON string containing column-value pairs to update. "
        'Example: \'{"name": "John", "age": 30}\'',
    ],
    conditions: Annotated[
        str,
        "JSON string containing list of WHERE conditions. Each condition should have "
        "'column', 'operator', and 'value' keys. "
        'Example: \'[{"column": "id", "operator": "=", "value": 1}]\'',
    ],
    limit: Annotated[int, "Optional LIMIT for safety. Set to 0 for no limit"] = 0,
) -> str:
    """Update records in a table with specified conditions.

    This tool safely updates records in the specified table. It requires at least one
    WHERE condition to prevent accidental updates to all records.

    Args:
        table_name: Name of the table to update records in
        updates: Dictionary of column names to new values
        conditions: List of WHERE conditions for safety
        limit: Optional LIMIT clause for additional safety (0 = no limit)

    Returns:
        A message indicating successful update

    Raises:
        ValueError: If no conditions provided or invalid conditions
        RetryableToolError: If the database operation fails
    """
    try:
        # Parse JSON parameters
        try:
            parsed_updates = json.loads(updates)
            if not isinstance(parsed_updates, dict):
                raise TypeError("Updates must be a JSON object")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for updates: {e}") from e

        try:
            parsed_conditions = json.loads(conditions)
            if not isinstance(parsed_conditions, list):
                raise TypeError("Conditions must be a JSON array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for conditions: {e}") from e

        # Create and validate request using Pydantic
        request = _create_update_request(table_name, parsed_updates, parsed_conditions, limit)

        # Build query with parameterized values
        query, values = _build_update_query(request)

        # Execute update
        client = GibsonAIClient(context.get_secret("GIBSONAI_API_KEY"))
        await client.execute_query(query, values)

    except ValueError as e:
        raise RetryableToolError(f"Update validation error: {e!s}")
    except Exception as e:
        raise RetryableToolError(f"Failed to update records in table '{table_name}': {e!s}")
    else:
        # If we reach here, the update was successful
        return f"Successfully updated records in table '{table_name}'"
