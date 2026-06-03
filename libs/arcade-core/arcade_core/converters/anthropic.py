"""Converter for converting Arcade ToolDefinition to Anthropic tool schema."""

from typing import Any, TypedDict

from arcade_core.catalog import MaterializedTool
from arcade_core.converters.utils import normalize_tool_name
from arcade_core.schema import InputParameter, ValueSchema

# ----------------------------------------------------------------------------
# Type definitions for JSON tool schemas used by Anthropic APIs.
# Defines the proper types for tool schemas to ensure
# compatibility with Anthropic's Messages API tool use feature.
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
# ----------------------------------------------------------------------------


class AnthropicInputSchemaProperty(TypedDict, total=False):
    """Type definition for a property within Anthropic input schema."""

    type: str | list[str]
    """The JSON Schema type(s) for this property. A list expresses a union (e.g. ["string", "null"])."""

    description: str
    """Description of the property."""

    enum: list[Any]
    """Allowed values for enum properties."""

    items: "AnthropicInputSchemaProperty"
    """Schema for array items when type is 'array'."""

    properties: dict[str, "AnthropicInputSchemaProperty"]
    """Nested properties when type is 'object'."""

    required: list[str]
    """Required fields for nested objects."""


class AnthropicInputSchema(TypedDict, total=False):
    """Type definition for Anthropic tool input schema."""

    type: str
    """Must be 'object' for tool input schemas."""

    properties: dict[str, AnthropicInputSchemaProperty]
    """The properties of the tool input parameters."""

    required: list[str]
    """List of required parameter names."""


class AnthropicToolSchema(TypedDict, total=False):
    """
    Schema for a tool definition passed to Anthropic's `tools` parameter.

    Unlike OpenAI, Anthropic uses a flat structure without a wrapper object.
    The schema uses `input_schema` instead of `parameters`.
    """

    name: str
    """The name of the tool."""

    description: str
    """Description of what the tool does."""

    input_schema: AnthropicInputSchema
    """JSON Schema describing the tool's input parameters."""


# Type alias for a list of Anthropic tool schemas
AnthropicToolList = list[AnthropicToolSchema]


# ----------------------------------------------------------------------------
# Converters
# ----------------------------------------------------------------------------
def to_anthropic(tool: MaterializedTool) -> AnthropicToolSchema:
    """Convert a MaterializedTool to Anthropic tool schema format.

    Args:
        tool: The MaterializedTool to convert

    Returns:
        The Anthropic tool schema format (what is passed to the Anthropic API)
    """
    name = normalize_tool_name(tool.definition.fully_qualified_name)
    description = tool.description
    input_schema = _convert_input_parameters_to_json_schema(tool.definition.input.parameters)

    return _create_tool_schema(name, description, input_schema)


def _create_tool_schema(
    name: str, description: str, input_schema: AnthropicInputSchema
) -> AnthropicToolSchema:
    """Create a properly typed Anthropic tool schema.

    Args:
        name: The name of the tool
        description: Description of what the tool does
        input_schema: JSON schema for the tool input parameters

    Returns:
        A properly typed AnthropicToolSchema
    """
    tool: AnthropicToolSchema = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
    }

    return tool


def _add_null_to_type(schema: AnthropicInputSchemaProperty) -> None:
    """Union a field's type with "null" so a null value validates.

    A nested field can be required yet nullable (``str | None`` with no default): it must
    stay required while still accepting null. When the field is an enum, ``None`` is
    appended to the enum too, since ``type`` and ``enum`` are independent assertions.
    """
    field_type = schema.get("type")
    if isinstance(field_type, str):
        schema["type"] = [field_type, "null"]
    elif isinstance(field_type, list) and "null" not in field_type:
        schema["type"] = [*field_type, "null"]

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and None not in enum_values:
        schema["enum"] = [*enum_values, None]


def _build_object_schema(
    properties: dict[str, ValueSchema],
    required_keys: list[str] | None,
) -> AnthropicInputSchemaProperty:
    """Build an object schema from a structured type's fields.

    Anthropic uses standard JSON Schema: only the actually-required fields appear in
    ``required`` and there is no ``additionalProperties`` constraint. A nullable field
    unions ``null`` into its type so a null value validates even when the field is required.
    """
    field_schemas: dict[str, AnthropicInputSchemaProperty] = {}
    for name, field_value_schema in properties.items():
        field_schema = _convert_value_schema_to_json_schema(field_value_schema)
        if field_value_schema.description:
            field_schema["description"] = field_value_schema.description
        if field_value_schema.nullable:
            _add_null_to_type(field_schema)
        field_schemas[name] = field_schema

    schema: AnthropicInputSchemaProperty = {"type": "object", "properties": field_schemas}
    if required_keys:
        schema["required"] = list(required_keys)
    return schema


def _convert_value_schema_to_json_schema(
    value_schema: ValueSchema,
) -> AnthropicInputSchemaProperty:
    """Convert Arcade ValueSchema to JSON Schema format for Anthropic."""
    type_mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }

    schema: AnthropicInputSchemaProperty

    if value_schema.val_type == "array" and value_schema.inner_val_type:
        schema = {"type": "array"}
        if value_schema.inner_val_type == "json" and value_schema.inner_properties:
            schema["items"] = _build_object_schema(
                value_schema.inner_properties, value_schema.inner_required_keys
            )
        else:
            items_schema: AnthropicInputSchemaProperty = {
                "type": type_mapping[value_schema.inner_val_type]
            }
            # For arrays of scalars, enum applies to the items, not the array itself
            if value_schema.enum:
                items_schema["enum"] = value_schema.enum
            schema["items"] = items_schema
        return schema

    if value_schema.val_type == "json" and value_schema.properties:
        return _build_object_schema(value_schema.properties, value_schema.required_keys)

    schema = {"type": type_mapping[value_schema.val_type]}
    if value_schema.enum:
        schema["enum"] = value_schema.enum
    return schema


def _convert_input_parameters_to_json_schema(
    parameters: list[InputParameter],
) -> AnthropicInputSchema:
    """Convert list of InputParameter to JSON schema parameters object.

    Unlike OpenAI's strict mode, Anthropic uses standard JSON Schema:
    - Only actually required parameters are listed in 'required'
    - No need to add 'null' to optional parameter types
    - No 'additionalProperties: false' requirement
    """
    if not parameters:
        # Minimal JSON schema for a tool with no input parameters
        return {
            "type": "object",
            "properties": {},
        }

    properties: dict[str, AnthropicInputSchemaProperty] = {}
    required: list[str] = []

    for parameter in parameters:
        param_schema = _convert_value_schema_to_json_schema(parameter.value_schema)

        if parameter.description:
            param_schema["description"] = parameter.description

        properties[parameter.name] = param_schema

        # Only add actually required parameters to the required list
        if parameter.required:
            required.append(parameter.name)

    json_schema: AnthropicInputSchema = {
        "type": "object",
        "properties": properties,
    }

    # Only include 'required' if there are required parameters
    if required:
        json_schema["required"] = required

    return json_schema
