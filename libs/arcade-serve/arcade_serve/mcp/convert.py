import json
import logging
from enum import Enum
from typing import Any

from arcade_core.catalog import MaterializedTool

# Type aliases for MCP types
MCPTool = dict[str, Any]
MCPTextContent = dict[str, Any]
MCPImageContent = dict[str, Any]
MCPEmbeddedResource = dict[str, Any]
MCPContent = MCPTextContent | MCPImageContent | MCPEmbeddedResource

logger = logging.getLogger("arcade.mcp")


def create_mcp_tool(tool: MaterializedTool) -> dict[str, Any] | None:  # noqa: C901
    """
    Create an MCP-compatible tool definition from an Arcade tool.

    Args:
        tool: An Arcade tool object

    Returns:
        An MCP tool definition or None if the tool cannot be converted
    """
    try:
        name = getattr(tool.definition, "fully_qualified_name", None) or getattr(
            tool.definition, "name", "unknown"
        )
        description = getattr(tool.definition, "description", "No description available")

        # Extract parameters from the input model
        parameters = {}
        required = []

        if (
            hasattr(tool, "input_model")
            and tool.input_model is not None
            and hasattr(tool.input_model, "model_fields")
        ):
            for field_name, field in tool.input_model.model_fields.items():
                # Skip internal tool context parameters
                if field_name == getattr(
                    tool.definition.input, "tool_context_parameter_name", None
                ):
                    continue

                # Get field type information
                field_type = getattr(field, "annotation", None)
                field_type_name = "string"  # default

                # Safety check for field_type
                if field_type is int:
                    field_type_name = "integer"
                elif field_type is float:
                    field_type_name = "number"
                elif field_type is bool:
                    field_type_name = "boolean"
                elif field_type is list or str(field_type).startswith("list["):
                    field_type_name = "array"
                elif field_type is dict or str(field_type).startswith("dict["):
                    field_type_name = "object"

                # Get description with fallback
                field_description = getattr(field, "description", None)
                if not field_description:
                    field_description = f"Parameter: {field_name}"

                # Create parameter definition
                param_def = {
                    "type": field_type_name,
                    "description": field_description,
                }

                # Enum support: if the field annotation is an Enum, add allowed values
                enum_type = None
                if hasattr(field, "annotation"):
                    ann = field.annotation
                    # Handle typing.Annotated[Enum, ...]
                    if getattr(ann, "__origin__", None) is not None and hasattr(ann, "__args__"):
                        for arg in ann.__args__:  # type: ignore[union-attr]
                            if isinstance(arg, type) and issubclass(arg, Enum):
                                enum_type = arg
                                break
                    elif isinstance(ann, type) and issubclass(ann, Enum):
                        enum_type = ann
                if enum_type is not None:
                    param_def["enum"] = [e.value for e in enum_type]

                parameters[field_name] = param_def

                # In Pydantic v2, check if field is required based on default value
                try:
                    if field.is_required():
                        required.append(field_name)
                except (AttributeError, TypeError):
                    # Fallback if is_required() doesn't exist or fails
                    try:
                        has_default = getattr(field, "default", None) is not None
                        has_factory = getattr(field, "default_factory", None) is not None
                        if not (has_default or has_factory):
                            required.append(field_name)
                    except Exception:
                        # Ultimate fallback - assume required if we can't determine
                        logger.debug(
                            f"Could not determine if field {field_name} is required, assuming optional"
                        )

        # Create the input schema with explicit properties and required fields
        input_schema = {
            "type": "object",
            "properties": parameters,
        }

        # Only include required field if we have required parameters
        if required:
            input_schema["required"] = required

        # Add annotations based on tool metadata
        annotations = {}

        # Use tool name as title if available
        annotations["title"] = getattr(tool.definition, "title", str(name).replace(".", "_"))

        # Determine hints based on tool properties
        if hasattr(tool.definition, "metadata"):
            metadata = tool.definition.metadata or {}
            annotations["readOnlyHint"] = metadata.get("read_only", False)
            annotations["destructiveHint"] = metadata.get("destructive", False)
            annotations["idempotentHint"] = metadata.get("idempotent", True)
            annotations["openWorldHint"] = metadata.get("open_world", False)

        # Create the final tool definition
        tool_def: MCPTool = {
            "name": str(name).replace(".", "_"),
            "description": str(description),
            "inputSchema": input_schema,
            "annotations": annotations,
        }

        logger.debug(f"Created tool definition for {name}")

    except Exception:
        logger.exception(
            f"Error creating MCP tool definition for {getattr(tool, 'name', str(tool))}"
        )
        return None
    return tool_def


def convert_to_mcp_content(value: Any) -> list[dict[str, Any]]:
    """
    Convert a Python value to MCP-compatible content.
    """
    if value is None:
        return []

    if isinstance(value, (str, bool, int, float)):
        return [{"type": "text", "text": str(value)}]

    if isinstance(value, (dict, list)):
        return [{"type": "text", "text": json.dumps(value)}]

    # Default fallback
    return [{"type": "text", "text": str(value)}]


def _map_type_to_json_schema_type(val_type: str) -> str:
    """
    Map Arcade value types to JSON schema types.

    Args:
        val_type: The Arcade value type as a string.

    Returns:
        The corresponding JSON schema type as a string.
    """
    mapping: dict[str, str] = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }
    return mapping.get(val_type, "string")
