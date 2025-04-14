"""
MCP (Model Context Protocol) integration for Arcade Workers.

This package provides components and utilities for serving Arcade tools
over the Model Context Protocol.
"""

try:
    from mcp.types import JSONRPCMessage  # noqa: F401

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from arcade.worker.mcp.components import (
    convert_to_mcp_content,
    create_mcp_tool,
    execute_tool,
)
from arcade.worker.mcp.logging import MCPLoggingMiddleware, create_mcp_logging_middleware
from arcade.worker.mcp.message_processor import MCPMessageProcessor, create_message_processor
from arcade.worker.mcp.server import PatchedMCPServer
from arcade.worker.mcp.sse import MCPSSEComponent, create_mcp_sse_component

__all__ = [
    "convert_to_mcp_content",
    "create_mcp_tool",
    "execute_tool",
    "create_mcp_logging_middleware",
    "MCPLoggingMiddleware",
    "create_message_processor",
    "MCPMessageProcessor",
    "PatchedMCPServer",
    "create_mcp_sse_component",
    "MCPSSEComponent",
    "MCP_AVAILABLE",
]
