"""
MCP (Model Context Protocol) support for Arcade.

This package provides:
- MCP server implementation for serving Arcade tools
- Multiple transport options (stdio, HTTP/SSE)
- Integration with Arcade workers with factory and runner functions
- Context system for tool execution with MCP methods

A FastAPI-like interface for building MCP servers.
- Add tools with decorators or explicitly
- Run the server with a single function call
- Supports HTTP transport only

`arcade_mcp` for running stdio directly from the command line.
- auto discovery of tools and construction of the server
- supports stdio transport only
- run with uv or `python -m arcade_mcp`
"""

from arcade_tdk import tool

from arcade_mcp_server.context import Context
from arcade_mcp_server.mcp_app import MCPApp
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.worker import create_arcade_mcp, run_arcade_mcp

__all__ = [
    "Context",
    # FastAPI-like interface
    "MCPApp",
    # MCP Server implementation
    "MCPServer",
    "MCPSettings",
    # Integrated Factory and Runner
    "create_arcade_mcp",
    "run_arcade_mcp",
    # Re-exported from TDK functionality
    "tool",
]

# Package metadata
__version__ = "0.1.0"
