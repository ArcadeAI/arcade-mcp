"""
JWT-based token verification provider.

Implements OAuth 2.1 Resource Server token validation using JWT with JWKS.
"""

import time
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
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
        jwks_uri: str,
        issuer: str,
        audience: str | None = None,
        algorithms: list[str] | None = None,
        cache_ttl: int = 3600,
    ):
        """Initialize JWT verifier.

        Args:
            jwks_uri: URL to fetch JSON Web Key Set
            issuer: Expected token issuer (iss claim)
            audience: Expected token audience (aud claim) - should be MCP server's canonical URL.
                      If None, audience validation is skipped (for providers like AuthKit
                      that don't implement RFC 8707 Resource Indicators).
            algorithms: Allowed signature algorithms (default: ["RS256"])
            cache_ttl: JWKS cache time-to-live in seconds (default: 3600)
        """
        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self._cache_ttl = cache_ttl

        # Async HTTP client for JWKS fetching
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
            return self._jwks_cache
        except httpx.HTTPError as e:
            raise AuthenticationError(f"Failed to fetch JWKS: {e}") from e

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
            # Fetch JWKS (uses cache if available)
            jwks = await self._fetch_jwks()

            # Decode header to get kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching public key in JWKS
            signing_key = None
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    signing_key = RSAAlgorithm.from_jwk(key_data)
                    break

            if not signing_key:
                raise InvalidTokenError("No matching key found in JWKS")

            # Decode and validate JWT
            # Validates: signature, expiration, issuer, and audience (if provided)
            decode_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": self.audience is not None,  # Only verify if audience is set
                "verify_iss": True,
            }

            decode_kwargs = {
                "algorithms": self.algorithms,
                "issuer": self.issuer,
                "options": decode_options,
            }

            # Only add audience parameter if it's provided
            if self.audience is not None:
                decode_kwargs["audience"] = self.audience

            decoded = jwt.decode(token, signing_key, **decode_kwargs)

            # Extract user info from standard claims
            user_id = decoded.get("sub")
            if not user_id:
                raise InvalidTokenError("Token missing 'sub' claim")

            return AuthenticatedUser(
                user_id=user_id,
                email=decoded.get("email"),
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
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
