"""
Server-level authentication for MCP servers.

This module provides front-door authentication capabilities following OAuth 2.1
Resource Server specifications. It enables MCP servers to validate Bearer tokens
on every HTTP request before processing MCP messages.
"""

from arcade_mcp_server.server_auth.base import AuthorizationServerConfig, JWTVerifyOptions
from arcade_mcp_server.server_auth.providers import (
    JWTVerifier,
    RemoteOAuthProvider,
)

__all__ = [
    "AuthorizationServerConfig",
    "JWTVerifier",
    "JWTVerifyOptions",
    "RemoteOAuthProvider",
]
