"""
Server-level authentication for MCP servers.

This module provides front-door authentication capabilities following OAuth 2.1
Resource Server specifications. It enables MCP servers to validate Bearer tokens
on HTTP requests before processing MCP protocol messages.
"""

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider

__all__ = [
    "AuthenticatedUser",
    "AuthenticationError",
    "AuthKitProvider",
    "InvalidTokenError",
    "ServerAuthProvider",
    "TokenExpiredError",
]
