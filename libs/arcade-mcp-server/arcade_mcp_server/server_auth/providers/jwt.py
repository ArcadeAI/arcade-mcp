"""
JWT-based token verification provider.

Implements OAuth 2.1 Resource Server token validation using JWT with JWKS.
"""

import time
from typing import Any, cast

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel, Field

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)


class JWTVerifyOptions(BaseModel):
    """Options for JWT token verification.

    All validations are enabled by default for security.
    Set to False to disable specific validations for non-compliant authorization servers.

    Note: Token signature verification is always enabled and cannot be disabled.
    """

    verify_exp: bool = Field(
        default=True,
        description="Verify token expiration (exp claim)",
    )
    verify_iat: bool = Field(
        default=True,
        description="Verify issued-at time (iat claim)",
    )
    verify_aud: bool = Field(
        default=True,
        description="Verify audience claim (aud claim)",
    )
    verify_iss: bool = Field(
        default=True,
        description="Verify issuer claim (iss claim)",
    )


class JWTVerifier(ServerAuthProvider):
    """JWT-based token verification with JWKS key fetching.

    This provider validates JWT access tokens by:
    1. Fetching public keys from a JWKS endpoint
    2. Verifying the token signature using the appropriate key
    3. Validating standard claims (exp, iss, aud)
    4. Extracting user information from claims

    The JWKS is cached to avoid fetching on every request, with a configurable TTL.

    Example:
        ```python
        auth = JWTVerifier(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com",
        )
        ```
    """

    def __init__(
        self,
        jwks_uri: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        algorithms: list[str] | None = None,
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize JWT verifier with optional env var support.

        Args:
            jwks_uri: URL to fetch JWKS (or MCP_SERVER_AUTH_JWKS_URI)
            issuer: Token issuer (or MCP_SERVER_AUTH_ISSUER)
            audience: Token audience (or MCP_SERVER_AUTH_CANONICAL_URL)
            algorithms: Signature algorithms (or MCP_SERVER_AUTH_ALGORITHMS)
            cache_ttl: JWKS cache TTL
            verify_options: JWT verification options (or MCP_SERVER_AUTH_VERIFY_*)

        Raises:
            ValueError: If required fields not provided or verify_aud is True but audience is None

        Example:
            ```python
            # Option 1: Use environment variables
            auth = JWTVerifier()

            # Option 2: Explicit parameters
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            # Option 3: Disable audience verification
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                verify_options=JWTVerifyOptions(verify_aud=False),
            )
            ```
        """
        from arcade_mcp_server.settings import MCPSettings

        settings = MCPSettings.from_env()
        auth_settings = settings.server_auth

        # Environment variables take precedence
        jwks_uri = auth_settings.jwks_uri or jwks_uri
        issuer = auth_settings.issuer or issuer
        audience = auth_settings.canonical_url or audience

        if auth_settings.algorithms:
            algorithms = auth_settings.algorithms
        elif algorithms is None:
            algorithms = ["RS256"]

        if verify_options is None:
            verify_options = JWTVerifyOptions(
                verify_aud=auth_settings.verify_aud,
                verify_exp=auth_settings.verify_exp,
                verify_iat=auth_settings.verify_iat,
                verify_iss=auth_settings.verify_iss,
            )

        # Validate required fields
        if not jwks_uri:
            raise ValueError("jwks_uri required (parameter or MCP_SERVER_AUTH_JWKS_URI)")
        if not issuer:
            raise ValueError("issuer required (parameter or MCP_SERVER_AUTH_ISSUER)")

        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self._cache_ttl = cache_ttl
        self.verify_options = verify_options

        if self.verify_options.verify_aud and self.audience is None:
            raise ValueError("audience must be provided when verify_aud is True")

        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._jwks_cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS asynchronously with caching.

        Returns:
            JWKS dictionary containing public keys

        Raises:
            AuthenticationError: If JWKS cannot be fetched
        """
        current_time = time.time()

        # Return cached JWKS if still valid
        if self._jwks_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._jwks_cache

        try:
            response = await self._http_client.get(self.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._cache_timestamp = current_time
        except httpx.HTTPError as e:
            raise AuthenticationError(f"Failed to fetch JWKS: {e}") from e
        else:
            return self._jwks_cache

    def _find_signing_key(self, jwks: dict[str, Any], token: str) -> Any:
        """Find the signing key from JWKS that matches the token's kid.

        Args:
            jwks: JSON Web Key Set
            token: JWT token

        Returns:
            RSA signing key

        Raises:
            InvalidTokenError: If no matching key is found in JWKS
        """
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return RSAAlgorithm.from_jwk(key_data)

        raise InvalidTokenError("No matching key found in JWKS")

    def _decode_token(self, token: str, signing_key: Any) -> dict[str, Any]:
        """Decode and verify the JWT token.

        Args:
            token: JWT token
            signing_key: RSA public key for verification

        Returns:
            Decoded token claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidAudienceError: Token audience mismatch
            jwt.InvalidIssuerError: Token issuer mismatch
            jwt.InvalidTokenError: Token is invalid
        """
        decode_options = {
            "verify_signature": True,  # Always verify signature
            "verify_exp": self.verify_options.verify_exp,
            "verify_iat": self.verify_options.verify_iat,
            "verify_aud": self.verify_options.verify_aud,
            "verify_iss": self.verify_options.verify_iss,
        }

        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=self.algorithms,
            issuer=self.issuer,
            options=decode_options,
            audience=self.audience,
        )

        return cast(dict[str, Any], decoded)

    def _extract_user_id(self, decoded: dict[str, Any]) -> str:
        """Extract and validate user_id from decoded token.

        Args:
            decoded: Decoded token claims

        Returns:
            User ID from 'sub' claim

        Raises:
            InvalidTokenError: If 'sub' claim is missing
        """
        user_id = decoded.get("sub")
        if not user_id:
            raise InvalidTokenError("Token missing 'sub' claim")
        return cast(str, user_id)

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate JWT and return authenticated user.

        Validates:
        - Token signature using JWKS public key
        - Expiration (exp claim)
        - Issuer (iss claim matches expected issuer)
        - Audience (aud claim matches this MCP server)
        - Subject (sub claim exists)

        Args:
            token: JWT Bearer token

        Returns:
            AuthenticatedUser with user_id from 'sub' claim

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature, audience, or issuer is invalid
            AuthenticationError: Other validation errors
        """
        try:
            jwks = await self._fetch_jwks()
            signing_key = self._find_signing_key(jwks, token)
            decoded = self._decode_token(token, signing_key)
            user_id = self._extract_user_id(decoded)
            email = decoded.get("email")

            # TODO: Determine if this user is allowed to access this MCP server

            return AuthenticatedUser(
                user_id=user_id,
                email=email,
                claims=decoded,
            )

        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except jwt.InvalidAudienceError as e:
            raise InvalidTokenError("Token audience mismatch") from e
        except jwt.InvalidIssuerError as e:
            raise InvalidTokenError("Token issuer mismatch") from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}") from e
        except (InvalidTokenError, TokenExpiredError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
