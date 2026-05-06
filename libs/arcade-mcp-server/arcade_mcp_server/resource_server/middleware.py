"""ASGI middleware for MCP Resource Server authentication."""

import logging
from urllib.parse import urlparse, urlunparse

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from arcade_mcp_server.resource_server.base import (
    AuthenticationError,
    InsufficientScopeError,
    InvalidTokenError,
    ResourceOwner,
    ResourceServerValidator,
    TokenExpiredError,
    _sanitize_rfc6750_quoted_value,
    _validate_resource_metadata_url,
)
from arcade_mcp_server.resource_server.headers import (
    build_insufficient_scope_www_authenticate,
)

logger = logging.getLogger(__name__)

# ASGI scope key for the authenticated resource owner. Established as a
# module-level constant so ``enforce_scopes`` (in scope_enforcement.py)
# can read it without depending on a stringly-typed contract. Pinned by
# tests so renames are deliberate.
RESOURCE_OWNER_SCOPE_KEY = "resource_owner"


class ResourceServerMiddleware:
    """ASGI middleware that validates Bearer tokens on every HTTP request.

    Validates tokens per MCP specification:
    - Checks Authorization header for Bearer token
    - Validates token on every request
    - Returns 401 with WWW-Authenticate header if authentication fails
    - Stores authenticated resource owner in scope for downstream use to lift
      tool-auth and tool-secrets restrictions
    - Catches ``InsufficientScopeError`` raised from downstream handlers
      and translates to RFC 6750 403 ``insufficient_scope`` response

    The WWW-Authenticate header includes:
    - resource_metadata URL for OAuth discovery (if validator supports it)
    - error and error_description for token validation failures (RFC 6750)
    - scope parameter on the entry-401 challenge (validator's
      ``default_challenge_scopes``) and on the 403 step-up challenge
      (operation-required scopes from ``InsufficientScopeError``)
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
            validator: Token validator for access token validation. The
                validator's ``default_challenge_scopes`` attribute drives
                advertisement on the entry-401 ``WWW-Authenticate`` challenge
                (MCP spec SHOULD-rule); ``scopes_supported`` drives the PRM
                document independently. One source of truth, no separate
                parameter on the middleware.
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
            scope[RESOURCE_OWNER_SCOPE_KEY] = resource_owner
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

        except InsufficientScopeError as exc:
            response = self._create_403_insufficient_scope_response(exc)
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

        For a canonical_url of "https://example.com/mcp" the metadata URL is
        "https://example.com/.well-known/oauth-protected-resource/mcp".
        Query components are preserved per RFC 8707 Section 2 ("Query
        components MUST be retained when used") and RFC 9728 Section 3
        (the PRM ``resource`` field MUST match the resource identifier
        the metadata URL was derived from). Fragments are rejected at
        intake by ``_validate_resource_metadata_url`` and never reach
        this builder.

        Returns:
            Metadata URL
        """
        if not self.canonical_url:
            return ""

        parsed = urlparse(self.canonical_url)
        # Insert well-known path after host, with resource path as suffix.
        # ``parsed.query`` is retained per RFC 8707 / RFC 9728.
        well_known_path = f"/.well-known/oauth-protected-resource{parsed.path}"
        return urlunparse((parsed.scheme, parsed.netloc, well_known_path, "", parsed.query, ""))

    def _cors_headers(self) -> dict[str, str]:
        """Shared CORS headers for 401, 403, and OPTIONS preflight responses."""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, Accept, MCP-Protocol-Version",
            "Access-Control-Expose-Headers": "WWW-Authenticate, Mcp-Session-Id, MCP-Protocol-Version",
        }

    def _create_cors_preflight_response(self) -> Response:
        """Create a CORS preflight response for OPTIONS requests.

        Returns:
            Response with 204 status and CORS headers
        """
        headers = self._cors_headers()
        headers["Access-Control-Max-Age"] = "86400"  # 24 hr
        return Response(
            content=None,
            status_code=204,
            headers=headers,
        )

    def _safe_metadata_url_for_emit(self) -> str | None:
        """Resolve the ``resource_metadata`` URL for emit, sanitizing.

        The 401 emit path follows the spec MUST: invalid Bearer tokens
        receive HTTP 401 even when an ancillary parameter cannot be
        rendered. When the canonical URL fails URI validation here
        (a misconfigured operator setting that bypassed intake, e.g.
        a runtime ``self.canonical_url = ...`` mutation), drop the
        ``resource_metadata`` parameter, log a warning, and let the
        401 response continue. Same policy applies to the 403 path
        because the 403 SHOULD-rule includes the parameter; failing
        the response over a misconfigured URL would corrupt the
        spec-mandated step-up flow.

        Returns the validated URL string, or ``None`` when the URL is
        absent or non-conformant.
        """
        if not (self.validator.supports_oauth_discovery() and self.canonical_url):
            return None
        metadata_url = self._build_metadata_url()
        if not metadata_url:
            return None
        try:
            return _validate_resource_metadata_url(metadata_url)
        except ValueError as exc:
            logger.warning(
                "Dropping resource_metadata parameter from WWW-Authenticate "
                "header: canonical URL fails URI validation at emit time. "
                "%s",
                exc,
            )
            return None

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
            error_description: Human-readable error description. Sanitized
                against the RFC 6750 ``error-char`` grammar; non-conformant
                upstream values (e.g., a pyjwt error message containing
                non-ASCII bytes) are dropped via
                ``_sanitize_rfc6750_quoted_value`` so the spec-mandated 401
                response is never blocked by a header-construction failure.

        Returns:
            Response with 401 status and WWW-Authenticate header
        """
        www_auth_parts = []

        # Add resource metadata URL if validator supports discovery (RFC 9728).
        # Sanitize-and-omit on failure: the spec MUST is "401 on invalid
        # Bearer token", and a server-side configuration issue must not
        # block the 401.
        metadata_url = self._safe_metadata_url_for_emit()
        if metadata_url:
            www_auth_parts.append(f'resource_metadata="{metadata_url}"')

        # Add error details if token validation failed (RFC 6750)
        if error:
            sanitized_error = _sanitize_rfc6750_quoted_value(error, field="error")
            if sanitized_error is not None:
                www_auth_parts.append(f'error="{sanitized_error}"')
        if error_description:
            sanitized_description = _sanitize_rfc6750_quoted_value(
                error_description, field="error_description"
            )
            if sanitized_description is not None:
                www_auth_parts.append(f'error_description="{sanitized_description}"')

        # The MCP spec SHOULD-rule: servers advertise the required ``scope``
        # on the WWW-Authenticate challenge so clients can apply the
        # principle-of-least-privilege scope-selection strategy.
        #
        # Per the SEP-835 surface split, the entry-401 challenge advertises
        # ``default_challenge_scopes`` (RFC 6750) which is independent from
        # the PRM document's ``scopes_supported`` (RFC 9728). Operators may
        # pick any of: equal, disjoint, sub/super-sets, or alternative
        # collections. When ``default_challenge_scopes`` is unset we omit
        # ``scope=`` rather than emit ``scope=""``: the empty form would
        # tell compliant OAuth clients to acquire a zero-scope token
        # (semantically wrong and a known cause of empty-scope token loops).
        # Tool-specific scopes are attached to the 403 ``insufficient_scope``
        # response by the handler-level scope check.
        #
        # The validator is the single source of truth: ``ResourceServerValidator``
        # declares ``default_challenge_scopes`` on the ABC so this attribute
        # access is always safe (no defensive ``getattr``).
        challenge = self.validator.default_challenge_scopes
        if challenge:
            scope_value = " ".join(challenge)
            www_auth_parts.append(f'scope="{scope_value}"')

        www_auth_value = "Bearer " + ", ".join(www_auth_parts)

        headers = self._cors_headers()
        headers["WWW-Authenticate"] = www_auth_value

        return Response(
            content="Unauthorized",
            status_code=401,
            headers=headers,
        )

    def _create_403_insufficient_scope_response(self, exc: InsufficientScopeError) -> Response:
        """Create RFC 6750 403 ``insufficient_scope`` response.

        Per the MCP authorization spec section Runtime Insufficient Scope
        Errors: a step-up challenge advertising the operation's required
        scopes. Arcade picks the spec-permitted "minimum approach" emit
        strategy: the header advertises exactly ``exc.required_scopes``
        (operation-required minimum, in caller order). ``granted_scopes``
        on the exception is diagnostic-only metadata for the caller and is
        intentionally NOT echoed into the wire response.

        The strict ``_validate_rfc6750_quoted_value`` policy applies to
        ``error_description``: ``InsufficientScopeError.__init__`` already
        validates at construction, so any value reaching this path that
        fails has bypassed the public constructor. Surfacing such a bug
        loudly via ``ValueError`` is the right call. The inline JSON-RPC
        path in ``MCPServer._handle_call_tool`` wraps the helper call in
        ``try/except ValueError`` and downgrades to a 500-class response
        for the same reason.

        Args:
            exc: ``InsufficientScopeError`` raised by a downstream handler

        Returns:
            Response with 403 status and WWW-Authenticate header
        """
        metadata_url = self._safe_metadata_url_for_emit()

        www_auth_value = build_insufficient_scope_www_authenticate(
            required_scopes=exc.required_scopes,
            resource_metadata_url=metadata_url,
            error_description=exc.error_description,
        )

        headers = self._cors_headers()
        headers["WWW-Authenticate"] = www_auth_value

        return Response(
            content="Insufficient scope",
            status_code=403,
            headers=headers,
        )
