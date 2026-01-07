"""EvalSuite internal unified tool registry (not part of the public API)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from arcade_core.converters.anthropic import to_anthropic
from arcade_core.converters.utils import normalize_tool_name

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

    Note: Tools are stored with their original names (e.g., "Google.Search"),
    but Anthropic requires underscores (e.g., "Google_Search"). The registry
    maintains a mapping to look up tools by either format.
    """

    def __init__(self, *, strict_mode: bool = True) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._strict_mode = strict_mode
        # Mapping from normalized names (underscores) to original names (dots)
        # e.g., {"Google_Search": "Google.Search"}
        self._normalized_to_original: dict[str, str] = {}
        # Store original MaterializedTool objects for direct Anthropic conversion (Python tools only)
        self._materialized_tools: dict[str, Any] = {}

    @property
    def strict_mode(self) -> bool:
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, value: bool) -> None:
        self._strict_mode = value

    def add_tool(
        self,
        tool_descriptor: MCPToolDefinition | dict[str, Any],
        materialized_tool: Any = None,
    ) -> None:
        """Add a tool to the registry.

        Args:
            tool_descriptor: MCP-style tool definition.
            materialized_tool: Optional MaterializedTool for direct Anthropic conversion (Python tools only).
        """
        if "name" not in tool_descriptor:
            raise ValueError("Tool descriptor must have a 'name' field")
        name = tool_descriptor["name"]
        if name in self._tools:
            raise ValueError(
                f"Tool '{name}' already registered. "
                "Each tool name must be unique across all sources (MCP servers, gateways, catalogs)."
            )
        self._tools[name] = dict(tool_descriptor)

        # Store MaterializedTool if provided (for direct Anthropic conversion)
        if materialized_tool is not None:
            self._materialized_tools[name] = materialized_tool

        # Build normalized name mapping for Anthropic/OpenAI lookups
        # e.g., "Google.Search" -> normalized key "Google_Search"
        normalized_name = normalize_tool_name(name)
        if normalized_name != name:
            # Check for collision: if the normalized name already exists as a direct tool
            # (e.g., registering "Google.Search" when "Google_Search" already exists),
            # the normalized lookup would be ambiguous
            if normalized_name in self._tools:
                # The underscore version is registered directly, so normalized lookups
                # should prefer that. Don't add to mapping to avoid ambiguity.
                pass
            elif normalized_name in self._normalized_to_original:
                # Another dotted tool already maps to this normalized name
                # e.g., "A.B" and "A_B" (as "A.B") would both normalize to "A_B"
                # Keep the first mapping to avoid silent overwrites
                pass
            else:
                self._normalized_to_original[normalized_name] = name

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
        """Convert stored MCP tools to OpenAI function calling format.

        Note: Tool names are normalized (dots replaced with underscores) because
        OpenAI function names don't allow dots.
        """
        openai_tools: list[dict[str, Any]] = []
        for tool in self._tools.values():
            parameters = tool.get("inputSchema", {"type": "object", "properties": {}})
            if self._strict_mode and isinstance(parameters, dict):
                parameters = convert_to_strict_mode_schema(parameters)

            # Normalize tool name for OpenAI (e.g., "Google.Search" -> "Google_Search")
            # OpenAI function names don't allow dots
            tool_name = normalize_tool_name(tool["name"])

            openai_tool: dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "parameters": parameters,
                },
            }
            if self._strict_mode:
                openai_tool["function"]["strict"] = True
            openai_tools.append(openai_tool)

        return openai_tools

    def _to_anthropic_format(self) -> list[dict[str, Any]]:
        """Convert stored tools to Anthropic format.

        Uses direct to_anthropic() from arcade-core for Python tools (when MaterializedTool available),
        falls back to convert_mcp_to_anthropic_tool() for MCP/remote tools (JSON descriptors only).
        """
        anthropic_tools: list[dict[str, Any]] = []
        for tool_name, tool_descriptor in self._tools.items():
            # Python tools: use direct converter (we have MaterializedTool)
            if tool_name in self._materialized_tools:
                anthropic_tool = to_anthropic(self._materialized_tools[tool_name])
                anthropic_tools.append(dict(anthropic_tool))
            else:
                # MCP/remote tools: convert from JSON descriptor (no MaterializedTool available)
                # Used for tools from: load_mcp_remote_async(), load_from_stdio_async(),
                # load_arcade_mcp_gateway_async(), or add_tool_definitions()
                anthropic_tools.append(convert_mcp_to_anthropic_tool(tool_descriptor))

        return anthropic_tools

    def _resolve_tool_name(self, tool_name: str) -> str | None:
        """Resolve a tool name to its original registry key.

        Handles both original names (e.g., "Google.Search") and
        normalized names (e.g., "Google_Search" from Anthropic).

        Args:
            tool_name: The tool name to resolve.

        Returns:
            The original tool name if found, None otherwise.
        """
        # First, try direct lookup
        if tool_name in self._tools:
            return tool_name
        # Then, check if it's a normalized name (from Anthropic)
        original_name = self._normalized_to_original.get(tool_name)
        if original_name and original_name in self._tools:
            return original_name
        return None

    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Apply schema defaults to arguments.

        Fills in default values from the tool schema for:
        - Missing parameters (key not in args)
        - Null parameters (value is None), which OpenAI strict mode sends for optional params

        This ensures that optional parameters with defaults are properly filled
        even when the model sends null values.
        """
        resolved_name = self._resolve_tool_name(tool_name)
        tool = self._tools.get(resolved_name) if resolved_name else None
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
            # Apply default if parameter is missing OR if it's null (None)
            # OpenAI strict mode sends null for optional parameters that weren't provided
            should_apply_default = (
                isinstance(prop_schema, dict)
                and "default" in prop_schema
                and (prop_name not in normalized or normalized[prop_name] is None)
            )
            if should_apply_default:
                normalized[prop_name] = prop_schema["default"]
        return normalized

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        resolved_name = self._resolve_tool_name(tool_name)
        return self._tools.get(resolved_name) if resolved_name else None

    def has_tool(self, tool_name: str) -> bool:
        return self._resolve_tool_name(tool_name) is not None

    def resolve_tool_name(self, tool_name: str) -> str | None:
        """Public method to resolve a tool name to its original registry key.

        This is useful for callers that need to look up tools by names
        returned from providers (e.g., Anthropic returns underscore names).

        Args:
            tool_name: The tool name to resolve.

        Returns:
            The original tool name if found, None otherwise.
        """
        return self._resolve_tool_name(tool_name)

    def process_tool_call(self, tool_name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Resolve tool name and apply schema defaults in one step.

        This combines name resolution (for Anthropic underscore -> dot conversion)
        with schema default application.

        Args:
            tool_name: The tool name (may be in provider format like "Google_Search").
            args: The arguments from the tool call.

        Returns:
            Tuple of (resolved_name, args_with_defaults).
            resolved_name will be the original registered name (e.g., "Google.Search")
            or the input name if not found in registry.
        """
        resolved_name = self._resolve_tool_name(tool_name) or tool_name
        args_with_defaults = self.normalize_args(tool_name, args)
        return resolved_name, args_with_defaults

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def tool_count(self) -> int:
        return len(self._tools)
