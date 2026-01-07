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

    type: str
    """The JSON Schema type for this property."""

    description: str
    """Description of the property."""

    enum: list[Any]
    """Allowed values for enum properties."""

    items: dict[str, Any]
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

    schema: AnthropicInputSchemaProperty = {"type": type_mapping[value_schema.val_type]}

    if value_schema.val_type == "array" and value_schema.inner_val_type:
        items_schema: dict[str, Any] = {"type": type_mapping[value_schema.inner_val_type]}

        # For arrays, enum should be applied to the items, not the array itself
        if value_schema.enum:
            items_schema["enum"] = value_schema.enum

        schema["items"] = items_schema
    else:
        # Handle enum for non-array types
        if value_schema.enum:
            schema["enum"] = value_schema.enum

    # Handle object properties
    if value_schema.val_type == "json" and value_schema.properties:
        schema["properties"] = {
            name: _convert_value_schema_to_json_schema(nested_schema)
            for name, nested_schema in value_schema.properties.items()
        }

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
