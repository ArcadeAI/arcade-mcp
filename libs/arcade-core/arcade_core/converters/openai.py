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

    items: "OpenAIFunctionParameterProperty"
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


def _add_null_to_type(schema: OpenAIFunctionParameterProperty) -> None:
    """Union a property's type with "null" so it may be omitted in strict mode.

    Strict mode lists every property in ``required``; an optional property is then
    expressed by allowing ``null`` rather than by leaving it out of ``required``. When the
    property is an enum, ``None`` is appended to the enum too: ``type`` and ``enum`` are
    independent assertions, so a null value must satisfy both.
    """
    param_type = schema.get("type")
    if isinstance(param_type, str):
        schema["type"] = [param_type, "null"]
    elif isinstance(param_type, list) and "null" not in param_type:
        schema["type"] = [*param_type, "null"]

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and None not in enum_values:
        schema["enum"] = [*enum_values, None]


def _build_object_schema(
    properties: dict[str, ValueSchema],
    required_keys: list[str] | None,
) -> OpenAIFunctionParameterProperty:
    """Build a strict-mode object schema from a structured type's fields.

    Strict mode requires ``additionalProperties: false`` on every object and every
    property listed in ``required``. Fields that are not actually required are unioned
    with ``null`` so the model may omit them. When ``required_keys`` is a list (a known
    shape, possibly empty) a field is required iff it appears there; when it is ``None``
    (an unknown shape) the field's ``nullable`` flag decides.
    """
    required_set = set(required_keys or [])
    field_schemas: dict[str, OpenAIFunctionParameterProperty] = {}

    for name, field_value_schema in properties.items():
        field_schema = _convert_value_schema_to_json_schema(field_value_schema)
        if field_value_schema.description:
            field_schema["description"] = field_value_schema.description

        if required_keys is None:
            is_required = not field_value_schema.nullable
        else:
            is_required = name in required_set
        if field_value_schema.nullable or not is_required:
            _add_null_to_type(field_schema)

        field_schemas[name] = field_schema

    return {
        "type": "object",
        "properties": field_schemas,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


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

    schema: OpenAIFunctionParameterProperty

    if value_schema.val_type == "array" and value_schema.inner_val_type:
        schema = {"type": "array"}
        if value_schema.inner_val_type == "json" and value_schema.inner_properties is not None:
            schema["items"] = _build_object_schema(
                value_schema.inner_properties, value_schema.inner_required_keys
            )
        else:
            items_schema: OpenAIFunctionParameterProperty = {
                "type": type_mapping[value_schema.inner_val_type]
            }
            # For arrays of scalars, enum applies to the items, not the array itself
            if value_schema.enum:
                items_schema["enum"] = value_schema.enum
            schema["items"] = items_schema
        return schema

    if value_schema.val_type == "json" and value_schema.properties is not None:
        return _build_object_schema(value_schema.properties, value_schema.required_keys)

    schema = {"type": type_mapping[value_schema.val_type]}
    if value_schema.enum:
        schema["enum"] = value_schema.enum
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

        # In strict mode every parameter is listed in `required`; optional ones are
        # expressed by allowing "null" rather than by omission.
        if not parameter.required:
            _add_null_to_type(param_schema)

        if parameter.description:
            param_schema["description"] = parameter.description
        properties[parameter.name] = param_schema

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
