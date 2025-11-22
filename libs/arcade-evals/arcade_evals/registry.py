"""Base registry interface for tool evaluation."""

import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arcade_core import ToolCatalog
    from arcade_core.converters.openai import OpenAIToolList


def _convert_to_strict_mode_schema(parameters: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a JSON schema to OpenAI strict mode format.

    OpenAI's strict mode requires:
    1. additionalProperties: false
    2. Optional parameters must have type ["original_type", "null"]
    3. All parameters (including optional) must be in required array

    Args:
        parameters: The input JSON schema (MCP inputSchema).

    Returns:
        Schema compatible with OpenAI strict mode.
    """
    # Make a copy to avoid mutating the original
    result = parameters.copy()

    # Ensure additionalProperties is false (required for strict mode)
    if "additionalProperties" not in result:
        result["additionalProperties"] = False

    properties = result.get("properties", {})
    required = result.get("required", [])

    if not properties:
        return result

    new_properties = {}
    new_required = list(required)  # Start with existing required params

    for param_name, param_schema in properties.items():
        new_param_schema = param_schema.copy() if isinstance(param_schema, dict) else param_schema

        # If parameter is optional (not in required array or has default)
        if param_name not in required or "default" in param_schema:
            # Add null to type for strict mode
            param_type = (
                new_param_schema.get("type") if isinstance(new_param_schema, dict) else None
            )
            if param_type and isinstance(param_type, str):
                new_param_schema["type"] = [param_type, "null"]

            # In strict mode, all params must be in required (including optional ones)
            if param_name not in new_required:
                new_required.append(param_name)

        new_properties[param_name] = new_param_schema

    result["properties"] = new_properties
    result["required"] = new_required
    return result


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

    def __init__(self, tools: list[dict[str, Any]] | None = None):
        """
        Initialize with MCP tool descriptors.

        Args:
            tools: List of MCP tool descriptors (from tools/list response).
                   Each descriptor should have 'name', 'description', and 'inputSchema'.
        """
        self._tools: dict[str, dict[str, Any]] = {}
        if tools:
            for tool in tools:
                self.add_tool(tool)

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
        Convert MCP tools to OpenAI format with strict mode enabled.

        Args:
            tool_format: Format to convert to (only "openai" supported).

        Returns:
            List of tools in OpenAI function calling format.
        """
        if tool_format != "openai":
            raise ValueError(f"Tool format '{tool_format}' is not supported")

        openai_tools: list[Any] = []
        for tool in self._tools.values():
            # Get the input schema and convert to strict mode format
            parameters = tool.get("inputSchema", {"type": "object", "properties": {}})
            strict_parameters = _convert_to_strict_mode_schema(parameters)

            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": strict_parameters,
                    "strict": True,  # Enable strict mode for reliable tool calling
                },
            }
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
    ):
        """
        Initialize with multiple MCP registries or tool descriptor lists.

        Args:
            registries: Dict mapping server names to MCPToolRegistry instances.
            tool_lists: Dict mapping server names to lists of MCP tool descriptors.
                        If provided, MCPToolRegistry instances will be created for each.

        At least one of registries or tool_lists must be provided.
        """
        self._registries: dict[str, MCPToolRegistry] = {}
        self._tool_map: dict[str, tuple[str, MCPToolRegistry]] = {}

        if registries:
            self._registries.update(registries)

        if tool_lists:
            for server_name, tools in tool_lists.items():
                if server_name in self._registries:
                    raise ValueError(f"Duplicate server name: {server_name}")
                self._registries[server_name] = MCPToolRegistry(tools)

        if not self._registries:
            raise ValueError("At least one registry or tool list must be provided")

        # Build the tool lookup map
        for server_name, registry in self._registries.items():
            self._add_tools_to_map(server_name, registry)

    def _add_tools_to_map(self, server_name: str, registry: MCPToolRegistry) -> None:
        """
        Add tools from a registry to the tool map.

        Args:
            server_name: Name of the server/registry.
            registry: The MCPToolRegistry instance.
        """
        for tool_name in registry._tools:
            # Store with namespace prefix (using underscore for OpenAI compatibility)
            namespaced_name = f"{server_name}_{tool_name}"
            self._tool_map[namespaced_name] = (server_name, registry)

            # Also support dot notation for backward compatibility
            namespaced_name_dot = f"{server_name}.{tool_name}"
            self._tool_map[namespaced_name_dot] = (server_name, registry)

            # Also allow short name if unique
            if tool_name not in self._tool_map:
                self._tool_map[tool_name] = (server_name, registry)
            elif not tool_name.startswith(f"{server_name}_") and not tool_name.startswith(
                f"{server_name}."
            ):
                # Mark as ambiguous (multiple servers have this tool)
                self._tool_map[tool_name] = ("__ambiguous__", registry)

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
            server_name, _ = self._tool_map[identifier]
            if server_name == "__ambiguous__":
                raise ValueError(
                    f"Tool name '{identifier}' is ambiguous (exists in multiple servers). "
                    f"Use 'server_tool' or 'server.tool' format."
                )
            # If it's a short name, return the namespaced version with underscore
            if "." not in identifier and "_" not in identifier:
                return f"{server_name}_{identifier}"
            # Convert dot notation to underscore for OpenAI compatibility
            if "." in identifier:
                return identifier.replace(".", "_")
            return identifier

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
        server_name, registry = self._tool_map[resolved_name]

        # Get the original tool name without namespace (underscore format)
        original_name = resolved_name.split("_", 1)[1] if "_" in resolved_name else resolved_name

        return registry.normalize_args(original_name, args)

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
            server_name, registry = self._tool_map[resolved_name]
            # Get the original tool name without namespace (underscore format)
            original_name = (
                resolved_name.split("_", 1)[1] if "_" in resolved_name else resolved_name
            )
            return registry.get_tool_schema(original_name)
        except ValueError:
            return None

    def get_server_names(self) -> list[str]:
        """Get list of all server names in this composite registry."""
        return list(self._registries.keys())

    def get_registry(self, server_name: str) -> MCPToolRegistry | None:
        """Get a specific registry by server name."""
        return self._registries.get(server_name)
