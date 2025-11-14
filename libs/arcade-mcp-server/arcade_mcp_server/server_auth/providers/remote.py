"""
Remote OAuth provider with discovery metadata support.

Extends JWTVerifier to support OAuth 2.0 Protected Resource Metadata (RFC 9728)
for integration with external identity providers.
"""

from typing import Any

from arcade_mcp_server.server_auth.providers.jwt import JWTVerifier, JWTVerifyOptions


class RemoteOAuthProvider(JWTVerifier):
    """OAuth provider with discovery metadata pointing to external auth server.

    Use this when integrating with external identity providers that support
    Dynamic Client Registration (DCR), such as WorkOS, Descope, or other
    modern OAuth providers.

    This provider:
    1. Validates JWT tokens (inherits from JWTVerifier)
    2. Provides OAuth Protected Resource Metadata for MCP client discovery
    3. Points clients to the external authorization server for token acquisition

    Example:
        ```python
        auth = RemoteOAuthProvider(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com",
            authorization_server="https://auth.example.com",
        )
        ```
    """

    def __init__(
        self,
        jwks_uri: str,
        issuer: str,
        audience: str | None,
        authorization_server: str,
        authorization_server_metadata_url: str | None = None,
        algorithms: list[str] | None = None,
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize remote OAuth provider.

        Args:
            jwks_uri: URL to fetch JSON Web Key Set
            issuer: Expected token issuer (iss claim)
            audience: Expected token audience (aud claim) - MCP server's canonical URL.
                      If None, verify_aud must be set to False in verify_options.
            authorization_server: URL of the external authorization server
            authorization_server_metadata_url: URL of the external authorization server metadata if the provider supports metadata forwarding
            algorithms: Allowed signature algorithms (default: ["RS256"])
            cache_ttl: JWKS cache time-to-live in seconds (default: 3600)
            verify_options: Options controlling which claims to verify. All default to True for security.

                           Example for providers without audience support (e.g., AuthKit):
                           ```python
                           auth = RemoteOAuthProvider(
                               jwks_uri="https://auth.example.com/.well-known/jwks.json",
                               issuer="https://auth.example.com",
                               audience=None,
                               authorization_server="https://auth.example.com",
                               verify_options=JWTVerifyOptions(verify_aud=False),
                           )
                           ```
        """
        super().__init__(jwks_uri, issuer, audience, algorithms, cache_ttl, verify_options)
        self.authorization_server = authorization_server
        self.authorization_server_metadata_url = authorization_server_metadata_url

    def supports_oauth_discovery(self) -> bool:
        """This provider supports OAuth discovery."""
        return True

    def supports_authorization_server_metadata_forwarding(self) -> bool:
        """Whether this provider supports forwarding authorization server metadata."""
        return self.authorization_server_metadata_url is not None

    def get_authorization_server_metadata_url(self) -> str | None:
        """Get the URL of the external authorization server metadata.

        Returns:
            URL of the external authorization server metadata, or None if not supported
        """
        return self.authorization_server_metadata_url

    def get_resource_metadata(self, canonical_url: str) -> dict[str, Any]:
        """Return RFC 9728 Protected Resource Metadata.

        This metadata tells MCP clients:
        1. What resource this server protects (canonical URL)
        2. Which authorization server(s) can issue tokens for this resource

        Args:
            canonical_url: Canonical URL of this MCP server

        Returns:
            Dictionary containing resource metadata per RFC 9728
        """
        return {
            "resource": canonical_url,
            "authorization_servers": [self.authorization_server],
        }
