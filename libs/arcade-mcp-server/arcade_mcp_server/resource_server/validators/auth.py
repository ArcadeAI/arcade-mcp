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
        default_advertised_scopes: list[str] | None = None,
    ):
        """Initialize Resource Server.

        Supports environment variable configuration via MCP_RESOURCE_SERVER_* variables.
        Explicit parameters take precedence over environment variables.

        Args:
            authorization_servers: List of authorization server entries
            canonical_url: MCP server canonical URL (or MCP_RESOURCE_SERVER_CANONICAL_URL)
            cache_ttl: JWKS cache TTL in seconds
            default_advertised_scopes: Optional list of OAuth scopes to advertise on the
                entry-level 401 ``WWW-Authenticate`` challenge and as
                ``scopes_supported`` in the Protected Resource Metadata document
                (RFC 9728). MCP 2025-11-25 §Authorization says servers SHOULD
                include a ``scope`` parameter so clients can apply the
                principle-of-least-privilege scope-selection strategy. Per
                MCP §Authorization L347, this represents the **minimum scope
                set for basic functionality** — additional scopes get
                requested incrementally via per-tool 403 ``insufficient_scope``
                step-up at runtime. Each token must conform to RFC 6750 §3
                grammar (validated at construction); duplicates are removed
                preserving first-seen order. When omitted, no ``scope`` is
                advertised; clients fall back to the spec selection strategy.
                Also configurable via the
                ``MCP_RESOURCE_SERVER_DEFAULT_ADVERTISED_SCOPES`` env var
                (space-separated; explicit kwarg wins).

        Raises:
            ValueError: If required fields not provided via params or env vars,
                or if any advertised scope token violates RFC 6750 §3.

        Future extension — ``required_scopes`` (FastMCP-shaped):
            A future ``required_scopes`` field could enforce a server-level
            minimum scope set at token-validation time (i.e. tokens missing
            those scopes would be rejected with ``invalid_token`` before any
            tool dispatches). ``default_advertised_scopes`` would then fall
            back to ``required_scopes`` when unset, mirroring FastMCP's
            ``valid_scopes → required_scopes → []`` chain (jlowin/fastmcp
            PR #1717). The validation gate would live in ``validate_token``;
            the advertisement-fallback would live in
            ``_build_resource_metadata`` and the middleware's
            ``_create_401_response`` (where the validator's
            ``default_advertised_scopes`` is read today). Non-breaking
            addition — existing users continue to see
            ``default_advertised_scopes`` drive both surfaces.

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
            self.canonical_url = canonical_url
        elif settings.resource_server.canonical_url is not None:
            self.canonical_url = settings.resource_server.canonical_url
        else:
            raise ValueError(
                "'canonical_url' required (parameter or MCP_RESOURCE_SERVER_CANONICAL_URL environment variable)"
            )

        if authorization_servers is not None:
            configs = authorization_servers
        elif settings.resource_server.authorization_servers:
            configs = settings.resource_server.to_authorization_server_entries()
        else:
            raise ValueError(
                "'authorization_servers' required (parameter or MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS environment variable)"
            )

        # Resolve advertised scopes: explicit kwarg wins, else env var via
        # MCPSettings (see settings.py field_validator that parses the
        # space-separated string). Either path runs through the same
        # RFC 6750 §3 validator — malformed tokens raise ValueError at
        # construction rather than corrupting the WWW-Authenticate header
        # at runtime.
        raw_scopes: list[str] | None = (
            default_advertised_scopes
            if default_advertised_scopes is not None
            else settings.resource_server.default_advertised_scopes
        )
        self.default_advertised_scopes = _validate_advertised_scopes(raw_scopes)

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
        # RFC 9728 §3: ``scopes_supported`` is OPTIONAL but provides clients
        # with the fallback scope set when the WWW-Authenticate ``scope``
        # parameter is absent. MCP 2025-11-25 §Authorization explicitly
        # references this fallback in its scope-selection strategy.
        #
        # Future seam: a ``required_scopes`` field (token-validation gate,
        # FastMCP-shaped) would chain in here as
        # ``self.default_advertised_scopes or self.required_scopes`` — see
        # this class's __init__ docstring for the full extension sketch.
        if self.default_advertised_scopes:
            metadata["scopes_supported"] = list(self.default_advertised_scopes)
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
