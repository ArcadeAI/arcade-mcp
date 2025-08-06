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
        # Get the tool name from the definition
        tool_name = getattr(tool.definition, "name", "unknown")
        fully_qualified_name = getattr(tool.definition, "fully_qualified_name", None)

        # Use fully qualified name for MCP tool name (replacing dots with underscores)
        name = str(fully_qualified_name).replace(".", "_") if fully_qualified_name else tool_name

        description = getattr(tool.definition, "description", "No description available")

        # Check for deprecation
        deprecation_msg = getattr(tool.definition, "deprecation_message", None)
        if deprecation_msg:
            description = f"[DEPRECATED: {deprecation_msg}] {description}"

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

        # Create output schema if available
        output_schema = None
        if hasattr(tool.definition, "output") and tool.definition.output:
            output_def = tool.definition.output
            if output_def.value_schema:
                # Convert Arcade value schema to JSON schema
                output_schema = {
                    "type": "object",
                    "description": output_def.description or "Tool output",
                }
                # Note: Full value_schema conversion would require more complex mapping
                # For now, we indicate that the tool has structured output

        # Add annotations based on tool metadata and requirements
        annotations = {}

        # Use the raw tool name (in PascalCase) as the title
        annotations["title"] = tool_name

        # Add requirement-based hints
        if hasattr(tool.definition, "requirements") and tool.definition.requirements:
            reqs = tool.definition.requirements

            # If tool has no auth/secrets/metadata requirements, it's likely read-only
            has_requirements = bool(reqs.authorization or reqs.secrets or reqs.metadata)
            annotations["readOnlyHint"] = not has_requirements

            # Tools with auth requirements often interact with external systems
            if reqs.authorization:
                annotations["openWorldHint"] = True

        # Check for explicit metadata hints
        if hasattr(tool.definition, "metadata"):
            metadata = tool.definition.metadata or {}
            if "read_only" in metadata:
                annotations["readOnlyHint"] = metadata["read_only"]
            if "destructive" in metadata:
                annotations["destructiveHint"] = metadata["destructive"]
            if "idempotent" in metadata:
                annotations["idempotentHint"] = metadata["idempotent"]
            if "open_world" in metadata:
                annotations["openWorldHint"] = metadata["open_world"]

        # Create the final tool definition
        tool_def: MCPTool = {
            "name": name,
            "title": tool_name,  # Human-friendly name without toolkit prefix
            "description": str(description),
            "inputSchema": input_schema,
        }

        # Add output schema if available
        if output_schema:
            tool_def["outputSchema"] = output_schema

        # Only add annotations if we have any
        if annotations:
            tool_def["annotations"] = annotations

        # Add toolkit information to description if available
        if hasattr(tool.definition, "toolkit") and tool.definition.toolkit:
            toolkit = tool.definition.toolkit
            toolkit_info = f" (from {toolkit.name}"
            if toolkit.version:
                toolkit_info += f" v{toolkit.version}"
            toolkit_info += ")"
            tool_def["description"] += toolkit_info

        logger.debug(f"Created tool definition for {name}")
        return tool_def

    except Exception:
        logger.exception(
            f"Error creating MCP tool definition for {getattr(tool, 'name', str(tool))}"
        )
        return None


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
