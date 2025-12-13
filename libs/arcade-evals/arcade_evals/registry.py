"""Base registry interface for tool evaluation."""

import copy
import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    from arcade_core import ToolCatalog
    from arcade_core.converters.openai import OpenAIToolList


# ----------------------------------------------------------------------------
# OpenAI Strict Mode Type Definitions
# These types ensure compliance with OpenAI's function calling strict mode.
# Reference: https://platform.openai.com/docs/guides/structured-outputs
#
# OpenAI Strict Mode Requirements:
# 1. additionalProperties: false - REQUIRED at ALL object levels
# 2. properties: {} - REQUIRED for all object types (even if empty)
# 3. required: [] - REQUIRED for all object types (must list ALL properties)
# 4. Optional params: Use type union with null (e.g., ["string", "null"])
# 5. Unsupported keywords: minimum, maximum, pattern, format, nullable
# ----------------------------------------------------------------------------


class StrictModePropertySchema(TypedDict, total=False):
    """
    Schema for a property in OpenAI strict mode.

    All nested object properties must also comply with strict mode requirements.
    """

    type: str | list[str]
    """JSON Schema type. For optional params, use ["type", "null"]."""

    description: str
    """Description of the property."""

    enum: list[Any]
    """Allowed values for enum properties."""

    items: "StrictModePropertySchema"
    """Schema for array items when type is 'array'."""

    properties: dict[str, "StrictModePropertySchema"]
    """Nested properties when type is 'object'. Required for strict mode."""

    required: list[str]
    """Required fields. In strict mode, ALL properties must be listed here."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class StrictModeParametersSchema(TypedDict):
    """
    Root parameters schema for OpenAI strict mode function calling.

    This is the schema passed to function.parameters in OpenAI's API.
    ALL fields are required for strict mode compliance.
    """

    type: Literal["object"]
    """Must be 'object' for function parameters."""

    properties: dict[str, StrictModePropertySchema]
    """Parameter definitions. Required even if empty ({})."""

    required: list[str]
    """All property names. In strict mode, ALL properties must be listed."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class StrictModeFunctionSchema(TypedDict, total=False):
    """Schema for a function in OpenAI strict mode."""

    name: str
    """The name of the function to call."""

    description: str
    """Description of what the function does."""

    parameters: StrictModeParametersSchema
    """The function parameters schema."""

    strict: Literal[True]
    """Must be True for strict mode."""


class StrictModeToolSchema(TypedDict):
    """
    Complete tool schema for OpenAI strict mode function calling.

    This is what gets passed to the `tools` parameter in OpenAI's API.
    """

    type: Literal["function"]
    """Must be 'function'."""

    function: StrictModeFunctionSchema
    """The function definition."""


# Type alias for list of tools
StrictModeToolList = list[StrictModeToolSchema]


# Maximum recursion depth to prevent infinite loops in circular schema references
_MAX_SCHEMA_DEPTH = 50

# Keywords not supported by OpenAI strict mode that should be stripped
_UNSUPPORTED_STRICT_MODE_KEYWORDS = frozenset({
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "default",
    "nullable",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
})


class SchemaConversionError(Exception):
    """Raised when schema conversion fails."""

    pass


def _convert_to_strict_mode_schema(
    parameters: dict[str, Any],
) -> StrictModeParametersSchema:
    """
    Convert a JSON schema to OpenAI strict mode format.

    OpenAI's strict mode requires:
    1. additionalProperties: false - at ALL levels of nested objects
    2. properties: {} - REQUIRED for all object types (even if empty)
    3. required: [] - REQUIRED, must list ALL properties
    4. Optional parameters must have type ["original_type", "null"]
    5. Unsupported: minimum, maximum, pattern, format, nullable keywords

    Args:
        parameters: The input JSON schema (MCP inputSchema).

    Returns:
        StrictModeParametersSchema compatible with OpenAI strict mode.

    Raises:
        SchemaConversionError: If schema exceeds maximum nesting depth (circular reference protection).

    Example:
        >>> input_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> result = _convert_to_strict_mode_schema(input_schema)
        >>> result["additionalProperties"]
        False
        >>> result["required"]
        ['name']
    """
    # Deep copy to avoid mutating the original
    result = copy.deepcopy(parameters)

    # Apply strict mode recursively with depth tracking
    strict_schema = _apply_strict_mode_recursive(result, depth=0)

    # Ensure root schema has all required fields for StrictModeParametersSchema
    return StrictModeParametersSchema(
        type="object",
        properties=strict_schema.get("properties", {}),
        required=strict_schema.get("required", []),
        additionalProperties=False,
    )


