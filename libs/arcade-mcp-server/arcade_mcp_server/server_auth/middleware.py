"""ASGI middleware for front-door authentication."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)


class MCPAuthMiddleware:
    """ASGI middleware that validates Bearer tokens on every HTTP request.

    Validates tokens per MCP specification:
    - Checks Authorization header for Bearer token
    - Validates token on every request
    - Returns 401 with WWW-Authenticate header if authentication fails
    - Stores authenticated user in scope for downstream use to lift tool-auth and tool-secrets restrictions

    The WWW-Authenticate header includes:
    - resource_metadata URL for OAuth discovery (if provider supports it)
    - error and error_description for token validation failures (RFC 6750)

    Example:
        ```python
        from starlette.applications import Starlette

        app = Starlette()
        auth_provider = JWTVerifier(...)
        app = MCPAuthMiddleware(app, auth_provider, "https://mcp.example.com")
        ```
    """

    def __init__(
        self,
        app: ASGIApp,
        auth_provider: ServerAuthProvider,
        canonical_url: str | None,
    ):
        """Initialize the server-level auth middleware.

        Args:
            app: ASGI application to wrap
            auth_provider: Authentication provider for token validation
            canonical_url: Canonical URL of this MCP server (for OAuth metadata).
                          Required only for providers that support OAuth discovery.
        """
        self.app = app
        self.auth_provider = auth_provider
        self.canonical_url = canonical_url

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with authentication.

        For HTTP requests:
        1. Extract Bearer token from Authorization header
        2. Validate token (on EVERY request - no caching)
        3. Store authenticated user in scope
        4. Pass to wrapped app

        For non-HTTP requests, pass through without auth.
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        try:
            authenticated_user = await self._authenticate_request(request)

            # Store in scope for downstream usage & continue to app execution
            scope["authenticated_user"] = authenticated_user
            await self.app(scope, receive, send)

        except (TokenExpiredError, InvalidTokenError) as e:
            response = self._create_401_response(
                error="invalid_token",
                error_description=str(e),
            )
            await response(scope, receive, send)

        except AuthenticationError:
            response = self._create_401_response()
            await response(scope, receive, send)

    async def _authenticate_request(self, request: Request) -> AuthenticatedUser:
        """Extract and validate Bearer token from Authorization header.

        Args:
            request: Starlette request object

        Returns:
            AuthenticatedUser from validated token

        Raises:
            AuthenticationError: No token or invalid format
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature/audience/issuer invalid
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise AuthenticationError("No Authorization header")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Invalid Authorization header format.")

        # Remove "Bearer " prefix
        token = auth_header[7:]

        return await self.auth_provider.validate_token(token)

    def _create_401_response(
        self,
        error: str | None = None,
        error_description: str | None = None,
    ) -> Response:
        """Create RFC 6750 + RFC 9728 compliant 401 response.

        The WWW-Authenticate header format follows:
        - RFC 6750 (OAuth 2.0 Bearer Token Usage)
        - RFC 9728 (OAuth 2.0 Protected Resource Metadata)

        Args:
            error: Error code (e.g., "invalid_token")
            error_description: Human-readable error description

        Returns:
            Response with 401 status with WWW-Authenticate header
        """
        www_auth_parts = ["Bearer"]

        # Add resource metadata URL if provider supports discovery (RFC 9728)
        if self.auth_provider.supports_oauth_discovery() and self.canonical_url:
            metadata_url = f"{self.canonical_url}/.well-known/oauth-protected-resource"
            www_auth_parts.append(f'resource_metadata="{metadata_url}"')

        # Add error details if token validation failed (RFC 6750)
        if error:
            www_auth_parts.append(f'error="{error}"')
        if error_description:
            www_auth_parts.append(f'error_description="{error_description}"')

        www_auth_value = ", ".join(www_auth_parts)

        return Response(
            content="Unauthorized",
            status_code=401,
            headers={
                "WWW-Authenticate": www_auth_value,
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, DELETE",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id",
                "Access-Control-Expose-Headers": "WWW-Authenticate, Mcp-Session-Id",
            },
        )
