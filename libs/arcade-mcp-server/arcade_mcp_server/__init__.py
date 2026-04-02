"""
MCP (Model Context Protocol) support for Arcade.

This package provides:
- MCPApp: A FastAPI-like interface for building MCP servers with decorators
- MCPServer: Lower-level server implementation for serving Arcade tools
- Multiple transport options (stdio, HTTP/SSE)
- Tools and resources support
- Integration with Arcade workers with factory and runner functions
- Context system for tool execution with MCP methods
"""

from arcade_tdk import tool

from arcade_mcp_server.context import Context
from arcade_mcp_server.mcp_app import MCPApp
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.types import (
    Annotations,
    BlobResourceContents,
    Resource,
    ResourceTemplate,
    TextResourceContents,
)
from arcade_mcp_server.worker import create_arcade_mcp, run_arcade_mcp

__all__ = [
    "Annotations",
    "BlobResourceContents",
    "Context",
    "MCPApp",
    "MCPServer",
    "MCPSettings",
    "Resource",
    "ResourceTemplate",
    "TextResourceContents",
    "create_arcade_mcp",
    "run_arcade_mcp",
    "tool",
]

# Package metadata
__version__ = "0.1.0"