def _apply_strict_mode_recursive(schema: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """
    Recursively apply OpenAI strict mode requirements to a schema.

    Args:
        schema: A JSON schema (can be root or nested).
        depth: Current recursion depth (for infinite loop protection).

    Returns:
        Schema with strict mode applied at all levels.

    Raises:
        SchemaConversionError: If maximum depth is exceeded.
    """
    # Infinite loop protection
    if depth > _MAX_SCHEMA_DEPTH:
        raise SchemaConversionError(
            f"Schema nesting exceeds maximum depth of {_MAX_SCHEMA_DEPTH}. "
            "This may indicate a circular reference in the schema."
        )

    # Strip unsupported keywords that OpenAI strict mode doesn't allow
    for keyword in _UNSUPPORTED_STRICT_MODE_KEYWORDS:
        schema.pop(keyword, None)

    schema_type = schema.get("type")

    # Handle object schemas
    if schema_type == "object":
        # Ensure additionalProperties is false (required for strict mode)
        schema["additionalProperties"] = False

        # Ensure properties exists (required for strict mode)
        if "properties" not in schema:
            schema["properties"] = {}

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        new_properties = {}
        all_param_names = []

        for param_name, param_schema in properties.items():
            if not isinstance(param_schema, dict):
                new_properties[param_name] = param_schema
                all_param_names.append(param_name)
                continue

            # Recursively process nested schemas with incremented depth
            processed_schema = _apply_strict_mode_recursive(param_schema, depth=depth + 1)

            # If parameter is optional (not in required array), add null to type
            if param_name not in required:
                param_type = processed_schema.get("type")
                if param_type is not None:
                    if isinstance(param_type, str):
                        # Convert single type to union with null
                        processed_schema["type"] = [param_type, "null"]
                    elif isinstance(param_type, list) and "null" not in param_type:
                        # Add null to existing type array
                        processed_schema["type"] = [*param_type, "null"]

            new_properties[param_name] = processed_schema
            all_param_names.append(param_name)

        schema["properties"] = new_properties
        # In strict mode, required must always be present (even if empty)
        schema["required"] = all_param_names

    # Handle array schemas - process items recursively
    elif schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            schema["items"] = _apply_strict_mode_recursive(items, depth=depth + 1)

    # Handle anyOf, oneOf, allOf - process each option recursively
    for combiner in ("anyOf", "oneOf", "allOf"):
        if combiner in schema:
            schema[combiner] = [
                _apply_strict_mode_recursive(option, depth=depth + 1)
                if isinstance(option, dict)
                else option
                for option in schema[combiner]
            ]

    return schema


class BaseToolRegistry(ABC):
    """
    Abstract interface for tool registries used in evaluations.

    This allows evaluations to work with both Python-based tools (ToolCatalog)
    """

    @abstractmethod
    def list_tools_for_model(self, tool_format: str = "openai") -> "OpenAIToolList":
        """
        Get formatted tools for the LLM.

        Args:
            tool_format: The format to use (currently only "openai" supported).

        Returns:
            List of tools in OpenAI format.
        """
        pass

    @abstractmethod
    def resolve_tool_name(self, identifier: Any) -> str:
        """
        Resolve a tool identifier to its canonical name.

        Args:
            identifier: Either a callable (for Python tools) or a string name (for MCP tools).

        Returns:
            The canonical fully-qualified tool name.
        """
        pass

    @abstractmethod
    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize tool arguments by filling in defaults.

        Args:
            tool_name: The canonical tool name.
            args: The provided arguments.

        Returns:
            Arguments with defaults filled in where available.
        """
        pass

    @abstractmethod
    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """
        Get the schema for a tool.

        Args:
            tool_name: The canonical tool name.

        Returns:
            The tool schema or None if not found.
        """
        pass


class PythonToolRegistry(BaseToolRegistry):
    """
    Registry wrapper for Python-based ToolCatalog.

    This maintains backward compatibility with existing eval code that uses
    Python callables decorated with @tool.
    """

    def __init__(self, catalog: "ToolCatalog"):
        """
        Initialize with a ToolCatalog.

        Args:
            catalog: The Arcade ToolCatalog containing Python tools.
        """
        self._catalog = catalog

    @property
    def catalog(self) -> "ToolCatalog":
        """Access the underlying catalog for backward compatibility."""
        return self._catalog

    def list_tools_for_model(self, tool_format: str = "openai") -> "OpenAIToolList":
        """Get tools in OpenAI format from the catalog."""
        from arcade_core.converters.openai import to_openai

        if tool_format != "openai":
            raise ValueError(f"Tool format '{tool_format}' is not supported")

        return [to_openai(tool) for tool in self._catalog]

    def resolve_tool_name(self, identifier: Any) -> str:
        """
        Resolve a Python callable to its fully-qualified tool name.

        Args:
            identifier: A Python callable (function).

        Returns:
            The fully-qualified tool name.
        """
        if not callable(identifier):
            raise TypeError(f"Expected callable, got {type(identifier)}")

        tool_def = self._catalog.find_tool_by_func(identifier)
        return str(tool_def.get_fully_qualified_name())

    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Fill in default arguments from Python function signature.

        Args:
            tool_name: The fully-qualified tool name.
            args: The provided arguments.

        Returns:
            Arguments with defaults filled in.
        """
        from arcade_core.schema import TOOL_NAME_SEPARATOR

        tool = self._catalog.get_tool_by_name(tool_name, separator=TOOL_NAME_SEPARATOR)
        func = tool.tool
        sig = inspect.signature(func)

        args_with_defaults = {}
        for param in sig.parameters.values():
            if param.name in args:
                args_with_defaults[param.name] = args[param.name]
            elif param.default is not inspect.Parameter.empty:
                args_with_defaults[param.name] = param.default
            else:
                args_with_defaults[param.name] = None

        return args_with_defaults

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """
        Get the tool definition schema.

        Args:
            tool_name: The fully-qualified tool name.

        Returns:
            The tool definition as a dict, or None if not found.
        """
        from arcade_core.schema import TOOL_NAME_SEPARATOR

        try:
            tool = self._catalog.get_tool_by_name(tool_name, separator=TOOL_NAME_SEPARATOR)
            return tool.definition.model_dump()
        except ValueError:
            return None


class MCPToolRegistry(BaseToolRegistry):
    """
    Registry for MCP server tools.

    This allows evaluations to run against tools from remote MCP servers
    without requiring Python callables. Tool descriptors are provided directly
    or loaded from an MCP server.
    """

    def __init__(
        self,
        tools: list[dict[str, Any]] | None = None,
        *,
        strict_mode: bool = True,
    ):
        """
        Initialize with MCP tool descriptors.

        Args:
            tools: List of MCP tool descriptors (from tools/list response).
                   Each descriptor should have 'name', 'description', and 'inputSchema'.
            strict_mode: Whether to use OpenAI strict mode for tool schemas.
                        When True (default), applies strict mode transformations:
                        - additionalProperties: false at all levels
                        - All properties in required array
                        - Optional params get null type union
                        - Unsupported keywords stripped (minimum, maximum, pattern, etc.)
                        When False, uses the original schema as-is.
        """
        self._tools: dict[str, dict[str, Any]] = {}
        self._strict_mode = strict_mode
        if tools:
            for tool in tools:
                self.add_tool(tool)

    @property
    def strict_mode(self) -> bool:
        """Whether strict mode is enabled for this registry."""
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, value: bool) -> None:
        """Set whether strict mode is enabled."""
        self._strict_mode = value

    def add_tool(self, tool_descriptor: dict[str, Any]) -> None:
        """
        Add an MCP tool descriptor to the registry.

        Args:
            tool_descriptor: MCP tool descriptor with 'name', 'description', 'inputSchema'.
        """
        if "name" not in tool_descriptor:
            raise ValueError("Tool descriptor must have a 'name' field")

        name = tool_descriptor["name"]
        self._tools[name] = tool_descriptor

    def list_tools_for_model(self, tool_format: str = "openai") -> "OpenAIToolList":
        """
        Convert MCP tools to OpenAI format.

        Args:
            tool_format: Format to convert to (only "openai" supported).

        Returns:
            List of tools in OpenAI function calling format.
            If strict_mode is enabled, schemas are converted to strict mode format.
        """
        if tool_format != "openai":
            raise ValueError(f"Tool format '{tool_format}' is not supported")

        openai_tools: list[Any] = []
        for tool in self._tools.values():
            # Get the input schema
            parameters = tool.get("inputSchema", {"type": "object", "properties": {}})

            # Apply strict mode conversion if enabled
            if self._strict_mode:
                parameters = _convert_to_strict_mode_schema(parameters)

            openai_tool: dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": parameters,
                },
            }

            # Only add strict flag when strict mode is enabled
            if self._strict_mode:
                openai_tool["function"]["strict"] = True

            openai_tools.append(openai_tool)

        return openai_tools

    def resolve_tool_name(self, identifier: Any) -> str:
        """
        Resolve a tool name identifier.

        For MCP tools, the identifier should already be a string name.

        Args:
            identifier: Tool name as a string.

        Returns:
            The tool name.
        """
        if not isinstance(identifier, str):
            raise TypeError(f"MCP tools require string names, got {type(identifier)}")

        if identifier not in self._tools:
            raise ValueError(f"Tool '{identifier}' not found in registry")

        return identifier

    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize arguments using schema defaults if available.

        Args:
            tool_name: The tool name.
            args: The provided arguments.

        Returns:
            Arguments with schema defaults filled in where available.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return args

        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})

        normalized = dict(args)
        for prop_name, prop_schema in properties.items():
            if prop_name not in normalized and "default" in prop_schema:
                normalized[prop_name] = prop_schema["default"]

        return normalized

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """
        Get the MCP tool descriptor.

        Args:
            tool_name: The tool name.

        Returns:
            The tool descriptor or None if not found.
        """
        return self._tools.get(tool_name)


