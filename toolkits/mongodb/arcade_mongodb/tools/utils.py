import json
from datetime import datetime
from typing import Any

from arcade_tdk.errors import RetryableToolError
from bson import ObjectId


def _parse_json_parameter(json_string: str | None, parameter_name: str) -> Any | None:
    """
    Parse a JSON string parameter with proper error handling.

    Args:
        json_string: The JSON string to parse (can be None)
        parameter_name: Name of the parameter for error messages

    Returns:
        Parsed JSON object or None if json_string is None

    Raises:
        RetryableToolError: If JSON parsing fails
    """
    if json_string is None:
        return None

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise RetryableToolError(
            f"Invalid JSON in {parameter_name}: {e}",
            developer_message=f"Failed to parse JSON string for parameter '{parameter_name}': {json_string}. Error: {e}",
            additional_prompt_content=f"Please provide valid JSON for the {parameter_name} parameter. Check for proper escaping of quotes and valid JSON syntax.",
        ) from e


def _parse_json_list_parameter(
    json_strings: list[str] | None, parameter_name: str
) -> list[Any] | None:
    """
    Parse a list of JSON strings with proper error handling.

    Args:
        json_strings: List of JSON strings to parse (can be None)
        parameter_name: Name of the parameter for error messages

    Returns:
        List of parsed JSON objects or None if json_strings is None

    Raises:
        RetryableToolError: If JSON parsing fails for any string
    """
    if json_strings is None:
        return None

    try:
        return [json.loads(json_str) for json_str in json_strings]
    except json.JSONDecodeError as e:
        raise RetryableToolError(
            f"Invalid JSON in {parameter_name}: {e}",
            developer_message=f"Failed to parse JSON string list for parameter '{parameter_name}': {json_strings}. Error: {e}",
            additional_prompt_content=f"Please provide valid JSON strings for the {parameter_name} parameter. Each string must be valid JSON with proper escaping of quotes.",
        ) from e


def _infer_schema_from_docs(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer schema structure from a list of documents."""
    schema: dict[str, Any] = {}

    for doc in docs:
        _update_schema_with_doc(schema, doc)

    # Convert sets to lists for serialization
    for key in schema:
        if isinstance(schema[key]["types"], set):
            schema[key]["types"] = list(schema[key]["types"])

    return schema


def _update_schema_with_doc(schema: dict[str, Any], doc: dict[str, Any], prefix: str = "") -> None:
    """Recursively update schema with document structure."""
    for key, value in doc.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if full_key not in schema:
            schema[full_key] = {
                "types": set(),
                "sample_values": [],
                "null_count": 0,
                "total_count": 0,
            }

        schema[full_key]["total_count"] += 1

        if value is None:
            schema[full_key]["null_count"] += 1
            schema[full_key]["types"].add("null")
        else:
            value_type = type(value).__name__
            schema[full_key]["types"].add(value_type)

            # Store sample values (limit to 3 unique samples)
            if (
                len(schema[full_key]["sample_values"]) < 3
                and value not in schema[full_key]["sample_values"]
            ):
                schema[full_key]["sample_values"].append(value)

            # Handle nested objects
            if isinstance(value, dict):
                _update_schema_with_doc(schema, value, full_key)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Handle arrays of objects by sampling the first few
                for i, item in enumerate(value[:3]):  # Sample first 3 array items
                    if isinstance(item, dict):
                        _update_schema_with_doc(schema, item, f"{full_key}[{i}]")


def _serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format."""

    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            result[key] = _serialize_document(value)
        return result
    elif isinstance(doc, list):
        return [_serialize_document(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc