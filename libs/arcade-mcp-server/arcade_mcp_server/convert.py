import base64
import json
import logging
from enum import Enum
from typing import Any, get_args, get_origin

from arcade_core.catalog import MaterializedTool
from arcade_core.schema import ToolDefinition

from arcade_mcp_server.types import MCPContent, MCPTool, TextContent, ToolAnnotations

logger = logging.getLogger("arcade.mcp")


def create_mcp_tool(tool: MaterializedTool) -> MCPTool | None:
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
        name = fully_qualified_name.replace(".", "_") if fully_qualified_name else tool_name

        description = getattr(tool.definition, "description", "No description available")

        # Check for deprecation
        deprecation_msg = getattr(tool.definition, "deprecation_message", None)
        if deprecation_msg:
            description = f"[DEPRECATED: {deprecation_msg}] {description}"

        # Build input schema using authoritative ToolDefinition when available
        try:
            if getattr(tool.definition, "input", None):
                input_schema = build_input_schema_from_definition(tool.definition)
            else:
                # Fallback to input_model if definition input is missing
                input_schema = _build_input_schema_from_model(tool)
        except Exception:
            logger.exception("Error while constructing input schema; proceeding with empty schema")
            input_schema = {"type": "object", "properties": {}, "additionalProperties": False}

        # Create output schema if available
        output_schema = None
        try:
            if hasattr(tool.definition, "output") and tool.definition.output:
                output_def = tool.definition.output
                if getattr(output_def, "value_schema", None):
                    output_schema = _build_value_schema_json(output_def.value_schema)
        except Exception:
            logger.exception("Error while constructing output schema; omitting output schema")

        requirements = tool.definition.requirements

        # Build annotations using model for stricter typing
        annotations = ToolAnnotations(
            readOnlyHint=not (
                requirements.authorization or requirements.secrets or requirements.metadata
            ),
            openWorldHint=requirements.authorization is not None,
        )

        # Build meta with requirements if any exist
        meta = None
        if requirements.authorization or requirements.secrets or requirements.metadata:
            meta = {"arcade_requirements": requirements.model_dump(exclude_none=True)}

        # Instantiate MCPTool model to ensure shape correctness
        return MCPTool(
            name=name,
            title=tool.definition.toolkit.name + "_" + tool_name,
            description=str(description),
            inputSchema=input_schema,
            outputSchema=output_schema if output_schema else None,
            annotations=annotations,
            _meta=meta,
        )

    except Exception:
        logger.exception(
            f"Error creating MCP tool definition for {getattr(tool, 'name', str(tool))}"
        )
        try:
            # Fallback minimal tool to avoid None in callers
            fallback_name = getattr(tool.definition, "fully_qualified_name", "unknown").replace(
                ".", "_"
            )
            return MCPTool(
                name=fallback_name,
                title=fallback_name,
                description="",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
            )
        except Exception:
            return None


def convert_to_mcp_content(value: Any) -> list[MCPContent]:
    """
    Convert a Python value to MCP-compatible content.
    """
    if value is None:
        return []

    if isinstance(value, (str, bool, int, float)):
        return [TextContent(type="text", text=str(value))]

    if isinstance(value, (dict, list)):
        try:
            return [TextContent(type="text", text=json.dumps(value, ensure_ascii=False))]
        except Exception as exc:
            raise ValueError("Failed to serialize value to JSON for MCP content") from exc

    if isinstance(value, (bytes, bytearray, memoryview)):
        # Encode bytes as base64 text so it can be transmitted safely
        b = bytes(value)
        encoded = base64.b64encode(b).decode("ascii")
        return [TextContent(type="text", text=encoded)]

    # Default fallback
    return [TextContent(type="text", text=str(value))]


def convert_content_to_structured_content(value: Any) -> dict[str, Any] | None:
    """
    Convert a Python value to MCP-compatible structured content (JSON object).

    According to the MCP specification, structuredContent should be a JSON object
    that represents the structured result of the tool call.

    Args:
        value: The value to convert to structured content

    Returns:
        A dictionary representing the structured content, or None if value is None
    """
    if value is None:
        return None

    if isinstance(value, dict):
        # Already a dictionary - use as-is
        return value
    elif isinstance(value, list):
        # List - wrap in a result object
        return {"result": value}
    elif isinstance(value, (str, int, float, bool)):
        # Primitive types - wrap in a result object
        return {"result": value}
    else:
        # For other types, convert to string and wrap
        return {"result": str(value)}


def _map_type_to_json_schema_type(val_type: str | None) -> str:
    """
    Map Arcade value types to JSON schema types.

    Args:
        val_type: The Arcade value type as a string.

    Returns:
        The corresponding JSON schema type as a string.
    """
    if val_type is None:
        return "string"

    mapping: dict[str, str] = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }
    return mapping.get(val_type, "string")


