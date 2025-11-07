"""
WorkOS AuthKit provider for arcade-mcp-server.

Provides seamless integration with WorkOS AuthKit including:
- Automatic JWT configuration for AuthKit
- OAuth 2.0 Protected Resource Metadata
- Authorization server metadata forwarding
- Dynamic Client Registration support
"""

from pydantic import AnyHttpUrl, BaseModel, Field

from arcade_mcp_server.server_auth.providers.remote import RemoteOAuthProvider


class AuthKitProviderSettings(BaseModel):
    """Settings for AuthKit provider."""

    authkit_domain: AnyHttpUrl = Field(
        ...,
        description="Your AuthKit domain (e.g., https://your-app.authkit.app)",
    )
    canonical_url: AnyHttpUrl = Field(
        ...,
        description="Canonical URL of this MCP server",
    )


class AuthKitProvider(RemoteOAuthProvider):
    """WorkOS AuthKit authentication provider.

    This provider implements WorkOS AuthKit integration for MCP servers with:
    - Automatic JWT verification configuration
    - OAuth 2.0 Protected Resource Metadata
    - Authorization server metadata forwarding
    - Dynamic Client Registration support

    **IMPORTANT SETUP REQUIREMENTS:**

    1. Enable Dynamic Client Registration in WorkOS Dashboard:
       - Go to Applications → Configuration
       - Toggle "Dynamic Client Registration" to enabled

    2. Configure your MCP server URL as a redirect URI:
       - Add your server URL to the Redirects tab in WorkOS dashboard
       - This is needed for OAuth callback handling

    For detailed setup instructions, see:
    https://workos.com/docs/authkit/mcp/integrating/token-verification

    Example:
        ```python
        from arcade_mcp_server import MCPApp
        from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider

        # Create AuthKit provider (JWT verifier created automatically)
        auth = AuthKitProvider(
            authkit_domain="https://your-app.authkit.app",
            canonical_url="https://your-mcp-server.com",
        )

        # Use with MCPApp
        app = MCPApp(
            name="my_server",
            auth=auth,
            canonical_url="https://your-mcp-server.com",
        )
        ```

    The provider automatically:
    - Configures JWT verification for AuthKit tokens
    - Sets up OAuth discovery metadata pointing to AuthKit
    - Validates tokens on every request
    - Extracts user information from token claims
    """

    def __init__(
        self,
        authkit_domain: str,
        canonical_url: str,
        cache_ttl: int = 3600,
    ):
        """Initialize AuthKit provider.

        Args:
            authkit_domain: Your AuthKit domain (e.g., "https://your-app.authkit.app")
            canonical_url: Canonical URL of this MCP server
            cache_ttl: JWKS cache time-to-live in seconds (default: 3600)

        Note:
            WorkOS AuthKit does not implement RFC 8707 (Resource Indicators) by default,
            so audience validation is disabled.
        """
        # Validate settings
        settings = AuthKitProviderSettings(
            authkit_domain=authkit_domain,
            canonical_url=canonical_url,
        )

        # Normalize URLs (remove trailing slashes)
        self.authkit_domain = str(settings.authkit_domain).rstrip("/")
        self.canonical_url = str(settings.canonical_url).rstrip("/")

        # AuthKit-specific endpoints
        jwks_uri = f"{self.authkit_domain}/oauth2/jwks"
        issuer = self.authkit_domain

        # Initialize RemoteOAuthProvider with AuthKit configuration
        super().__init__(
            jwks_uri=jwks_uri,
            issuer=issuer,
            audience=None,  # AuthKit doesn't use audience claim - skips validation
            authorization_server=self.authkit_domain,
            algorithms=["RS256"],
            cache_ttl=cache_ttl,
        )

    def supports_authorization_server_metadata_forwarding(self) -> bool:
        """AuthKit supports authorization server metadata forwarding."""
        return True

    def get_authorization_server_metadata_url(self) -> str:
        """Get the URL for AuthKit's authorization server metadata.

        This is used by the server to forward AuthKit's metadata to clients,
        allowing clients to discover OAuth endpoints automatically.

        Returns:
            URL to AuthKit's authorization server metadata endpoint
        """
        return f"{self.authkit_domain}/.well-known/oauth-authorization-server"
