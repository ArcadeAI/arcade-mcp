import json
from datetime import datetime
from typing import Any

from arcade_tdk.errors import RetryableToolError
from bson import ObjectId


def _validate_no_write_operations(obj: Any, parameter_name: str, path: str = "") -> None:
    """
    Recursively validate that an object doesn't contain MongoDB write operations.

    Args:
        obj: The object to validate
        parameter_name: Name of the parameter for error messages
        path: Current path in the object (for nested validation)

    Raises:
        RetryableToolError: If write operations are detected
    """
    # MongoDB write/update operators that should be blocked
    WRITE_OPERATORS = {
        # Update operators
        "$set",
        "$unset",
        "$inc",
        "$mul",
        "$rename",
        "$min",
        "$max",
        "$currentDate",
        "$addToSet",
        "$pop",
        "$pull",
        "$push",
        "$pullAll",
        "$each",
        "$slice",
        "$sort",
        "$position",
        "$bit",
        "$isolated",
        # Array update operators
        "$",
        "$[]",
        "$[<identifier>]",
        # Pipeline update operators
        "$addFields",
        "$replaceRoot",
        "$replaceWith",
        # Aggregation stages that can modify (in case they're misused)
        "$out",
        "$merge",
        # Other potentially dangerous operators
        "$where",  # Can execute JavaScript
    }

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # Special check for $where operator which can execute JavaScript (check this first)
            if key == "$where":
                raise RetryableToolError(
                    f"JavaScript execution operator '$where' not allowed in {parameter_name}",
                    developer_message=f"Found '$where' operator at path '{current_path}' in parameter '{parameter_name}'. JavaScript execution is not allowed for security reasons.",
                    additional_prompt_content=f"The {parameter_name} parameter cannot use the $where operator. Use other query operators instead.",
                )

            # Check if this key is a write operator
            if key in WRITE_OPERATORS:
                raise RetryableToolError(
                    f"Write operation '{key}' not allowed in {parameter_name}",
                    developer_message=f"Found write operation '{key}' at path '{current_path}' in parameter '{parameter_name}'. Only read operations are allowed.",
                    additional_prompt_content=f"The {parameter_name} parameter cannot contain write operations like '{key}'. Use only query/read operations such as $match, $gte, $lte, $in, $regex, etc.",
                )

            # Recursively validate nested objects
            _validate_no_write_operations(value, parameter_name, current_path)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            _validate_no_write_operations(item, parameter_name, current_path)


def _parse_json_parameter(
    json_string: str | None, parameter_name: str, validate_read_only: bool = True
) -> Any | None:
    """
    Parse a JSON string parameter with proper error handling and optional write operation validation.

    Args:
        json_string: The JSON string to parse (can be None)
        parameter_name: Name of the parameter for error messages
        validate_read_only: Whether to validate that no write operations are present

    Returns:
        Parsed JSON object or None if json_string is None

    Raises:
        RetryableToolError: If JSON parsing fails or write operations are detected
    """
    if json_string is None:
        return None

    try:
        parsed_obj = json.loads(json_string)

        # Validate that no write operations are present
        if validate_read_only and parsed_obj is not None:
            _validate_no_write_operations(parsed_obj, parameter_name)

    except json.JSONDecodeError as e:
        raise RetryableToolError(
            f"Invalid JSON in {parameter_name}: {e}",
            developer_message=f"Failed to parse JSON string for parameter '{parameter_name}': {json_string}. Error: {e}",
            additional_prompt_content=f"Please provide valid JSON for the {parameter_name} parameter. Check for proper escaping of quotes and valid JSON syntax.",
        ) from e
    else:
        return parsed_obj


def _validate_aggregation_pipeline(pipeline: list[Any], parameter_name: str) -> None:
    """
    Validate that an aggregation pipeline only contains read operations.

    Args:
        pipeline: The aggregation pipeline to validate
        parameter_name: Name of the parameter for error messages

    Raises:
        RetryableToolError: If write operations are detected in the pipeline
    """
    # MongoDB aggregation stages that can modify data
    WRITE_STAGES = {
        "$out",
        "$merge",  # These stages write to collections
    }

    # Aggregation stages that are potentially dangerous
    DANGEROUS_STAGES = {
        "$where",  # Can execute JavaScript
    }

    for i, stage in enumerate(pipeline):
        if isinstance(stage, dict):
            for stage_name in stage:
                if stage_name in WRITE_STAGES:
                    raise RetryableToolError(
                        f"Write stage '{stage_name}' not allowed in {parameter_name}",
                        developer_message=f"Found write stage '{stage_name}' at pipeline index {i} in parameter '{parameter_name}'. Only read operations are allowed.",
                        additional_prompt_content=f"The {parameter_name} parameter cannot contain write stages like '{stage_name}'. Use only read stages such as $match, $group, $project, $sort, $limit, etc.",
                    )

                if stage_name in DANGEROUS_STAGES:
                    raise RetryableToolError(
                        f"Dangerous stage '{stage_name}' not allowed in {parameter_name}",
                        developer_message=f"Found dangerous stage '{stage_name}' at pipeline index {i} in parameter '{parameter_name}'. JavaScript execution is not allowed for security reasons.",
                        additional_prompt_content=f"The {parameter_name} parameter cannot use the {stage_name} stage. Use other aggregation stages instead.",
                    )

                # Also validate the stage content for write operations
                _validate_no_write_operations(
                    stage[stage_name], f"{parameter_name}[{i}].{stage_name}"
                )


def _parse_json_list_parameter(
    json_strings: list[str] | None, parameter_name: str, validate_read_only: bool = True
) -> list[Any] | None:
    """
    Parse a list of JSON strings with proper error handling and optional write operation validation.

    Args:
        json_strings: List of JSON strings to parse (can be None)
        parameter_name: Name of the parameter for error messages
        validate_read_only: Whether to validate that no write operations are present

    Returns:
        List of parsed JSON objects or None if json_strings is None

    Raises:
        RetryableToolError: If JSON parsing fails for any string or write operations are detected
    """
    if json_strings is None:
        return None

    try:
        parsed_list = [json.loads(json_str) for json_str in json_strings]

        # Validate that no write operations are present
        if validate_read_only and parsed_list is not None:
            # Special handling for pipeline parameters
            if parameter_name == "pipeline":
                _validate_aggregation_pipeline(parsed_list, parameter_name)
            else:
                # For non-pipeline lists, validate each item
                for i, item in enumerate(parsed_list):
                    _validate_no_write_operations(item, f"{parameter_name}[{i}]")

    except json.JSONDecodeError as e:
        raise RetryableToolError(
            f"Invalid JSON in {parameter_name}: {e}",
            developer_message=f"Failed to parse JSON string list for parameter '{parameter_name}': {json_strings}. Error: {e}",
            additional_prompt_content=f"Please provide valid JSON strings for the {parameter_name} parameter. Each string must be valid JSON with proper escaping of quotes.",
        ) from e
    else:
        return parsed_list


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
