"""
MCP Resource Server authentication.

This module provides OAuth 2.1 Resource Server capabilities for MCP servers.
It enables MCP servers to validate Bearer tokens on every HTTP request
before processing MCP messages.
"""

from arcade_mcp_server.resource_server.base import (
    AccessTokenValidationOptions,
    AuthorizationServerEntry,
)
from arcade_mcp_server.resource_server.validators import (
    JWKSTokenValidator,
    ResourceServerAuth,
)

__all__ = [
    "AccessTokenValidationOptions",
    "AuthorizationServerEntry",
    "JWKSTokenValidator",
    "ResourceServerAuth",
]
