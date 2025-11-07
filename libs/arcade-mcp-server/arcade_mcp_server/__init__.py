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
from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider
from arcade_mcp_server.server_auth.providers.jwt import JWTVerifier
from arcade_mcp_server.server_auth.providers.remote import RemoteOAuthProvider
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.worker import create_arcade_mcp, run_arcade_mcp

__all__ = [
    "AuthenticatedUser",
    "AuthenticationError",
    "AuthKitProvider",
    "Context",
    "InvalidTokenError",
    "JWTVerifier",
    "MCPApp",
    "MCPServer",
    "MCPSettings",
    "RemoteOAuthProvider",
    "ServerAuthProvider",
    "TokenExpiredError",
    "create_arcade_mcp",
    "run_arcade_mcp",
    "tool",
]

# Package metadata
__version__ = "0.1.0"
