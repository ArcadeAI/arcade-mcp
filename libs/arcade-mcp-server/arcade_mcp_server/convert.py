import base64
import json
import logging
from typing import Any

from arcade_core.catalog import MaterializedTool
from arcade_core.schema import ToolDefinition

from arcade_mcp_server.types import MCPContent, MCPTool, TextContent, ToolAnnotations

logger = logging.getLogger("arcade.mcp")


def _build_arcade_meta(definition: ToolDefinition) -> dict[str, Any] | None:
    """Build the _meta.arcade structure from a tool definition.

    The structure of _meta.arcade mirrors Arcade format when possible.
    """
    arcade_meta: dict[str, Any] = {}

    requirements = definition.requirements
    if requirements.authorization or requirements.secrets or requirements.metadata:
        arcade_meta["requirements"] = requirements.model_dump(exclude_none=True)

    tool_metadata = definition.metadata
    if tool_metadata:
        metadata_dump = tool_metadata.model_dump(mode="json", exclude_none=True)
        if metadata_dump:
            arcade_meta["metadata"] = metadata_dump

    return arcade_meta if arcade_meta else None


def create_mcp_tool(materialized_tool: MaterializedTool) -> MCPTool:
    """
    Create an MCP-compatible tool definition from a MaterializedTool.

    Computes MCP annotations from tool metadata behavior fields and builds
    the ``_meta.arcade`` structure with requirements and metadata.

    Args:
        materialized_tool: A materialized Arcade tool

    Returns:
        An MCP tool definition
    """
    definition = materialized_tool.definition
    name = definition.fully_qualified_name.replace(".", "_")

    # Build the tool's description
    description = definition.description
    deprecation_msg = getattr(definition, "deprecation_message", None)
    if deprecation_msg:
        description = f"[DEPRECATED: {deprecation_msg}] {description}"

    # Build the tool's output schema
    # MCP spec requires outputSchema.type to be "object"
    output_schema = None
    if hasattr(definition, "output") and definition.output:
        output_def = definition.output
        if getattr(output_def, "value_schema", None):
            # _build_value_schema_json always returns {"type": "object", ...}
            # (it wraps non-object types in a result property internally)
            output_schema = _build_value_schema_json(output_def.value_schema)

    # Build MCP tool annotations from metadata behavior fields
    title = getattr(materialized_tool.tool, "__tool_name__", definition.name)
    tool_metadata = definition.metadata
    if tool_metadata and tool_metadata.behavior:
        behavior = tool_metadata.behavior
        annotations = ToolAnnotations(
            title=title,
            readOnlyHint=behavior.read_only,
            destructiveHint=behavior.destructive,
            idempotentHint=behavior.idempotent,
            openWorldHint=behavior.open_world,
        )
    else:
        annotations = ToolAnnotations(title=title)

    # Build _meta.arcade structure
    arcade_meta = _build_arcade_meta(definition)
    meta = {"arcade": arcade_meta} if arcade_meta else None

    return MCPTool(
        name=name,
        title=title,
        description=str(description),
        inputSchema=build_input_schema_from_definition(definition),
        outputSchema=output_schema if output_schema else None,
        annotations=annotations,
        _meta=meta,
    )


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
            schema = _value_schema_to_json_schema(val_schema) if val_schema else {"type": "string"}

            if getattr(param, "description", None):
                schema["description"] = param.description

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


def _build_value_schema_json(value_schema: Any) -> dict[str, Any]:
    """Map a ValueSchema to a JSON Schema ``outputSchema``.

    Per the MCP specification, ``outputSchema.type`` MUST be ``"object"``
    because ``structuredContent`` is always a JSON object.

    * **object** return types (``val_type == "json"``) are emitted directly
      as ``{"type": "object", "properties": {…}}``.
    * All other return types (primitives, arrays) are wrapped in
      ``{"type": "object", "properties": {"result": <inner>}}`` to mirror
      the wrapping performed at runtime by
      :func:`convert_content_to_structured_content`.
    """
    inner_schema = _value_schema_to_json_schema(value_schema)

    # Object return types are already top-level objects, emit directly.
    if inner_schema.get("type") == "object":
        return inner_schema

    # Primitives/arrays must be wrapped so outputSchema.type is "object" per MCP spec.
    return {
        "type": "object",
        "properties": {
            "result": inner_schema,
        },
    }


def _value_schema_to_json_schema(value_schema: Any) -> dict[str, Any]:
    """Convert a ValueSchema to a JSON Schema dict without top-level object wrapping.

    Recursively expands nested object (json) types into their sub-schemas.
    """
    val_type = getattr(value_schema, "val_type", None)

    if val_type == "json":
        schema: dict[str, Any] = {"type": "object"}
        if getattr(value_schema, "enum", None):
            schema["enum"] = list(value_schema.enum)
        if getattr(value_schema, "properties", None):
            schema["properties"] = {}
            for prop_name, prop_schema in value_schema.properties.items():
                schema["properties"][prop_name] = _value_schema_to_json_schema(prop_schema)
                if getattr(prop_schema, "description", None):
                    schema["properties"][prop_name]["description"] = prop_schema.description
        return schema

    schema = {"type": _map_type_to_json_schema_type(val_type)}
    if getattr(value_schema, "enum", None):
        schema["enum"] = list(value_schema.enum)
    if val_type == "array" and getattr(value_schema, "inner_val_type", None):
        inner_type = value_schema.inner_val_type
        items_schema: dict[str, Any] = {"type": _map_type_to_json_schema_type(inner_type)}
        if inner_type == "json" and getattr(value_schema, "inner_properties", None):
            items_schema["properties"] = {}
            for prop_name, prop_schema in value_schema.inner_properties.items():
                items_schema["properties"][prop_name] = _value_schema_to_json_schema(prop_schema)
                if getattr(prop_schema, "description", None):
                    items_schema["properties"][prop_name]["description"] = prop_schema.description
        schema["items"] = items_schema
    return schema
