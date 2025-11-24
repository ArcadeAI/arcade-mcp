"""Base classes for server-level authentication providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class JWTVerifyOptions(BaseModel):
    """Options for JWT token verification.

    All validations are enabled by default for security.
    Set to False to disable specific validations for authorization servers that are not compliant with MCP.

    Note: Token signature verification is always enabled and cannot be disabled.
    Additionally, the subject (sub claim) must always be present in the token.
    """

    verify_exp: bool = Field(
        default=True,
        description="Verify token expiration (exp claim)",
    )
    verify_iat: bool = Field(
        default=True,
        description="Verify issued-at time (iat claim)",
    )
    verify_aud: bool = Field(
        default=True,
        description="Verify audience claim (aud claim)",
    )
    verify_iss: bool = Field(
        default=True,
        description="Verify issuer claim (iss claim)",
    )


@dataclass
class AuthenticatedUser:
    """User information extracted from validated access token.

    This represents the authenticated end-user making requests to the MCP server.
    The user_id typically comes from the 'sub' (subject) claim in JWT tokens.
    """

    user_id: str
    """User identifier from token (typically 'sub' claim)"""

    client_id: str | None = None
    """OAuth client identifier from 'client_id' or 'azp' claim"""

    email: str | None = None
    """User email if available in token claims"""

    claims: dict[str, Any] = field(default_factory=dict)
    """All claims from the validated token for advanced use cases"""


@dataclass
class AuthorizationServerConfig:
    """Configuration for a single authorization server.

    Each authorization server that can issue valid tokens for this
    MCP server needs its own config specifying how to verify tokens
    from that server.
    """

    authorization_server_url: str
    """Authorization server URL for client discovery (RFC 9728)"""

    issuer: str
    """Expected issuer claim in JWT tokens from this server"""

    jwks_uri: str
    """JWKS endpoint to fetch public keys for token verification"""

    algorithm: str = "RS256"
    """JWT signature algorithm (RS256, ES256, PS256, etc.)"""

    verify_options: JWTVerifyOptions = field(default_factory=JWTVerifyOptions)
    """Token verification options for this AS"""


class AuthenticationError(Exception):
    """Base authentication error."""

    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid (signature, audience, issuer, etc.)."""

    pass


class ServerAuthProvider(ABC):
    """Base class for front-door authentication providers.

    Implementations must validate Bearer tokens according to OAuth 2.1 Resource Server
    requirements, including:
    - Token signature verification
    - Expiration checking
    - Issuer validation
    - Audience validation

    Tokens are validated on EVERY request - no caching is permitted per MCP spec.
    """

    @abstractmethod
    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate bearer token and return authenticated user info.

        Must validate:
        - Token signature
        - Expiration
        - Issuer (matches expected authorization server)
        - Audience (matches this MCP server's canonical URL)

        Args:
            token: Bearer token from Authorization header

        Returns:
            AuthenticatedUser with user_id and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token is invalid (signature, audience, issuer mismatch)
            AuthenticationError: Other validation errors
        """
        pass

    def supports_oauth_discovery(self) -> bool:
        """Whether this provider supports OAuth discovery endpoints.

        Returns True if the provider can serve OAuth 2.0 Protected Resource Metadata
        (RFC 9728) to enable MCP clients to discover authorization servers.
        """
        return False

    def get_resource_metadata(self) -> dict[str, Any] | None:
        """Return OAuth Protected Resource Metadata (RFC 9728) if supported.

        Returns:
            Metadata dictionary with 'resource' and 'authorization_servers' fields,
            or None if discovery is not supported.
        """
        return None
