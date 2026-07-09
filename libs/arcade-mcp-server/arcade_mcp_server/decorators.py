"""MCP-aware decorators.

This module is the home for ``arcade_mcp_server``-side decorators that layer
MCP-specific concepts on top of ``arcade_tdk``. arcade-tdk stays
protocol-agnostic; protocol-specific kwargs (currently only ``execution`` /
``taskSupport``) live here, on a thin wrapper that delegates to
``arcade_tdk.tool`` for everything else.
"""

from __future__ import annotations

from typing import Callable

from arcade_core.metadata import ToolMetadata
from arcade_tdk import tool as _arcade_tdk_tool
from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.error_adapters import ErrorAdapter

from arcade_mcp_server.types import ToolExecution


# Keep this signature in sync with ``arcade_tdk.tool``. The
# ``test_signature_mirrors_arcade_tdk_plus_execution`` test in
# ``libs/tests/arcade_mcp_server/test_tool_wrapper.py`` fails loudly if
# arcade-tdk grows a new top-level kwarg that is not mirrored here.
def tool(
    func: Callable | None = None,
    desc: str | None = None,
    name: str | None = None,
    requires_auth: ToolAuthorization | None = None,
    requires_secrets: list[str] | None = None,
    requires_metadata: list[str] | None = None,
    adapters: list[ErrorAdapter] | None = None,
    metadata: ToolMetadata | None = None,
    execution: ToolExecution | None = None,
) -> Callable:
    """MCP-aware ``@tool`` decorator.

    Identical to ``arcade_tdk.tool`` plus an ``execution`` kwarg that
    declares MCP 2025-11-25 task-augmentation policy on the function via
    ``__tool_execution__``. The dunder is read by
    ``MCPServer._handle_call_tool`` (taskSupport policy enforcement) and
    ``create_mcp_tool`` (MCP wire conversion). All other arcade-tdk
    kwargs pass through unchanged.
    """

    def _apply(f: Callable) -> Callable:
        decorated = _arcade_tdk_tool(
            f,
            desc=desc,
            name=name,
            requires_auth=requires_auth,
            requires_secrets=requires_secrets,
            requires_metadata=requires_metadata,
            adapters=adapters,
            metadata=metadata,
        )
        # Write on the error-handler-wrapped callable arcade-tdk returns.
        # Both read sites (``server.py`` for taskSupport policy and
        # ``convert.py`` for the MCP wire response) read the dunder off
        # this exact object, so writing here is the direct path. Arcade-tdk
        # itself no longer touches ``__tool_execution__``, so there is no
        # risk of the wrap clobbering the value.
        decorated.__tool_execution__ = execution  # type: ignore[attr-defined]
        return decorated

    if func is None:
        return _apply
    return _apply(func)


# Forward arcade-tdk's ``@tool.deprecated("msg")`` ergonomic so callers can
# use ``@tool.deprecated`` via the MCP-side import path too. Same callable
# object, same semantics.
tool.deprecated = _arcade_tdk_tool.deprecated  # type: ignore[attr-defined]
