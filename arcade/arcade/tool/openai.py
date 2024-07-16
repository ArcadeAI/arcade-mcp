import json
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from arcade.tool.catalog import MaterializedTool

PYTHON_TO_JSON_TYPES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def python_type_to_json_type(python_type: type[Any]) -> dict[str, Any]:
    """
    Map Python types to JSON Schema types, including handling of
    complex types such as lists and dictionaries.
    """
    if hasattr(python_type, "__origin__"):
        origin = python_type.__origin__

        if origin is list:
            item_type = python_type_to_json_type(python_type.__args__[0])
            return {"type": "array", "items": item_type}
        elif origin is dict:
            value_type = python_type_to_json_type(python_type.__args__[1])
            return {"type": "object", "additionalProperties": value_type}

    elif issubclass(python_type, BaseModel):
        return model_to_json_schema(python_type)

    raise ValueError(f"Unsupported type: {python_type}")


def model_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    Convert a Pydantic model to a JSON schema.
    """
    properties = {}
    required = []
    for field_name, model_field in model.model_fields.items():
        # TODO: remove type ignore
        type_json = python_type_to_json_type(model_field.annotation)  # type: ignore[arg-type]
        if isinstance(type_json, dict):
            field_schema = type_json
        else:
            field_schema = {
                "type": type_json,
                "description": model_field.description or "",
            }
        if model_field.default not in [None, PydanticUndefined]:
            if isinstance(model_field.default, Enum):
                field_schema["default"] = model_field.default.value
            else:
                field_schema["default"] = model_field.default
        if model_field.is_required():
            required.append(field_name)
        properties[field_name] = field_schema
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def schema_to_openai_tool(tool: "MaterializedTool") -> str:
    """Convert an ToolDefinition object to a JSON schema string in the specified function format.

    Example output format:
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    }
    """
    input_model_schema = model_to_json_schema(tool.input_model)
    function_schema = {
        "type": "function",
        "function": {
            "name": tool.definition.name,
            "description": tool.definition.description,
            "parameters": input_model_schema,
        },
    }
    return json.dumps(function_schema, indent=2)