def build_input_schema_from_definition(definition: ToolDefinition) -> dict[str, Any]:
    """Build a JSON schema object for tool inputs from a ToolDefinition.

    Returns a dict with keys: type, properties, and optional required.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    if getattr(definition, "input", None) and getattr(definition.input, "parameters", None):
        for param in definition.input.parameters:
            val_schema = getattr(param, "value_schema", None)
            schema: dict[str, Any] = {
                "type": _map_type_to_json_schema_type(getattr(val_schema, "val_type", None)),
            }

            if getattr(param, "description", None):
                schema["description"] = param.description

            if val_schema and getattr(val_schema, "enum", None):
                schema["enum"] = list(val_schema.enum)

            if (
                val_schema
                and val_schema.val_type == "array"
                and getattr(val_schema, "inner_val_type", None)
            ):
                schema["items"] = {"type": _map_type_to_json_schema_type(val_schema.inner_val_type)}

            if (
                val_schema
                and val_schema.val_type == "json"
                and getattr(val_schema, "properties", None)
            ):
                schema["type"] = "object"
                schema["properties"] = {}
                for prop_name, prop_schema in val_schema.properties.items():
                    schema["properties"][prop_name] = {
                        "type": _map_type_to_json_schema_type(
                            getattr(prop_schema, "val_type", None)
                        ),
                    }
                    if getattr(prop_schema, "description", None):
                        schema["properties"][prop_name]["description"] = prop_schema.description

            properties[param.name] = schema
            if getattr(param, "required", False):
                required.append(param.name)

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        input_schema["required"] = required
    return input_schema


def _build_input_schema_from_model(tool: MaterializedTool) -> dict[str, Any]:
    """Build input schema from a tool's input_model as a fallback."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    context_param_name = None
    tool_input = getattr(tool.definition, "input", None)
    if tool_input is not None:
        context_param_name = getattr(tool_input, "tool_context_parameter_name", None)

    if (
        hasattr(tool, "input_model")
        and tool.input_model is not None
        and hasattr(tool.input_model, "model_fields")
    ):
        for field_name, field in tool.input_model.model_fields.items():
            if field_name == context_param_name:
                continue

            field_type = getattr(field, "annotation", None)
            field_type_name = "string"  # default

            if field_type is int:
                field_type_name = "integer"
            elif field_type is float:
                field_type_name = "number"
            elif field_type is bool:
                field_type_name = "boolean"
            elif field_type is list or (getattr(field_type, "__origin__", None) is list):
                field_type_name = "array"
            elif field_type is dict or (getattr(field_type, "__origin__", None) is dict):
                field_type_name = "object"

            field_description = getattr(field, "description", None) or f"Parameter: {field_name}"

            param_def: dict[str, Any] = {
                "type": field_type_name,
                "description": field_description,
            }

            # Enum support: Enum classes or typing.Annotated[...] with Enum
            enum_type = None
            ann = getattr(field, "annotation", None)
            if ann is not None:
                origin = get_origin(ann)
                args = get_args(ann)
                # typing.Annotated[Enum, ...]
                if origin is not None and args:
                    for arg in args:
                        if isinstance(arg, type) and issubclass(arg, Enum):
                            enum_type = arg
                            break
                elif isinstance(ann, type) and issubclass(ann, Enum):
                    enum_type = ann
            if enum_type is not None:
                param_def["enum"] = [e.value for e in enum_type]

            # Literal[...] support for enum-like constraints
            if ann is not None and get_origin(ann) is None:
                pass  # no-op, handled above
            elif ann is not None and get_origin(ann) is Any:
                pass
            else:
                if get_origin(ann) is None:
                    ...

            # Attempt to infer inner list item types for list[T]
            if field_type_name == "array":
                inner = None
                if get_origin(field_type) is list and get_args(field_type):
                    inner = get_args(field_type)[0]
                if inner is int:
                    param_def["items"] = {"type": "integer"}
                elif inner is float:
                    param_def["items"] = {"type": "number"}
                elif inner is bool:
                    param_def["items"] = {"type": "boolean"}
                elif inner is str:
                    param_def["items"] = {"type": "string"}

            properties[field_name] = param_def

            # Required detection with multiple strategies
            is_required_attr = getattr(field, "is_required", None)
            try:
                if callable(is_required_attr):
                    if is_required_attr():
                        required.append(field_name)
                elif isinstance(is_required_attr, bool) and is_required_attr:
                    required.append(field_name)
                else:
                    has_default = getattr(field, "default", None) is not None
                    has_factory = getattr(field, "default_factory", None) is not None
                    if not (has_default or has_factory):
                        required.append(field_name)
            except Exception:
                logger.debug(
                    f"Could not determine if field {field_name} is required, assuming optional"
                )

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        input_schema["required"] = required
    return input_schema


def _build_value_schema_json(value_schema: Any) -> dict[str, Any]:
    """Map a ValueSchema to a JSON schema fragment for outputSchema."""
    schema: dict[str, Any] = {
        "type": _map_type_to_json_schema_type(getattr(value_schema, "val_type", None)),
    }
    if getattr(value_schema, "enum", None):
        schema["enum"] = list(value_schema.enum)
    if getattr(value_schema, "val_type", None) == "array" and getattr(
        value_schema, "inner_val_type", None
    ):
        schema["items"] = {"type": _map_type_to_json_schema_type(value_schema.inner_val_type)}
    if getattr(value_schema, "val_type", None) == "json" and getattr(
        value_schema, "properties", None
    ):
        schema["type"] = "object"
        schema["properties"] = {}
        for prop_name, prop_schema in value_schema.properties.items():
            schema["properties"][prop_name] = {
                "type": _map_type_to_json_schema_type(getattr(prop_schema, "val_type", None))
            }
            if getattr(prop_schema, "description", None):
                schema["properties"][prop_name]["description"] = prop_schema.description
    return schema
