from typing import Any

from arcadepy.types import ToolDefinition
from pydantic import BaseModel, Field, create_model

# Mapping of Arcade value types to Python types
TYPE_MAPPING = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "json": dict,
}


def get_python_type(val_type: str) -> Any:
    """Map Arcade value types to Python types.

    Args:
        val_type: The value type as a string.

    Returns:
        Corresponding Python type.
    """
    _type = TYPE_MAPPING.get(val_type)
    if _type is None:
        raise ValueError(f"Invalid value type: {val_type}")
    return _type


def tool_definition_to_pydantic_model(tool_def: ToolDefinition) -> type[BaseModel]:
    """Convert a ToolDefinition's inputs into a Pydantic BaseModel.

    Args:
        tool_def: The ToolDefinition object to convert.

    Returns:
        A Pydantic BaseModel class representing the tool's input schema.
    """
    try:
        fields: dict[str, Any] = {}
        for param in tool_def.input.parameters or []:
            param_type = get_python_type(param.value_schema.val_type)
            if param_type == list and param.value_schema.inner_val_type:  # noqa: E721
                inner_type: type[Any] = get_python_type(param.value_schema.inner_val_type)
                param_type = list[inner_type]  # type: ignore[valid-type]
            param_description = param.description or "No description provided."
            default = ... if param.required else None
            fields[param.name] = (
                param_type,
                Field(default=default, description=param_description),
            )
        return create_model(f"{tool_def.name}Args", **fields)
    except ValueError as e:
        raise ValueError(f"Error converting {tool_def.name} parameters into pydantic model: {e}")