class CompositeMCPRegistry(BaseToolRegistry):
    """
    Composite registry that combines multiple MCP tool sources.

    This allows evaluations to use tools from multiple MCP servers in a single suite.
    Tools are namespaced by server to avoid collisions (e.g., 'server1_tool_name').
    """

    def __init__(
        self,
        registries: dict[str, MCPToolRegistry] | None = None,
        tool_lists: dict[str, list[dict[str, Any]]] | None = None,
        *,
        strict_mode: bool = True,
    ):
        """
        Initialize with multiple MCP registries or tool descriptor lists.

        Args:
            registries: Dict mapping server names to MCPToolRegistry instances.
                        Note: If provided, those registries keep their own strict_mode setting.
            tool_lists: Dict mapping server names to lists of MCP tool descriptors.
                        If provided, MCPToolRegistry instances will be created with the
                        strict_mode setting from this composite registry.
            strict_mode: Whether to use OpenAI strict mode for tool schemas.
                        Only applies to registries created from tool_lists.
                        Pre-existing registries keep their own strict_mode setting.
                        Default is True.

        At least one of registries or tool_lists must be provided.
        """
        self._registries: dict[str, MCPToolRegistry] = {}
        # Maps tool identifiers to (server_name, registry, original_tool_name)
        self._tool_map: dict[str, tuple[str, MCPToolRegistry, str]] = {}
        self._strict_mode = strict_mode

        if registries:
            self._registries.update(registries)

        if tool_lists:
            for server_name, tools in tool_lists.items():
                if server_name in self._registries:
                    raise ValueError(f"Duplicate server name: {server_name}")
                self._registries[server_name] = MCPToolRegistry(tools, strict_mode=strict_mode)

        if not self._registries:
            raise ValueError("At least one registry or tool list must be provided")

        # Build the tool lookup map
        for server_name, registry in self._registries.items():
            self._add_tools_to_map(server_name, registry)

    @property
    def strict_mode(self) -> bool:
        """Whether strict mode is enabled for this composite registry."""
        return self._strict_mode

    def _add_tools_to_map(self, server_name: str, registry: MCPToolRegistry) -> None:
        """
        Add tools from a registry to the tool map.

        Args:
            server_name: Name of the server/registry.
            registry: The MCPToolRegistry instance.
        """
        for tool_name in registry._tools:
            # Store with namespace prefix (using underscore for OpenAI compatibility)
            # We store (server_name, registry, original_tool_name) to avoid underscore splitting issues
            namespaced_name = f"{server_name}_{tool_name}"
            self._tool_map[namespaced_name] = (server_name, registry, tool_name)

            # Also support dot notation for backward compatibility
            namespaced_name_dot = f"{server_name}.{tool_name}"
            self._tool_map[namespaced_name_dot] = (server_name, registry, tool_name)

            # Also allow short name if unique
            if tool_name not in self._tool_map:
                self._tool_map[tool_name] = (server_name, registry, tool_name)
            elif self._tool_map[tool_name][0] != "__ambiguous__":
                # Mark as ambiguous (multiple servers have this tool)
                self._tool_map[tool_name] = ("__ambiguous__", registry, tool_name)

    def add_registry(self, server_name: str, registry: MCPToolRegistry) -> None:
        """
        Add an additional MCP registry.

        Args:
            server_name: Unique name for this server/registry.
            registry: The MCPToolRegistry to add.
        """
        if server_name in self._registries:
            raise ValueError(f"Server '{server_name}' already exists")

        self._registries[server_name] = registry
        self._add_tools_to_map(server_name, registry)

    def list_tools_for_model(self, tool_format: str = "openai") -> "OpenAIToolList":
        """
        List all tools from all registries in OpenAI format.

        Tool names are prefixed with server name to ensure uniqueness.
        Uses underscore separator for OpenAI compatibility (dots not allowed).

        Args:
            tool_format: Format to convert to (only "openai" supported).

        Returns:
            List of tools in OpenAI format with namespaced names.
        """
        if tool_format != "openai":
            raise ValueError(f"Tool format '{tool_format}' is not supported")

        all_tools: list[Any] = []
        for server_name, registry in self._registries.items():
            server_tools = registry.list_tools_for_model(tool_format)
            # Prefix tool names with server name (using underscore for OpenAI compatibility)
            for tool in server_tools:
                # Only copy the parts we need to modify (more efficient than deepcopy)
                tool_copy = {
                    "type": tool["type"],
                    "function": {
                        **tool["function"],
                        "name": f"{server_name}_{tool['function']['name']}",
                    },
                }
                all_tools.append(tool_copy)

        return all_tools

    def resolve_tool_name(self, identifier: Any) -> str:
        """
        Resolve a tool name, supporting both namespaced and short names.

        Args:
            identifier: Tool name as a string, optionally prefixed with 'server_' or 'server.'

        Returns:
            The fully-qualified tool name in underscore format (server_tool).
            Always returns underscore format for OpenAI compatibility.

        Raises:
            TypeError: If identifier is not a string.
            ValueError: If tool not found or name is ambiguous.
        """
        if not isinstance(identifier, str):
            raise TypeError(f"MCP tools require string names, got {type(identifier)}")

        # Check if already namespaced
        if identifier in self._tool_map:
            server_name, _, original_tool_name = self._tool_map[identifier]
            if server_name == "__ambiguous__":
                raise ValueError(
                    f"Tool name '{identifier}' is ambiguous (exists in multiple servers). "
                    f"Use 'server_tool' or 'server.tool' format."
                )
            # Always return the canonical underscore format
            return f"{server_name}_{original_tool_name}"

        raise ValueError(f"Tool '{identifier}' not found in any registry")

    def normalize_args(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize arguments for a tool using its registry.

        Args:
            tool_name: The tool name (can be short or namespaced).
            args: The provided arguments.

        Returns:
            Arguments with defaults filled in.
        """
        # Resolve to get the correct registry
        resolved_name = self.resolve_tool_name(tool_name)
        server_name, registry, original_tool_name = self._tool_map[resolved_name]

        return registry.normalize_args(original_tool_name, args)

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """
        Get the schema for a tool.

        Args:
            tool_name: The tool name (can be short or namespaced).

        Returns:
            The tool descriptor or None if not found.
        """
        try:
            resolved_name = self.resolve_tool_name(tool_name)
            server_name, registry, original_tool_name = self._tool_map[resolved_name]
            return registry.get_tool_schema(original_tool_name)
        except ValueError:
            return None

    def get_server_names(self) -> list[str]:
        """Get list of all server names in this composite registry."""
        return list(self._registries.keys())

    def get_registry(self, server_name: str) -> MCPToolRegistry | None:
        """Get a specific registry by server name."""
        return self._registries.get(server_name)
