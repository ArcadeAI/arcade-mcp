"""EvalSuite internal unified tool registry (not part of the public API)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from arcade_evals._evalsuite._anthropic_schema import convert_mcp_to_anthropic_tool
from arcade_evals._evalsuite._openai_schema import convert_to_strict_mode_schema

ToolFormat = Literal["openai", "anthropic"]


class _MCPToolDefinitionRequired(TypedDict):
    """Required fields for MCP-style tool definition."""

    name: str


class MCPToolDefinition(_MCPToolDefinitionRequired, total=False):
    """MCP-style tool definition structure.

    This is the format expected by `add_tool_definitions()` and used internally
    by the EvalSuiteToolRegistry.

    Required:
        name: The unique tool name.

    Optional:
        description: Human-readable description (defaults to "").
        inputSchema: JSON Schema for input parameters
                     (defaults to {"type": "object", "properties": {}}).
    """

    description: str
    inputSchema: dict[str, Any]


class EvalSuiteToolRegistry:
    """
    A minimal internal registry that stores tools in MCP-style descriptors:

        {
          "name": "...",
          "description": "...",
          "inputSchema": { ... JSON Schema ... }
        }

    EvalSuite converts Python tools into this format too, so there is only one
    runtime path for OpenAI tool formatting.
    """

    def __init__(self, *, strict_mode: bool = True) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._strict_mode = strict_mode

    @property
    def strict_mode(self) -> bool:
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, value: bool) -> None:
        self._strict_mode = value

    def add_tool(self, tool_descriptor: MCPToolDefinition | dict[str, Any]) -> None:
        if "name" not in tool_descriptor:
            raise ValueError("Tool descriptor must have a 'name' field")
        name = tool_descriptor["name"]
        if name in self._tools:
            raise ValueError(
                f"Tool '{name}' already registered. "
                "Each tool name must be unique across all sources (MCP servers, gateways, catalogs)."
            )
        self._tools[name] = dict(tool_descriptor)

    def add_tools(self, tools: list[MCPToolDefinition] | list[dict[str, Any]]) -> None:
        for tool in tools:
            self.add_tool(tool)

    def list_tools_for_model(self, tool_format: ToolFormat = "openai") -> list[dict[str, Any]]:
        if tool_format == "openai":
            return self._to_openai_format()
        elif tool_format == "anthropic":
            return self._to_anthropic_format()
        else:
            raise ValueError(f"Tool format '{tool_format}' is not supported")

    def _to_openai_format(self) -> list[dict[str, Any]]:
        """Convert stored MCP tools to OpenAI function calling format."""
        openai_tools: list[dict[str, Any]] = []
        for tool in self._tools.values():
            parameters = tool.get("inputSchema", {"type": "object", "properties": {}})
            if self._strict_mode and isinstance(parameters, dict):
                parameters = convert_to_strict_mode_schema(parameters)

            openai_tool: dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": parameters,
                },
            }
            if self._strict_mode:
                openai_tool["function"]["strict"] = True
            openai_tools.append(openai_tool)

        return openai_tools

    def _to_anthropic_format(self) -> list[dict[str, Any]]:
        """Convert stored MCP tools to Anthropic tool format."""
        return [convert_mcp_to_anthropic_tool(tool) for tool in self._tools.values()]

    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(tool_name)
        if not tool:
            return args

        schema = tool.get("inputSchema", {})
        if not isinstance(schema, dict):
            return args

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return args

        normalized = dict(args)
        for prop_name, prop_schema in properties.items():
            if (
                prop_name not in normalized
                and isinstance(prop_schema, dict)
                and "default" in prop_schema
            ):
                normalized[prop_name] = prop_schema["default"]
        return normalized

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        return self._tools.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def tool_count(self) -> int:
        return len(self._tools)
