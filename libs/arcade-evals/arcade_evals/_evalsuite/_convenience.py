"""EvalSuite convenience methods (internal-only).

This module contains only the functionality introduced in this PR:
- tool registration convenience methods
- unified internal registry plumbing helpers

It is intentionally not exported from `arcade_evals.__init__`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from arcade_core.converters.openai import to_openai

from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry, MCPToolDefinition
from arcade_evals.loaders import (
    load_arcade_mcp_gateway_async,
    load_from_http_async,
    load_from_stdio_async,
)

if TYPE_CHECKING:
    from arcade_core import ToolCatalog


class _EvalSuiteConvenienceMixin:
    """Mixin providing convenience tool registration methods."""

    _internal_registry: EvalSuiteToolRegistry | None
    _python_tool_func_map: dict[str, Callable]
    _python_func_to_tool_name: dict[Callable, str]

    def _get_registry(self) -> EvalSuiteToolRegistry:
        """Get the internal registry (always initialized by EvalSuite.__post_init__)."""
        if self._internal_registry is None:
            raise RuntimeError("Internal registry not initialized. This should not happen.")
        return self._internal_registry

    def add_tool_definitions(self, tools: list[MCPToolDefinition]) -> Any:
        """Add tool definitions directly from MCP-style dictionaries.

        Args:
            tools: List of tool definitions. Each must have:
                - name (str): Required. The unique tool name.
                - description (str): Optional. Defaults to "".
                - inputSchema (dict): Optional. JSON Schema for parameters.
                                       Defaults to {"type": "object", "properties": {}}.

        Returns:
            Self for method chaining.

        Raises:
            TypeError: If a tool definition is not a dictionary.
            ValueError: If a tool definition is missing 'name' or the name is already registered.
        """
        registry = self._get_registry()
        for tool in tools:
            if not isinstance(tool, dict):
                raise TypeError("Tool definitions must be dictionaries")
            if "name" not in tool:
                raise ValueError("Tool definition must include 'name'")
            tool.setdefault("description", "")
            tool.setdefault("inputSchema", {"type": "object", "properties": {}})
            registry.add_tool(tool)
        return self

    async def add_mcp_server(
        self, url: str, *, headers: dict[str, str] | None = None, timeout: int = 10
    ) -> Any:
        import warnings

        registry = self._get_registry()
        tools = await load_from_http_async(url, timeout=timeout, headers=headers)
        if not tools:
            warnings.warn(
                f"No tools loaded from {url}. Server may be unavailable.",
                UserWarning,
                stacklevel=2,
            )
            return self
        registry.add_tools(tools)
        return self

    async def add_mcp_stdio_server(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> Any:
        import warnings

        registry = self._get_registry()
        tools = await load_from_stdio_async(command, timeout=timeout, env=env)
        if not tools:
            warnings.warn(
                f"No tools loaded from stdio command: {' '.join(command)}",
                UserWarning,
                stacklevel=2,
            )
            return self
        registry.add_tools(tools)
        return self

    async def add_arcade_gateway(
        self,
        gateway_slug: str,
        *,
        arcade_api_key: str | None = None,
        arcade_user_id: str | None = None,
        base_url: str | None = None,
        timeout: int = 10,
    ) -> Any:
        import warnings

        from arcade_evals.loaders import ARCADE_API_BASE_URL

        registry = self._get_registry()
        tools = await load_arcade_mcp_gateway_async(
            gateway_slug,
            arcade_api_key=arcade_api_key,
            arcade_user_id=arcade_user_id,
            base_url=base_url or ARCADE_API_BASE_URL,
            timeout=timeout,
        )
        if not tools:
            warnings.warn(
                f"No tools loaded from Arcade gateway: {gateway_slug}",
                UserWarning,
                stacklevel=2,
            )
            return self
        registry.add_tools(tools)
        return self

    def add_tool_catalog(self, catalog: ToolCatalog) -> Any:
        registry = self._get_registry()
        for tool in catalog:
            openai_tool = to_openai(tool)
            func_schema = openai_tool.get("function", {})
            tool_name = func_schema.get("name")
            if not tool_name:
                continue

            description = func_schema.get("description") or ""
            parameters = func_schema.get("parameters")
            input_schema: dict[str, Any] = (
                dict(parameters) if parameters else {"type": "object", "properties": {}}
            )

            registry.add_tool({
                "name": tool_name,
                "description": description,
                "inputSchema": input_schema,
            })

            python_func = getattr(tool, "tool", None)
            if callable(python_func):
                self._python_tool_func_map[tool_name] = python_func
                self._python_func_to_tool_name[python_func] = tool_name

        return self

    def get_tool_count(self) -> int:
        if self._internal_registry is None:
            return 0
        return self._internal_registry.tool_count()

    def list_tool_names(self) -> list[str]:
        if self._internal_registry is None:
            return []
        return self._internal_registry.tool_names()
