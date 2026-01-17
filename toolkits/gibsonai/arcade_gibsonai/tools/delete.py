import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from pydantic import BaseModel, Field, field_validator

from ..api_client import GibsonAIClient


class DeleteCondition(BaseModel):
    """Pydantic model for delete WHERE conditions."""

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


class DeleteRequest(BaseModel):
    """Pydantic model for validating delete requests."""

    table_name: str = Field(
        ..., min_length=1, description="Name of the table to delete records from"
    )
    conditions: list[DeleteCondition] = Field(
        ..., min_length=1, description="List of WHERE conditions for safety"
    )
    limit: int = Field(default=0, ge=0, description="Optional LIMIT for safety")
    confirm_deletion: bool = Field(
        ..., description="Explicit confirmation required (must be True to proceed)"
    )

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

    @field_validator("confirm_deletion")
    @classmethod
    def validate_confirmation(cls, v: bool) -> bool:
        """Validate deletion confirmation."""
        if not v:
            raise ValueError("confirm_deletion must be explicitly set to True to proceed")
        return v


def _build_delete_query(request: DeleteRequest) -> tuple[str, list[Any]]:
    """Build DELETE query with parameterized values from validated request."""
    # Build WHERE clause
    where_parts = []
    values: list[Any] = []

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

    # Build complete query - use parameterized query for safety
    # Note: table_name is validated above, not user-controlled
    query_parts = ["DELETE FROM", request.table_name, where_clause]
    if request.limit > 0:
        query_parts.extend(["LIMIT", str(request.limit)])

    query = " ".join(query_parts)
    return query, values


def _create_delete_request(
    table_name: str,
    parsed_conditions: list,
    limit: int,
    confirm_deletion: bool,
) -> DeleteRequest:
    """Create and validate DeleteRequest from parsed data."""
    try:
        # Convert conditions to DeleteCondition models
        condition_models = [
            DeleteCondition(column=cond["column"], operator=cond["operator"], value=cond["value"])
            for cond in parsed_conditions
        ]

        return DeleteRequest(
            table_name=table_name,
            conditions=condition_models,
            limit=limit,
            confirm_deletion=confirm_deletion,
        )
    except Exception as e:
        # Convert Pydantic validation errors to more readable messages
        error_msg = str(e)
        if "String should have at least 1 character" in error_msg:
            raise ValueError("Table name cannot be empty") from e
        elif "List should have at least 1 item" in error_msg:
            msg = "Delete operations require at least one WHERE condition for safety"
            raise ValueError(msg) from e
        elif "confirm_deletion must be explicitly set to True" in error_msg:
            raise ValueError("confirm_deletion must be explicitly set to True to proceed") from e
        else:
            raise ValueError(f"Validation error: {error_msg}") from e


@tool(requires_secrets=["GIBSONAI_API_KEY"])
async def delete_records(
    context: ToolContext,
    table_name: Annotated[str, "Name of the table to delete records from"],
    conditions: Annotated[
        str,
        "JSON string containing list of WHERE conditions. Each condition should have "
        "'column', 'operator', and 'value' keys. "
        'Example: \'[{"column": "id", "operator": "=", "value": 1}]\'',
    ],
    limit: Annotated[int, "Optional LIMIT for safety. Set to 0 for no limit"] = 0,
    confirm_deletion: Annotated[
        bool, "Explicit confirmation required (must be True to proceed)"
    ] = False,
) -> str:
    """Delete records from a table with specified conditions.

    This tool safely deletes records from the specified table. It requires at least one
    WHERE condition and explicit confirmation to prevent accidental deletions.

    Args:
        table_name: Name of the table to delete records from
        conditions: List of WHERE conditions for safety
        limit: Optional LIMIT clause for additional safety (0 = no limit)
        confirm_deletion: Must be set to True to proceed with deletion

    Returns:
        A message indicating the number of records deleted

    Raises:
        ValueError: If no conditions provided, invalid conditions, or confirmation not given
        RetryableToolError: If the database operation fails
    """
    try:
        # Parse JSON conditions
        try:
            parsed_conditions = json.loads(conditions)
            if not isinstance(parsed_conditions, list):
                raise TypeError("Conditions must be a JSON array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for conditions: {e}") from e

        # Create and validate request using Pydantic
        request = _create_delete_request(table_name, parsed_conditions, limit, confirm_deletion)

        # Build query with parameterized values
        query, values = _build_delete_query(request)

        # Execute delete
        client = GibsonAIClient(context.get_secret("GIBSONAI_API_KEY"))
        await client.execute_query(query, values)

    except ValueError as e:
        raise ValueError(f"Delete validation error: {e!s}")
    except Exception as e:
        raise RetryableToolError(f"Failed to delete records from table '{table_name}': {e!s}")
    else:
        # If we reach here, the delete was successful
        return f"Successfully deleted records from table '{table_name}'"
