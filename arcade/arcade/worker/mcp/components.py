import json
from typing import Any

from arcade.core.catalog import MaterializedTool

# Type aliases for MCP types
MCPTool = dict[str, Any]
MCPTextContent = dict[str, Any]
MCPImageContent = dict[str, Any]
MCPEmbeddedResource = dict[str, Any]
MCPContent = MCPTextContent | MCPImageContent | MCPEmbeddedResource


def create_mcp_tool(tool: MaterializedTool) -> MCPTool | None:
    """Convert an Arcade tool definition to MCP tool format

    Args:
        tool: The Arcade tool to convert

    Returns:
        An MCP tool definition or None if conversion failed
    """
    try:
        # Create input schema for the tool
        properties = {}
        required = []

        for param in tool.definition.input.parameters:
            param_schema = {
                "type": _map_type_to_json_schema_type(param.value_schema.val_type),
                "description": param.description or "",
            }

            # Add enum values if available
            if param.value_schema.enum:
                param_schema["enum"] = param.value_schema.enum

            properties[param.name] = param_schema

            if param.required:
                required.append(param.name)

        input_schema = {"type": "object", "properties": properties}

        if required:
            input_schema["required"] = required

        return {
            "name": str(tool.definition.get_fully_qualified_name()),
            "description": tool.definition.description,
            "inputSchema": input_schema,
        }
    except Exception:
        # If conversion fails, return None
        return None


def convert_to_mcp_content(result: Any) -> list[MCPContent]:
    """Convert an Arcade tool result to MCP content format

    MCP supports TextContent, ImageContent, and EmbeddedResource types.
    This function attempts to convert any result to one or more of these types.

    Args:
        result: The result from the tool execution

    Returns:
        A list of MCP content objects
    """
    if result is None:
        return []

    # Handle results that are already in MCP content format
    if isinstance(result, dict) and "type" in result:  # noqa: SIM102
        if result["type"] in ["text", "image", "resource"]:
            return [result]

    # Handle list/tuple of results
    if isinstance(result, (list, tuple)):
        # Flatten the list of contents
        contents = []
        for item in result:
            contents.extend(convert_to_mcp_content(item))
        return contents

    # Handle dict/object results by converting to JSON
    if isinstance(result, dict):
        try:
            return [{"type": "text", "text": json.dumps(result)}]
        except Exception:
            return [{"type": "text", "text": str(result)}]

    # Handle primitive types by converting to string
    return [{"type": "text", "text": str(result)}]


def _map_type_to_json_schema_type(val_type: str) -> str:
    """Map Arcade value types to JSON schema types"""
    mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }

    return mapping.get(val_type, "string")


async def execute_tool(tool: MaterializedTool, arguments: dict[str, Any]) -> Any:
    """Execute an Arcade tool with the given arguments

    Args:
        tool: The tool to execute
        arguments: The arguments to pass to the tool

    Returns:
        The result of the tool execution
    """
    # Convert arguments to input model
    tool_input = tool.input_model(**arguments)

    # Call the tool function
    tool_func = tool.tool
    if callable(tool_func):
        # Handle both async and sync functions
        if hasattr(tool_func, "__awaitable__") or hasattr(tool_func, "__await__"):
            result = await tool_func(**tool_input.model_dump())
        else:
            result = tool_func(**tool_input.model_dump())

        return result

    raise ValueError(f"Tool {tool.name} is not callable")
