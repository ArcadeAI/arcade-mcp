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
            canonical_url="https://mcp.example.com/mcp",
            authorization_server="https://auth.example.com",
        )
        ```
    """

    def __init__(
        self,
        jwks_uri: str | None = None,
        issuer: str | list[str] | None = None,
        canonical_url: str | None = None,
        authorization_server: str | None = None,
        algorithm: str = "RS256",
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize remote OAuth provider.

        All parameters can be provided via environment variables (MCP_SERVER_AUTH_*).
        Environment variables take precedence over parameters.

        Args:
            jwks_uri: URL to fetch JWKS (or MCP_SERVER_AUTH_JWKS_URI)
            issuer: Token issuer or list of issuers (or MCP_SERVER_AUTH_ISSUER)
            canonical_url: MCP server canonical URL (or MCP_SERVER_AUTH_CANONICAL_URL)
            authorization_server: Auth server URL (or MCP_SERVER_AUTH_AUTHORIZATION_SERVER)
            algorithm: Signature algorithm (or MCP_SERVER_AUTH_ALGORITHM)
            cache_ttl: JWKS cache TTL in seconds
            verify_options: JWT verification options (or MCP_SERVER_AUTH_VERIFY_* vars)

        Raises:
            ValueError: If required fields not provided via env vars or parameters

        Example:
            ```python
            # Option 1: Use environment variables
            auth = RemoteOAuthProvider()

            # Option 2: Explicit parameters
            auth = RemoteOAuthProvider(
                jwks_uri="https://your-app.authkit.app/oauth2/jwks",
                issuer="https://your-app.authkit.app",
                canonical_url="http://127.0.0.1:8000/mcp",
                authorization_server="https://your-app.authkit.app",
            )

            # Option 3: Multiple issuers
            auth = RemoteOAuthProvider(
                jwks_uri="https://auth.example.com/jwks",
                issuer=["https://auth1.example.com", "https://auth2.example.com"],
                canonical_url="http://127.0.0.1:8000/mcp",
                authorization_server="https://auth1.example.com",
            )
            ```
        """
        from arcade_mcp_server.settings import MCPSettings

        settings = MCPSettings.from_env()
        auth_settings = settings.server_auth

        # Environment variables take precedence
        jwks_uri = auth_settings.jwks_uri or jwks_uri
        issuer = auth_settings.issuer or issuer
        canonical_url = auth_settings.canonical_url or canonical_url
        authorization_server = auth_settings.authorization_server or authorization_server

        if auth_settings.algorithm:
            algorithm = auth_settings.algorithm

        if verify_options is None:
            verify_options = JWTVerifyOptions(
                verify_aud=auth_settings.verify_aud,
                verify_exp=auth_settings.verify_exp,
                verify_iat=auth_settings.verify_iat,
                verify_iss=auth_settings.verify_iss,
            )

        # Validate required fields
        missing = []
        if not jwks_uri:
            missing.append("jwks_uri (MCP_SERVER_AUTH_JWKS_URI)")
        if not issuer:
            missing.append("issuer (MCP_SERVER_AUTH_ISSUER)")
        if not canonical_url:
            missing.append("canonical_url (MCP_SERVER_AUTH_CANONICAL_URL)")
        if not authorization_server:
            missing.append("authorization_server (MCP_SERVER_AUTH_AUTHORIZATION_SERVER)")

        if missing:
            raise ValueError(
                f"RemoteOAuthProvider requires: {', '.join(missing)}. "
                f"Provide via parameters or environment variables."
            )

        super().__init__(jwks_uri, issuer, canonical_url, algorithm, cache_ttl, verify_options)
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
