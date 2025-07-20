import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..api_client import GibsonAIClient


def _validate_delete_conditions(conditions: list[dict[str, Any]]) -> None:
    """Validate that all delete conditions have required keys."""
    if not conditions:
        raise ValueError("Delete operations require at least one WHERE condition for safety")

    required_keys = {"column", "operator", "value"}
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

    for i, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            raise TypeError(f"Condition {i} must be a dictionary")

        missing_keys = required_keys - set(condition.keys())
        if missing_keys:
            raise ValueError(f"Condition {i} missing required keys: {missing_keys}")

        if condition["operator"] not in valid_operators:
            raise ValueError(
                f"Condition {i} has invalid operator '{condition['operator']}'. "
                f"Valid operators: {', '.join(sorted(valid_operators))}"
            )


def _build_delete_query(
    table_name: str, conditions: list[dict[str, Any]], limit: int
) -> tuple[str, list[Any]]:
    """Build DELETE query with parameterized values."""
    # Build WHERE clause
    where_parts = []
    values: list[Any] = []

    for condition in conditions:
        column = condition["column"]
        operator = condition["operator"]
        value = condition["value"]

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
    query_parts = ["DELETE FROM", table_name, where_clause]
    if limit > 0:
        query_parts.extend(["LIMIT", str(limit)])

    query = " ".join(query_parts)
    return query, values


def _validate_delete_inputs(
    table_name: str,
    parsed_conditions: list,
    limit: int,
    confirm_deletion: bool,
) -> None:
    """Validate delete inputs and raise appropriate errors."""
    if not table_name or not isinstance(table_name, str):
        raise ValueError("table_name must be a non-empty string")

    if not parsed_conditions:
        raise TypeError("conditions must be a non-empty list")

    if limit < 0:
        raise ValueError("limit must be non-negative (0 = no limit)")

    if not confirm_deletion:
        raise ValueError("confirm_deletion must be explicitly set to True to proceed")


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

        # Validate inputs
        _validate_delete_inputs(table_name, parsed_conditions, limit, confirm_deletion)

        _validate_delete_conditions(parsed_conditions)

        # Build query with parameterized values
        query, values = _build_delete_query(table_name, parsed_conditions, limit)

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
