"""Base classes for MCP Resource Server authentication."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

# RFC 6750 §3 ABNF: scope-token = 1*( %x21 / %x23-5B / %x5D-7E )
# Equivalent to: at least one printable ASCII character, excluding ``"``
# (0x22), ``\`` (0x5C), space, control characters (< 0x20 and 0x7F), and any
# non-ASCII character.
_VALID_SCOPE_TOKEN = re.compile(r"^[\x21\x23-\x5B\x5D-\x7E]+$")
_WHITESPACE = re.compile(r"\s")


def _validate_scope_token(token: str) -> None:
    """Validate a single scope token against RFC 6750 §3 grammar.

    The grammar is ``scope-token = 1*( %x21 / %x23-5B / %x5D-7E )`` — at
    least one printable ASCII character, excluding ``"``, ``\\``, space,
    control characters, and non-ASCII.

    Validation runs at ``ResourceServerAuth`` construction (and at env-var
    parse time) so malformed tokens fail fast with a precise error rather
    than silently corrupting the ``WWW-Authenticate`` header at runtime.

    Args:
        token: A single OAuth scope value.

    Raises:
        ValueError: with a message classifying the failure (empty,
        whitespace, non-ASCII, or RFC 6750 grammar violation) and naming
        the offending token.
    """
    if not token:
        raise ValueError("Scope token must not be empty")
    if not token.strip():
        raise ValueError(f"Scope token must not be empty or whitespace-only: {token!r}")
    if _WHITESPACE.search(token):
        raise ValueError(f"Scope token must not contain whitespace per RFC 6750 §3: {token!r}")
    try:
        token.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"Scope token must be ASCII (non-ASCII char in {token!r}): {exc}") from exc
    if not _VALID_SCOPE_TOKEN.match(token):
        raise ValueError(
            f"Scope token violates RFC 6750 §3 grammar: {token!r}. "
            'Allowed: 0x21 / 0x23-0x5B / 0x5D-0x7E (no spaces, ", \\, '
            "control chars, or non-ASCII)."
        )


def _validate_advertised_scopes(scopes: list[str] | None) -> list[str] | None:
    """Validate, deduplicate, and normalize a list of OAuth scope tokens.

    Each token must conform to RFC 6750 §3 grammar (see
    ``_validate_scope_token``). Duplicates are removed with first-seen
    ordering preserved — operators expect their declared order to drive the
    advertised order in PRM ``scopes_supported`` and on the
    ``WWW-Authenticate`` ``scope`` parameter.

    Args:
        scopes: Scope token list (as passed to ``default_advertised_scopes``)
            or ``None``.

    Returns:
        Validated, deduplicated list (first-seen order), or ``None`` if
        input was ``None`` or empty list (signaling "no advertisement").

    Raises:
        ValueError: If any token violates RFC 6750 §3.
    """
    if not scopes:
        return None
    for token in scopes:
        _validate_scope_token(token)
    return list(dict.fromkeys(scopes))


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

    Subclasses may override ``default_advertised_scopes`` (set in ``__init__``)
    to surface scope guidance on the entry-401 ``WWW-Authenticate`` challenge
    and as ``scopes_supported`` in the RFC 9728 Protected Resource Metadata
    document. ``ResourceServerMiddleware`` reads this attribute directly from
    the validator — it is part of the ABC contract so middleware does not need
    a defensive ``getattr``.
    """

    default_advertised_scopes: list[str] | None = None
    """Operator-declared OAuth scopes for entry-401 ``WWW-Authenticate``
    advertisement and RFC 9728 ``scopes_supported``. ``None`` (the default)
    means no advertisement; clients fall back to the MCP 2025-11-25
    §Authorization scope-selection strategy. Concrete validators set this in
    their ``__init__``.

    The class-level default is ``None`` (immutable) rather than ``[]`` to
    avoid the mutable-default-argument footgun: a list at the class level
    would be shared across all subclass instances and could leak state via
    ``self.default_advertised_scopes.append(...)``. ``None`` is always
    shadowed cleanly by subclass instance assignment.
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
