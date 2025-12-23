"""Base classes for MCP Resource Server authentication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class AccessTokenValidationOptions(BaseModel):
    """Options for access token validation.

    All validations are enabled by default for security.
    Set to False to disable specific validations for authorization servers
    that are not compliant with MCP.

    Note: Token signature verification and audience validation are always enabled
    and cannot be disabled. Additionally, the subject (sub claim) must always be
    present in the token.
    """

    verify_exp: bool = Field(
        default=True,
        description="Verify token expiration (exp claim)",
    )
    verify_iat: bool = Field(
        default=True,
        description="Verify issued-at time (iat claim)",
    )
    verify_iss: bool = Field(
        default=True,
        description="Verify issuer claim (iss claim)",
    )
    verify_nbf: bool = Field(
        default=True,
        description="Verify not-before time (nbf claim). Rejects tokens used before their activation time.",
    )
    leeway: int = Field(
        default=0,
        description="Clock skew tolerance in seconds for exp/nbf validation. Recommended: 30-60 seconds.",
    )


@dataclass
class ResourceOwner:
    """User information extracted from validated access token.

    This represents the authenticated resource owner (end-user) making requests
    to the MCP server. The user_id typically comes from the 'sub' (subject) claim
    in JWT tokens.
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
class AuthorizationServerEntry:
    """Configuration entry for a single authorization server.

    Each authorization server that can issue valid tokens for this
    MCP server (Resource Server) needs its own entry specifying how to
    verify tokens from that server.
    """

    authorization_server_url: str
    """Authorization server URL for client discovery (RFC 9728)"""

    issuer: str
    """Expected issuer claim in JWT tokens from this server"""

    jwks_uri: str
    """JWKS endpoint to fetch public keys for token verification"""

    algorithm: str = "RS256"
    """JWT signature algorithm (RS256, ES256, PS256, etc.)"""

    expected_audiences: list[str] | None = None
    """Optional list of expected audience claims. If not provided,
    defaults to the MCP server's canonical_url. Use this when your
    authorization server returns a different aud claim (e.g., client_id)."""

    validation_options: AccessTokenValidationOptions = field(
        default_factory=AccessTokenValidationOptions
    )
    """Token validation options for this authorization server"""


class AuthenticationError(Exception):
    """Base authentication error."""

    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid (signature, audience, issuer, etc.)."""

    pass


class ResourceServerValidator(ABC):
    """Base class for MCP Resource Server token validation.

    An MCP server acts as an OAuth 2.1 Resource Server, validating Bearer tokens
    on every HTTP request. Implementations must validate tokens according to
    OAuth 2.1 Resource Server requirements, including:
    - Token signature verification
    - Expiration checking
    - Issuer validation
    - Audience validation

    Tokens are validated on every request - no caching is permitted per MCP spec.
    """

    @abstractmethod
    async def validate_token(self, token: str) -> ResourceOwner:
        """Validate bearer token and return authenticated resource owner info.

        Must validate:
        - Token signature
        - Expiration
        - Issuer (matches expected authorization server)
        - Audience (matches this MCP server's canonical URL)

        Args:
            token: Bearer token from Authorization header

        Returns:
            ResourceOwner with user_id and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token is invalid (signature, audience, issuer mismatch)
            AuthenticationError: Other validation errors
        """
        pass

    def supports_oauth_discovery(self) -> bool:
        """Whether this validator supports OAuth discovery endpoints.

        Returns True if the validator can serve OAuth 2.0 Protected Resource Metadata
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
