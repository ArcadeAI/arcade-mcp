"""EvalSuite convenience methods (internal-only).

This module contains only the functionality introduced in this PR:
- tool registration convenience methods
- unified internal registry plumbing helpers
- track-based tool registration for comparative evaluations

It is intentionally not exported from `arcade_evals.__init__`.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Callable

from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry, MCPToolDefinition
from arcade_evals._evalsuite._tracks import TrackManager
from arcade_evals.loaders import (
    load_arcade_mcp_gateway_async,
    load_from_stdio_async,
    load_mcp_remote_async,
)

if TYPE_CHECKING:
    from arcade_core import ToolCatalog


class _EvalSuiteConvenienceMixin:
    """Mixin providing convenience tool registration methods."""

    _internal_registry: EvalSuiteToolRegistry | None
    _track_manager: TrackManager
    _python_tool_func_map: dict[str, Callable]
    _python_func_to_tool_name: dict[Callable, str]
    strict_mode: bool  # Attribute from EvalSuite dataclass

    def _get_registry(self, track: str | None = None) -> EvalSuiteToolRegistry:
        """Get the registry for a track or the default internal registry.

        Args:
            track: Optional track name. If provided, gets or creates the track registry.
                   If None, uses the default internal registry.

        Returns:
            The appropriate EvalSuiteToolRegistry.

        Raises:
            RuntimeError: If internal registry not initialized.
        """
        if track is not None:
            # Get existing track registry or create new one
            registry = self._track_manager.get_registry(track)
            if registry is None:
                # Create new registry for this track
                registry = EvalSuiteToolRegistry(strict_mode=self.strict_mode)
                self._track_manager.create_track(track, registry)
            return registry

        # Default: use internal registry
        if self._internal_registry is None:
            raise RuntimeError("Internal registry not initialized. This should not happen.")
        return self._internal_registry

    def get_tracks(self) -> list[str]:
        """Get all registered track names.

        Returns:
            List of track names in registration order.
        """
        return self._track_manager.get_track_names()

    def add_tool_definitions(
        self,
        tools: list[MCPToolDefinition],
        *,
        track: str | None = None,
    ) -> Any:
        """Add tool definitions directly from MCP-style dictionaries.

        Args:
            tools: List of tool definitions. Each must have:
                - name (str): Required. The unique tool name.
                - description (str): Optional. Defaults to "".
                - inputSchema (dict): Optional. JSON Schema for parameters.
                                       Defaults to {"type": "object", "properties": {}}.
            track: Optional track name. If provided, tools are added to that track's
                   isolated registry. Use for comparative evaluations.

        Returns:
            Self for method chaining.

        Raises:
            TypeError: If a tool definition is not a dictionary.
            ValueError: If a tool definition is missing 'name' or the name is already registered.
        """
        registry = self._get_registry(track)
        for tool in tools:
            if not isinstance(tool, dict):
                raise TypeError("Tool definitions must be dictionaries")
            if "name" not in tool:
                raise ValueError("Tool definition must include 'name'")
            # Copy to avoid mutating input dict
            tool_copy = dict(tool)
            tool_copy.setdefault("description", "")
            tool_copy.setdefault("inputSchema", {"type": "object", "properties": {}})
            registry.add_tool(tool_copy)
        return self

    async def add_mcp_server(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 10,
        track: str | None = None,
        use_sse: bool = False,
    ) -> Any:
        """Add tools from an MCP HTTP server.

        Args:
            url: The MCP server URL.
            headers: Optional HTTP headers.
            timeout: Connection timeout in seconds.
            track: Optional track name for comparative evaluations.
            use_sse: If True, use Server-Sent Events (SSE) transport.

        Returns:
            Self for method chaining.
        """
        registry = self._get_registry(track)
        tools = await load_mcp_remote_async(url, timeout=timeout, headers=headers, use_sse=use_sse)
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
        track: str | None = None,
    ) -> Any:
        """Add tools from an MCP stdio server.

        Args:
            command: Command to start the MCP server.
            env: Optional environment variables.
            timeout: Connection timeout in seconds.
            track: Optional track name for comparative evaluations.

        Returns:
            Self for method chaining.
        """
        registry = self._get_registry(track)
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
        track: str | None = None,
    ) -> Any:
        """Add tools from an Arcade MCP gateway.

        Args:
            gateway_slug: The Arcade gateway slug.
            arcade_api_key: Optional API key.
            arcade_user_id: Optional user ID.
            base_url: Optional base URL.
            timeout: Connection timeout in seconds.
            track: Optional track name for comparative evaluations.

        Returns:
            Self for method chaining.
        """
        registry = self._get_registry(track)

        tools = await load_arcade_mcp_gateway_async(
            gateway_slug,
            arcade_api_key=arcade_api_key,
            arcade_user_id=arcade_user_id,
            base_url=base_url,  # Let loader handle default/env var
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

    def add_tool_catalog(
        self,
        catalog: ToolCatalog,
        *,
        track: str | None = None,
    ) -> Any:
        """Add tools from a ToolCatalog to the internal registry.

        Args:
            catalog: A ToolCatalog containing registered Python tools.
            track: Optional track name for comparative evaluations.

        Returns:
            Self for method chaining.
        """
        # Delegate to the shared helper method defined in EvalSuite
        self._register_catalog_tools(catalog, track=track)  # type: ignore[attr-defined]
        return self

    def get_tool_count(self, track: str | None = None) -> int:
        """Get the number of registered tools.

        Args:
            track: Optional track name. If provided, counts tools in that track.

        Returns:
            Number of tools.
        """
        if track is not None:
            registry = self._track_manager.get_registry(track)
            return registry.tool_count() if registry else 0
        if self._internal_registry is None:
            return 0
        return self._internal_registry.tool_count()

    def list_tool_names(self, track: str | None = None) -> list[str]:
        """List all registered tool names.

        Args:
            track: Optional track name. If provided, lists tools in that track.

        Returns:
            List of tool names.
        """
        if track is not None:
            registry = self._track_manager.get_registry(track)
            return registry.tool_names() if registry else []
        if self._internal_registry is None:
            return []
        return self._internal_registry.tool_names()
