"""ASGI middleware for MCP Resource Server authentication."""

from urllib.parse import urlparse, urlunparse

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from arcade_mcp_server.resource_server.base import (
    AuthenticationError,
    InvalidTokenError,
    ResourceOwner,
    ResourceServerValidator,
    TokenExpiredError,
)


class ResourceServerMiddleware:
    """ASGI middleware that validates Bearer tokens on every HTTP request.

    Validates tokens per MCP specification:
    - Checks Authorization header for Bearer token
    - Validates token on every request
    - Returns 401 with WWW-Authenticate header if authentication fails
    - Stores authenticated resource owner in scope for downstream use to lift
      tool-auth and tool-secrets restrictions

    The WWW-Authenticate header includes:
    - resource_metadata URL for OAuth discovery (if validator supports it)
    - error and error_description for token validation failures (RFC 6750)
    """

    def __init__(
        self,
        app: ASGIApp,
        validator: ResourceServerValidator,
        canonical_url: str | None,
    ):
        """Initialize the Resource Server middleware.

        Args:
            app: ASGI application to wrap
            validator: Token validator for access token validation
            canonical_url: Canonical URL of this MCP server (for OAuth metadata).
                          Required only for validators that support OAuth discovery.
        """
        self.app = app
        self.validator = validator
        self.canonical_url = canonical_url

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with authentication.

        For HTTP requests:
        1. Allow CORS preflight OPTIONS requests to pass through
        2. Extract Bearer token from Authorization header
        3. Validate token (on EVERY request - no caching)
        4. Store authenticated resource owner in scope
        5. Pass to wrapped app

        For non-HTTP requests, pass through without auth.
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Allow CORS preflight requests to pass through without authentication.
        # Browsers send OPTIONS requests without Authorization headers to check
        # if the cross-origin request is allowed before sending the actual request.
        if request.method == "OPTIONS":
            response = self._create_cors_preflight_response()
            await response(scope, receive, send)
            return

        try:
            resource_owner = await self._authenticate_request(request)

            # Store in scope for downstream usage & continue to app execution
            scope["resource_owner"] = resource_owner
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

    async def _authenticate_request(self, request: Request) -> ResourceOwner:
        """Extract and validate Bearer token from Authorization header.

        Args:
            request: Starlette request object

        Returns:
            ResourceOwner from validated token

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

        return await self.validator.validate_token(token)

    def _build_metadata_url(self) -> str:
        """Build the OAuth Protected Resource Metadata URL per RFC 9728.

        For example, for a canonical_url of "https://example.com/mcp" the metadata URL is:
        "https://example.com/.well-known/oauth-protected-resource/mcp"

        Returns:
            Metadata URL
        """
        if not self.canonical_url:
            return ""

        parsed = urlparse(self.canonical_url)
        # Insert well-known path after host, with resource path as suffix
        well_known_path = f"/.well-known/oauth-protected-resource{parsed.path}"
        return urlunparse((parsed.scheme, parsed.netloc, well_known_path, "", "", ""))

    def _create_cors_preflight_response(self) -> Response:
        """Create a CORS preflight response for OPTIONS requests.

        Returns:
            Response with 204 status and CORS headers
        """
        return Response(
            content=None,
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, Accept",
                "Access-Control-Expose-Headers": "WWW-Authenticate, Mcp-Session-Id",
                "Access-Control-Max-Age": "86400",  # 24 hr
            },
        )

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
        www_auth_parts = []

        # Add resource metadata URL if validator supports discovery (RFC 9728)
        if self.validator.supports_oauth_discovery() and self.canonical_url:
            metadata_url = self._build_metadata_url()
            www_auth_parts.append(f'resource_metadata="{metadata_url}"')

        # Add error details if token validation failed (RFC 6750)
        if error:
            www_auth_parts.append(f'error="{error}"')
        if error_description:
            www_auth_parts.append(f'error_description="{error_description}"')

        www_auth_value = "Bearer " + ", ".join(www_auth_parts)

        return Response(
            content="Unauthorized",
            status_code=401,
            headers={
                "WWW-Authenticate": www_auth_value,
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, Accept",
                "Access-Control-Expose-Headers": "WWW-Authenticate, Mcp-Session-Id",
            },
        )
