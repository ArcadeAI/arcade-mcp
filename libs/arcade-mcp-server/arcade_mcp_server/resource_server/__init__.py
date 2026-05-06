"""
MCP Resource Server authentication.

This module provides OAuth 2.1 Resource Server capabilities for MCP servers.
It enables MCP servers to validate Bearer tokens on every HTTP request
before processing MCP messages.
"""

from arcade_mcp_server.resource_server.base import (
    AccessTokenValidationOptions,
    AuthorizationServerEntry,
    InsufficientScopeError,
    ResourceOwner,
)
from arcade_mcp_server.resource_server.headers import (
    build_insufficient_scope_www_authenticate,
)
from arcade_mcp_server.resource_server.scope_enforcement import enforce_scopes
from arcade_mcp_server.resource_server.validators import (
    JWKSTokenValidator,
    ResourceServerAuth,
)

__all__ = [
    "AccessTokenValidationOptions",
    "AuthorizationServerEntry",
    "InsufficientScopeError",
    "JWKSTokenValidator",
    "ResourceOwner",
    "ResourceServerAuth",
    "build_insufficient_scope_www_authenticate",
    "enforce_scopes",
]
