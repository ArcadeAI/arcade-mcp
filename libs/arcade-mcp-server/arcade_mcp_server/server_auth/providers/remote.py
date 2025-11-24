"""Remote OAuth provider with discovery metadata support for one or more authorization servers."""

from typing import Any

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    AuthorizationServerConfig,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.providers.jwt import JWTVerifier
from arcade_mcp_server.settings import MCPSettings


class RemoteOAuthProvider(ServerAuthProvider):
    """OAuth provider with discovery metadata supporting one or more authorization servers.

    This Resource Server implementation validates JWT tokens from one or more
    authorization servers and provides OAuth 2.0 Protected Resource Metadata
    for discovery.
    """

    def __init__(
        self,
        authorization_servers: list[AuthorizationServerConfig] | None = None,
        canonical_url: str | None = None,
        cache_ttl: int = 3600,
    ):
        """Initialize remote OAuth provider.

        Supports environment variable configuration via MCP_SERVER_AUTH_* variables.
        Environment variables take precedence over parameters.

        Args:
            authorization_servers: List of authorization server configurations
            canonical_url: MCP server canonical URL (or MCP_SERVER_AUTH_CANONICAL_URL)
            cache_ttl: JWKS cache TTL in seconds

        Raises:
            ValueError: If required fields not provided via env vars or parameters

        Example:
            ```python
            # Option 1: Use environment variables
            # Set MCP_SERVER_AUTH_CANONICAL_URL and MCP_SERVER_AUTH_AUTHORIZATION_SERVERS env vars
            auth = RemoteOAuthProvider()

            # Option 2: Single Auth Server
            auth = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
            )

            # Option 3: Multiple Auth Servers
            auth = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://workos.authkit.app",
                        issuer="https://workos.authkit.app",
                        jwks_uri="https://workos.authkit.app/oauth2/jwks",
                        verify_options=JWTVerifyOptions(verify_aud=False),
                    ),
                    AuthorizationServerConfig(
                        authorization_server_url="https://github.com/login/oauth",
                        issuer="https://github.com",
                        jwks_uri="https://token.actions.githubusercontent.com/.well-known/jwks",
                    ),
                ],
            )
            ```
        """
        settings = MCPSettings.from_env()

        self.cache_ttl = cache_ttl

        # Environment variables (loaded into settings) take precedence
        if settings.server_auth.canonical_url is not None:
            self.canonical_url = settings.server_auth.canonical_url
        elif canonical_url is not None:
            self.canonical_url = canonical_url
        else:
            raise ValueError(
                "'canonical_url' required (parameter or MCP_SERVER_AUTH_CANONICAL_URL environment variable)"
            )

        if settings.server_auth.authorization_servers:
            configs = settings.server_auth.to_authorization_server_configs()
        elif authorization_servers is not None:
            configs = authorization_servers
        else:
            raise ValueError(
                "'authorization_servers' required (parameter or MCP_SERVER_AUTH_AUTHORIZATION_SERVERS environment variable)"
            )

        self._verifiers = self._create_verifiers(configs)

    def _create_verifiers(self, configs: list[AuthorizationServerConfig]) -> dict[str, JWTVerifier]:
        """Create a mapping of authorization server URLs to their JWTVerifier instances.

        Args:
            configs: List of authorization server configurations

        Returns:
            Dictionary that maps authorization_server_url to its JWTVerifier instance
        """
        verifiers = {}

        for config in configs:
            verifiers[config.authorization_server_url] = JWTVerifier(
                jwks_uri=config.jwks_uri,
                issuer=config.issuer,
                audience=self.canonical_url,
                algorithm=config.algorithm,
                cache_ttl=self.cache_ttl,
                verify_options=config.verify_options,
            )

        return verifiers

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate the given token against each configured authorization server.

        Tries each verifier until one succeeds. If all fail, then raises InvalidTokenError.

        Error handling strategy:
        - TokenExpiredError: Raise immediately. If any verifier raises this, the token
          is expired for all authorization servers (expiration is universal). No point
          trying other verifiers.
        - InvalidTokenError/AuthenticationError: Continue to next verifier b/c another
          Auth Server might accept the token. These errors indicate wrong issuer, audience,
          or signature mismatch.

        Args:
            token: JWT Bearer token

        Returns:
            AuthenticatedUser with user_id, client_id, and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature, algorithm, audience, or issuer is invalid
            AuthenticationError: Other validation errors
        """
        for verifier in self._verifiers.values():
            try:
                return await verifier.validate_token(token)
            except TokenExpiredError:
                raise
            except (InvalidTokenError, AuthenticationError):
                continue

        raise InvalidTokenError("Token validation failed for all configured authorization servers")

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
            "authorization_servers": list(self._verifiers.keys()),
        }
