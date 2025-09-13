from arcade_core.catalog import MaterializedTool
from arcade_core.schema import InputParameter, ValueSchema
from arcade_evals.models.openai.types import (
    OpenAIFunctionParameterProperty,
    OpenAIFunctionParameters,
    OpenAIFunctionSchema,
    OpenAIToolSchema,
)


def create_tool_schema(
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


def convert_materialized_tool_to_openai_schema(tool: MaterializedTool) -> OpenAIToolSchema:
    """Convert a MaterializedTool to OpenAI JsonToolSchema format."""
    name = tool.definition.fully_qualified_name.replace(".", "_")
    description = tool.description
    parameters_schema = convert_input_parameters_to_json_schema(tool.definition.input.parameters)
    return create_tool_schema(name, description, parameters_schema)


def convert_value_schema_to_json_schema(
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
        items_schema = {"type": type_mapping[value_schema.inner_val_type]}

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
            name: convert_value_schema_to_json_schema(nested_schema)
            for name, nested_schema in value_schema.properties.items()
        }

    return schema


def convert_input_parameters_to_json_schema(
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
        param_schema = convert_value_schema_to_json_schema(parameter.value_schema)

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
