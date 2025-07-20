import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..api_client import GibsonAIClient


def _validate_update_conditions(conditions: list[dict[str, Any]]) -> None:
    """Validate that all update conditions have required keys."""
    if not conditions:
        raise ValueError("Update operations require at least one WHERE condition for safety")

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


def _build_update_query(
    table_name: str, updates: dict[str, Any], conditions: list[dict[str, Any]], limit: int
) -> tuple[str, list[Any]]:
    """Build UPDATE query with parameterized values."""
    # Build SET clause
    set_parts = []
    values: list[Any] = []
    for column, value in updates.items():
        set_parts.append(f"{column} = ?")
        values.append(value)

    set_clause = "SET " + ", ".join(set_parts)

    # Build WHERE clause
    where_parts = []
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

    # Build complete query
    query = f"UPDATE {table_name} {set_clause} {where_clause}"
    if limit > 0:
        query += f" LIMIT {limit}"

    return query, values


def _validate_update_inputs(
    table_name: str, parsed_updates: dict, parsed_conditions: list, limit: int
) -> None:
    """Validate update inputs and raise appropriate errors."""
    if not table_name or not isinstance(table_name, str):
        raise ValueError("table_name must be a non-empty string")

    if not parsed_updates:
        raise ValueError("updates must be a non-empty dictionary")

    if not parsed_conditions:
        raise TypeError("conditions must be a non-empty list")

    if limit < 0:
        raise ValueError("limit must be non-negative (0 = no limit)")


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
        A message indicating the number of records updated

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

        # Validate inputs
        _validate_update_inputs(table_name, parsed_updates, parsed_conditions, limit)

        _validate_update_conditions(parsed_conditions)

        # Build query with parameterized values
        query, values = _build_update_query(table_name, parsed_updates, parsed_conditions, limit)

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
