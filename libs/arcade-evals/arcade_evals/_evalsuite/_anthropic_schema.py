"""Anthropic tool schema conversion (internal).

Converts MCP-style tool schemas to Anthropic's tool format.

Anthropic uses standard JSON Schema, so conversion is minimal:
- Rename inputSchema -> input_schema (camelCase to snake_case)
- Normalize tool names (dots to underscores, as Anthropic doesn't allow dots)
- No strict mode transformations needed
- Standard JSON Schema constraints are preserved
"""

from __future__ import annotations

from typing import Any

from arcade_core.converters.utils import normalize_tool_name as _normalize_tool_name


def convert_mcp_to_anthropic_tool(mcp_tool: dict[str, Any]) -> dict[str, Any]:
    """
    Convert an MCP tool definition to Anthropic tool format.

    This is a minimal conversion since Anthropic accepts standard JSON Schema.
    Changes:
    - Rename `inputSchema` to `input_schema`
    - Normalize tool name (dots to underscores)

    Args:
        mcp_tool: MCP-style tool definition with keys:
            - name (required)
            - description (optional)
            - inputSchema (optional, JSON Schema)

    Returns:
        Anthropic tool definition with keys:
            - name
            - description
            - input_schema
    """
    return {
        "name": _normalize_tool_name(mcp_tool["name"]),
        "description": mcp_tool.get("description", ""),
        "input_schema": mcp_tool.get("inputSchema", {"type": "object", "properties": {}}),
    }


def convert_mcp_tools_to_anthropic(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert a list of MCP tool definitions to Anthropic tool format.

    Args:
        mcp_tools: List of MCP-style tool definitions.

    Returns:
        List of Anthropic tool definitions.
    """
    return [convert_mcp_to_anthropic_tool(tool) for tool in mcp_tools]
