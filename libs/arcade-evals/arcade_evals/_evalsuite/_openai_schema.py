"""OpenAI tool schema conversion (internal).

Converts MCP-style tool schemas to OpenAI's tool format with strict mode support.

OpenAI strict mode requirements:
- additionalProperties: false at all object levels
- properties and required present on all object schemas
- required includes ALL properties (optional params use null union types)
- Unsupported JSON Schema keywords are stripped
"""

from __future__ import annotations

import copy
from typing import Any

# Maximum recursion depth to prevent infinite loops in circular schema references
_MAX_SCHEMA_DEPTH = 50

# Keywords not supported by OpenAI strict mode that should be stripped
_UNSUPPORTED_STRICT_MODE_KEYWORDS = frozenset({
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "default",
    "nullable",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
})


class SchemaConversionError(Exception):
    """Raised when schema conversion fails."""


def convert_to_strict_mode_schema(parameters: dict[str, Any]) -> dict[str, Any]:
    """
    Convert an input JSON schema (MCP `inputSchema`) to OpenAI strict mode format.

    OpenAI strict mode requires:
    - additionalProperties: false at all object levels
    - properties and required present on all object schemas
    - required includes ALL properties
    - optional params become union types with null (e.g., ["string", "null"])
    - unsupported JSON Schema keywords stripped
    """
    result = copy.deepcopy(parameters)
    strict_schema = _apply_strict_mode_recursive(result, depth=0)
    return {
        "type": "object",
        "properties": strict_schema.get("properties", {}),
        "required": strict_schema.get("required", []),
        "additionalProperties": False,
    }


def _apply_strict_mode_recursive(schema: dict[str, Any], *, depth: int = 0) -> dict[str, Any]:
    if depth > _MAX_SCHEMA_DEPTH:
        raise SchemaConversionError(
            f"Schema nesting exceeds maximum depth of {_MAX_SCHEMA_DEPTH}. "
            "This may indicate a circular reference in the schema."
        )

    # Strip unsupported keywords that OpenAI strict mode doesn't allow
    for keyword in _UNSUPPORTED_STRICT_MODE_KEYWORDS:
        schema.pop(keyword, None)

    # OpenAI strict mode enum handling:
    # 1. OpenAI requires enum values to be strings
    # 2. OpenAI validates that enum values match the declared type
    # 3. When we convert enum values to strings, we must also change the type to "string"
    #
    # Example: {"type": "integer", "enum": [0, 1, 2]} becomes {"type": "string", "enum": ["0", "1", "2"]}
    # Example: {"type": ["integer", "null"], "enum": [0, 1]} becomes {"type": ["string", "null"], "enum": ["0", "1"]}
    #
    # Without this fix, OpenAI returns: "enum value 0 does not validate against {'type': ['integer', 'null']}"
    if "enum" in schema:
        schema["enum"] = [str(v) for v in schema["enum"]]
        # Change type to string to match the stringified enum values
        current_type = schema.get("type")
        if current_type and current_type != "string":
            if isinstance(current_type, str):
                schema["type"] = "string"
            elif isinstance(current_type, list) and "string" not in current_type:
                # Replace non-string types with string, preserve null if present
                has_null = "null" in current_type
                if has_null:
                    schema["type"] = ["string", "null"]
                else:
                    # Single type without null should be simplified to string
                    schema["type"] = "string"

    schema_type = schema.get("type")

    if schema_type == "object":
        schema["additionalProperties"] = False
        schema.setdefault("properties", {})

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        new_properties: dict[str, Any] = {}
        all_param_names: list[str] = []

        for param_name, param_schema in properties.items():
            if not isinstance(param_schema, dict):
                new_properties[param_name] = param_schema
                all_param_names.append(param_name)
                continue

            processed_schema = _apply_strict_mode_recursive(param_schema, depth=depth + 1)

            # Optional param: add null to type union
            if param_name not in required:
                param_type = processed_schema.get("type")
                if isinstance(param_type, str):
                    processed_schema["type"] = [param_type, "null"]
                elif isinstance(param_type, list) and "null" not in param_type:
                    processed_schema["type"] = [*param_type, "null"]

            new_properties[param_name] = processed_schema
            all_param_names.append(param_name)

        schema["properties"] = new_properties
        schema["required"] = all_param_names

    elif schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            schema["items"] = _apply_strict_mode_recursive(items, depth=depth + 1)

    for combiner in ("anyOf", "oneOf", "allOf"):
        if combiner in schema:
            schema[combiner] = [
                _apply_strict_mode_recursive(option, depth=depth + 1)
                if isinstance(option, dict)
                else option
                for option in schema[combiner]
            ]

    return schema
