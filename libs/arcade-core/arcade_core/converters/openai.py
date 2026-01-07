"""Converter for converting Arcade ToolDefinition to OpenAI tool schema."""

from typing import Any, Literal, TypedDict

from arcade_core.catalog import MaterializedTool
from arcade_core.converters.utils import normalize_tool_name
from arcade_core.schema import InputParameter, ValueSchema

# ----------------------------------------------------------------------------
# Type definitions for JSON tool schemas used by OpenAI APIs.
# Defines the proper types for tool schemas to ensure
# compatibility with OpenAI's Responses and Chat Completions APIs.
# ----------------------------------------------------------------------------


class OpenAIFunctionParameterProperty(TypedDict, total=False):
    """Type definition for a property within OpenAI function parameters schema."""

    type: str | list[str]
    """The JSON Schema type(s) for this property. Can be a single type or list for unions (e.g., ["string", "null"])."""

    description: str
    """Description of the property."""

    enum: list[Any]
    """Allowed values for enum properties."""

    items: dict[str, Any]
    """Schema for array items when type is 'array'."""

    properties: dict[str, "OpenAIFunctionParameterProperty"]
    """Nested properties when type is 'object'."""

    required: list[str]
    """Required fields for nested objects."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class OpenAIFunctionParameters(TypedDict, total=False):
    """Type definition for OpenAI function parameters schema."""

    type: Literal["object"]
    """Must be 'object' for function parameters."""

    properties: dict[str, OpenAIFunctionParameterProperty]
    """The properties of the function parameters."""

    required: list[str]
    """List of required parameter names. In strict mode, all properties should be listed here."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class OpenAIFunctionSchema(TypedDict, total=False):
    """Type definition for a function tool parameter matching OpenAI's API."""

    name: str
    """The name of the function to call."""

    parameters: OpenAIFunctionParameters | None
    """A JSON schema object describing the parameters of the function."""

    strict: Literal[True]
    """Always enforce strict parameter validation. Default `true`."""

    description: str | None
    """A description of the function.
    Used by the model to determine whether or not to call the function.
    """


class OpenAIToolSchema(TypedDict):
    """
    Schema for a tool definition passed to OpenAI's `tools` parameter.
    A tool wraps a callable function for function-calling. Each tool
    includes a type (always 'function') and a `function` payload that
    specifies the callable via `OpenAIFunctionSchema`.
    """

    type: Literal["function"]
    """The type field, always 'function'."""

    function: OpenAIFunctionSchema
    """The function definition."""


# Type alias for a list of openai tool schemas
OpenAIToolList = list[OpenAIToolSchema]


# ----------------------------------------------------------------------------
# Converters
# ----------------------------------------------------------------------------
def to_openai(tool: MaterializedTool) -> OpenAIToolSchema:
    """Convert a MaterializedTool to OpenAI JsonToolSchema format.

    Args:
        tool: The MaterializedTool to convert
    Returns:
        The OpenAI JsonToolSchema format (what is passed to the OpenAI API)
    """
    name = normalize_tool_name(tool.definition.fully_qualified_name)
    description = tool.description
    parameters_schema = _convert_input_parameters_to_json_schema(tool.definition.input.parameters)
    return _create_tool_schema(name, description, parameters_schema)


def _create_tool_schema(
    name: str, description: str, parameters: OpenAIFunctionParameters
) -> OpenAIToolSchema:
    """Create a properly typed tool schema.
    Args:
        name: The name of the function
        description: Description of what the function does
        parameters: JSON schema for the function parameters
        strict: Whether to enforce strict validation (default: True for reliable function calls)
    Returns:
        A properly typed OpenAIToolSchema
    """

    function: OpenAIFunctionSchema = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "strict": True,
    }

    tool: OpenAIToolSchema = {
        "type": "function",
        "function": function,
    }

    return tool


def _convert_value_schema_to_json_schema(
    value_schema: ValueSchema,
) -> OpenAIFunctionParameterProperty:
    """Convert Arcade ValueSchema to JSON Schema format."""
    type_mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }

    schema: OpenAIFunctionParameterProperty = {"type": type_mapping[value_schema.val_type]}

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
) -> OpenAIFunctionParameters:
    """Convert list of InputParameter to JSON schema parameters object."""
    if not parameters:
        # Minimal JSON schema for a tool with no input parameters
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    properties = {}
    required = []

    for parameter in parameters:
        param_schema = _convert_value_schema_to_json_schema(parameter.value_schema)

        # For optional parameters in strict mode, we need to add "null" as a type option
        if not parameter.required:
            param_type = param_schema.get("type")
            if isinstance(param_type, str):
                # Convert single type to union with null
                param_schema["type"] = [param_type, "null"]
            elif isinstance(param_type, list) and "null" not in param_type:
                param_schema["type"] = [*param_type, "null"]

        if parameter.description:
            param_schema["description"] = parameter.description
        properties[parameter.name] = param_schema

        # In strict mode, all parameters (including optional ones) go in required array
        # Optional parameters are handled by adding "null" to their type
        required.append(parameter.name)

    json_schema: OpenAIFunctionParameters = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    if not required:
        del json_schema["required"]

    return json_schema
