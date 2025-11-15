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
            canonical_url="https://mcp.example.com",
            authorization_server="https://auth.example.com",
        )
        ```
    """

    def __init__(
        self,
        jwks_uri: str,
        issuer: str,
        canonical_url: str,
        authorization_server: str,
        algorithms: list[str] | None = None,
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize remote OAuth provider.

        Args:
            jwks_uri: URL to fetch JSON Web Key Set
            issuer: Expected token issuer (iss claim)
            canonical_url: Canonical URL of the MCP server (used as JWT audience claim).
                          Required for OAuth discovery (RFC 9728).
            authorization_server: URL of the external authorization server
            algorithms: Allowed signature algorithms (default: ["RS256"])
            cache_ttl: JWKS cache time-to-live in seconds (default: 3600)
            verify_options: Options controlling which claims to verify. All default to True for security.

        Example:
            ```python
            auth = RemoteOAuthProvider(
                jwks_uri="https://your-app.authkit.app/oauth2/jwks",
                issuer="https://your-app.authkit.app",
                canonical_url="http://127.0.0.1:8000/mcp",
                authorization_server="https://your-app.authkit.app",
                algorithms=["RS256"],
                verify_options=JWTVerifyOptions(
                    verify_aud=False,
                ),
            )
            ```
        """
        super().__init__(jwks_uri, issuer, canonical_url, algorithms, cache_ttl, verify_options)
        self.canonical_url = canonical_url
        self.authorization_server = authorization_server

    def supports_oauth_discovery(self) -> bool:
        """This provider supports OAuth discovery."""
        return True

    def get_resource_metadata(self) -> dict[str, Any]:
        """Return RFC 9728 Protected Resource Metadata.

        This metadata tells MCP clients:
        1. What resource this server protects (canonical URL)
        2. Which authorization server(s) can issue tokens for this resource

        Returns:
            Dictionary containing resource metadata per RFC 9728
        """
        return {
            "resource": self.canonical_url,
            "authorization_servers": [self.authorization_server],
        }
