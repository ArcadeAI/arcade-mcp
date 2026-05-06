"""ResourceServerAuth implementation with OAuth discovery metadata support.

This module provides the base ResourceServerAuth class that validates JWT tokens
from one or more authorization servers and provides OAuth 2.0 Protected Resource
Metadata (RFC 9728) for discovery.

Vendor specific implementations (WorkOS, Auth0, Descope, etc.) should inherit
from ResourceServerAuth.
"""

from typing import Any

from arcade_mcp_server.resource_server.base import (
    AuthenticationError,
    AuthorizationServerEntry,
    InvalidTokenError,
    ResourceOwner,
    ResourceServerValidator,
    TokenExpiredError,
    _validate_advertised_scopes,
    _validate_resource_metadata_url,
)
from arcade_mcp_server.resource_server.validators.jwks import JWKSTokenValidator
from arcade_mcp_server.settings import MCPSettings


class ResourceServerAuth(ResourceServerValidator):
    """OAuth 2.1 Resource Server with discovery metadata support.

    This class implements the MCP server's role as an OAuth 2.1 Resource Server,
    validating JWT tokens from one or more authorization servers and providing
    OAuth 2.0 Protected Resource Metadata (RFC 9728) for discovery.

    """

    def __init__(
        self,
        authorization_servers: list[AuthorizationServerEntry] | None = None,
        canonical_url: str | None = None,
        cache_ttl: int = 3600,
        scopes_supported: list[str] | None = None,
        default_challenge_scopes: list[str] | None = None,
    ):
        """Initialize Resource Server.

        Supports environment variable configuration via MCP_RESOURCE_SERVER_* variables.
        Explicit parameters take precedence over environment variables.

        Args:
            authorization_servers: List of authorization server entries
            canonical_url: MCP server canonical URL (or MCP_RESOURCE_SERVER_CANONICAL_URL).
                Validated at construction against RFC 6750 char-grammar,
                RFC 3986 URI structure (scheme is https, or http for loopback
                hosts only), RFC 3986 character correctness, and the MCP
                canonical-URI rule (no fragment).
            cache_ttl: JWKS cache TTL in seconds
            scopes_supported: Operator-declared scopes for RFC 9728 PRM
                ``scopes_supported``. Per the MCP spec, the *minimum* scopes
                for basic functionality. ``None`` (the default) omits the
                field from PRM. Independent of ``default_challenge_scopes``
                (the spec permits the two surfaces to be unrelated).
                Configurable via ``MCP_RESOURCE_SERVER_SCOPES_SUPPORTED``
                (space-separated, explicit kwarg wins). Each token must
                conform to the RFC 6750 grammar; duplicates are removed
                preserving first-seen order.
            default_challenge_scopes: Operator-declared scopes for the
                entry-401 RFC 6750 ``WWW-Authenticate: scope=`` parameter.
                ``None`` (the default) omits ``scope=``. Independent of
                ``scopes_supported``: the spec explicitly permits this set
                to be a non-subset / non-superset alternative collection.
                Configurable via
                ``MCP_RESOURCE_SERVER_DEFAULT_CHALLENGE_SCOPES``
                (space-separated, explicit kwarg wins). Same RFC 6750
                grammar validation as ``scopes_supported``.

        Raises:
            ValueError: If required fields not provided via params or env vars,
                if ``canonical_url`` violates the URI rules above, or if any
                scope token violates the RFC 6750 grammar.

        Example:
            ```python
            # Option 1: Use environment variables
            # Set MCP_RESOURCE_SERVER_CANONICAL_URL and MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS env vars
            resource_server_auth = ResourceServerAuth()

            # Option 2: Single Authorization Server (aud claim matches canonical_url)
            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
            )

            # Option 3: Custom audience (when auth server returns different aud claim)
            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://workos.authkit.app",
                        issuer="https://workos.authkit.app",
                        jwks_uri="https://workos.authkit.app/oauth2/jwks",
                        expected_audiences=["my-authkit-client-id"],  # Override expected aud
                    ),
                    AuthorizationServerEntry(  # Keycloak example configuration
                        authorization_server_url="http://localhost:8080/realms/mcp-test",
                        issuer="http://localhost:8080/realms/mcp-test",
                        jwks_uri="http://localhost:8080/realms/mcp-test/protocol/openid-connect/certs",
                        algorithm="RS256",
                        expected_audiences=["my-keycloak-client-id"],
                    ),
                ],
            )
            ```
        """
        settings = MCPSettings.from_env()

        self.cache_ttl = cache_ttl

        # Explicit parameters take precedence over environment variables
        if canonical_url is not None:
            resolved_canonical = canonical_url
        elif settings.resource_server.canonical_url is not None:
            resolved_canonical = settings.resource_server.canonical_url
        else:
            raise ValueError(
                "'canonical_url' required (parameter or MCP_RESOURCE_SERVER_CANONICAL_URL environment variable)"
            )

        # Validate the canonical URL at construction so misconfigurations
        # surface at server startup, not at the first 401/403 emit.
        # Settings-level validation also runs (see ResourceServerSettings),
        # but explicit constructor kwargs bypass that path.
        self.canonical_url = _validate_resource_metadata_url(resolved_canonical)

        if authorization_servers is not None:
            configs = authorization_servers
        elif settings.resource_server.authorization_servers:
            configs = settings.resource_server.to_authorization_server_entries()
        else:
            raise ValueError(
                "'authorization_servers' required (parameter or MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS environment variable)"
            )

        # Resolve scopes_supported: explicit kwarg wins, else env var via
        # MCPSettings. Either path runs through the same RFC 6750 grammar
        # validator: malformed tokens raise ValueError at construction.
        raw_supported: list[str] | None = (
            scopes_supported
            if scopes_supported is not None
            else settings.resource_server.scopes_supported
        )
        self.scopes_supported = _validate_advertised_scopes(raw_supported)

        # Resolve default_challenge_scopes: same precedence and validation.
        # Independent of scopes_supported per the SEP-835 surface split.
        raw_challenge: list[str] | None = (
            default_challenge_scopes
            if default_challenge_scopes is not None
            else settings.resource_server.default_challenge_scopes
        )
        self.default_challenge_scopes = _validate_advertised_scopes(raw_challenge)

        self._validators = self._create_validators(configs)

        self._resource_metadata = self._build_resource_metadata()

    def _build_resource_metadata(self) -> dict[str, Any]:
        """Build RFC 9728 Protected Resource Metadata

        Returns:
            Dictionary containing resource metadata per RFC 9728
        """
        metadata: dict[str, Any] = {
            "resource": self.canonical_url,
            "authorization_servers": list(self._validators.keys()),
            "bearer_methods_supported": ["header"],
        }
        # ``scopes_supported`` is OPTIONAL per RFC 9728. The SEP-835 surface
        # split keeps this independent from ``default_challenge_scopes``:
        # PRM advertises the documented baseline; the 401 challenge advertises
        # what the server is asking the client to acquire RIGHT NOW. They MAY
        # be equal, disjoint, sub/super-sets, or alternative collections.
        if self.scopes_supported:
            metadata["scopes_supported"] = list(self.scopes_supported)
        return metadata

    def _create_validators(
        self, entries: list[AuthorizationServerEntry]
    ) -> dict[str, JWKSTokenValidator]:
        """Create a mapping of authorization server URLs to their JWKSTokenValidator instances.

        Args:
            entries: List of authorization server entries

        Returns:
            Dictionary that maps authorization_server_url to its JWKSTokenValidator instance
        """
        validators = {}

        for entry in entries:
            # Use expected_audiences if provided, otherwise default to canonical_url
            audience = (
                entry.expected_audiences if entry.expected_audiences else [self.canonical_url]
            )
            validators[entry.authorization_server_url] = JWKSTokenValidator(
                jwks_uri=entry.jwks_uri,
                issuer=entry.issuer,
                audience=audience,
                algorithm=entry.algorithm,
                cache_ttl=self.cache_ttl,
                validation_options=entry.validation_options,
            )

        return validators

    async def validate_token(self, token: str) -> ResourceOwner:
        """Validate the given token against each configured authorization server.

        Tries each validator until one succeeds. If all fail, raises InvalidTokenError.

        Error handling strategy:
        - TokenExpiredError: Raise immediately. If any validator raises this, the token
          is expired for all authorization servers (expiration is universal). No point
          trying other validators.
        - InvalidTokenError/AuthenticationError: Continue to next validator because another
          authorization server might accept the token. These errors indicate wrong issuer,
          audience, or signature mismatch.

        Args:
            token: JWT Bearer token

        Returns:
            ResourceOwner with user_id, client_id, and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature, algorithm, audience, or issuer is invalid
            AuthenticationError: Other validation errors
        """
        for validator in self._validators.values():
            try:
                return await validator.validate_token(token)
            except TokenExpiredError:
                raise
            except (InvalidTokenError, AuthenticationError):
                continue

        raise InvalidTokenError("Token validation failed for all configured authorization servers")

    def supports_oauth_discovery(self) -> bool:
        """This Resource Server supports OAuth discovery."""
        return True

    def get_resource_metadata(self) -> dict[str, Any]:
        """Return RFC 9728 Protected Resource Metadata.

        This metadata tells MCP clients:
        1. What resource this server protects (canonical URL)
        2. Which authorization server(s) can issue tokens for this resource
        3. Supported bearer token methods

        Returns:
            Dictionary containing resource metadata per RFC 9728
        """
        return self._resource_metadata
