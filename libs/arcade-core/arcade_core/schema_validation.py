"""Schema restrictions shared by worker and MCP elicitation authoring."""

from typing import Any


class UnsupportedSchemaDialectError(ValueError):
    """The declared JSON Schema dialect is unsupported."""


# Accepted JSON Schema 2020-12 dialect URIs
_ACCEPTED_SCHEMA_DIALECTS: set[str] = {
    "https://json-schema.org/draft/2020-12/schema",
    "https://json-schema.org/draft/2020-12/schema#",
    "http://json-schema.org/draft/2020-12/schema",
    "http://json-schema.org/draft/2020-12/schema#",
    "https://json-schema.org/2025-11-25/2020-12/schema",
}


def validate_schema_dialect(schema: dict[str, Any]) -> None:
    """Validate that a JSON Schema uses a supported dialect (2020-12).

    If ``$schema`` is absent, the schema is treated as 2020-12 (valid).
    If ``$schema`` is present and matches a recognized 2020-12 URI, it is
    valid. Otherwise, raises :class:`UnsupportedSchemaDialectError`.
    """
    dollar_schema = schema.get("$schema")
    if dollar_schema is None:
        return  # No $schema -> default to 2020-12 (valid)
    if dollar_schema in _ACCEPTED_SCHEMA_DIALECTS:
        return
    raise UnsupportedSchemaDialectError(
        f"Unsupported JSON Schema dialect: {dollar_schema}. Only JSON Schema 2020-12 is supported."
    )


def validate_elicitation_schema(schema: dict[str, Any]) -> None:
    """Validate that the schema conforms to MCP elicitation restrictions."""
    if not isinstance(schema, dict):
        raise TypeError("Schema must be a dictionary")

    # Enforce the MCP-required JSON Schema 2020-12 dialect.
    validate_schema_dialect(schema)

    if schema.get("type") != "object":
        raise ValueError("Schema must have type 'object'")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise TypeError("Schema properties must be a dictionary")

    # Validate each property
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            raise TypeError(f"Property '{prop_name}' schema must be a dictionary")

        prop_type = prop_schema.get("type")

        # Allow "array" type for multi-select enum schemas (MCP 2025-11-25)
        # Allow properties WITHOUT an explicit type but WITH enum / oneOf
        # (SEP-1330 enum variants: legacy ``enum``+``enumNames`` and
        # ``oneOf``-titled selects). Any other type value must be a
        # supported primitive -- the enum/oneOf bypass previously
        # whitelisted invalid types like ``"object"`` as long as one of
        # those keys was present.
        has_enum = "enum" in prop_schema
        has_one_of = "oneOf" in prop_schema
        if prop_type == "array":
            # Array properties are allowed ONLY as a multi-select enum
            # shape. The three supported variants, per the MCP 2025-11-25
            # enum schema family, are:
            #   - MultiSelectEnumSchema         -> items.enum
            #   - UntitledMultiSelectEnumSchema -> items.oneOf (untitled)
            #   - TitledMultiSelectEnumSchema   -> items.anyOf (titled)
            # A plain string/number array is NOT a valid elicitation input.
            items = prop_schema.get("items")
            items_ok = isinstance(items, dict) and (
                "enum" in items or "oneOf" in items or "anyOf" in items
            )
            if not items_ok:
                raise ValueError(
                    f"Property '{prop_name}' is an array but its items do "
                    f"not declare enum/oneOf/anyOf. Arrays are only allowed "
                    f"as multi-select enums in elicitation schemas."
                )
        elif prop_type is None:
            # Untyped properties are OK only when enum/oneOf provides
            # the value set.
            if not (has_enum or has_one_of):
                raise ValueError(
                    f"Property '{prop_name}' has no type and no enum/oneOf. "
                    f"Provide a type or an enum/oneOf variant."
                )
        elif prop_type not in ["string", "number", "integer", "boolean"]:
            raise ValueError(
                f"Property '{prop_name}' has unsupported type '{prop_type}'. "
                f"Only primitive types and array (for multi-select enum) are allowed."
            )

        # Validate string formats
        if prop_type == "string" and "format" in prop_schema:
            allowed_formats = ["email", "uri", "date", "date-time"]
            if prop_schema["format"] not in allowed_formats:
                raise ValueError(
                    f"Property '{prop_name}' has unsupported format '{prop_schema['format']}'. Allowed: {allowed_formats}"
                )
