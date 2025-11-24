"""
JWT-based token verification provider.

Implements OAuth 2.1 Resource Server token validation using JWT with JWKS.
"""

import time
from typing import Any, cast

import httpx
from jose import jwk, jwt

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    JWTVerifyOptions,
    ServerAuthProvider,
    TokenExpiredError,
)

# Note: Only asymmetric algorithms supported
SUPPORTED_ALGORITHMS = {
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
}


class JWTVerifier(ServerAuthProvider):
    def __init__(
        self,
        jwks_uri: str,
        issuer: str | list[str],
        audience: str | list[str],
        algorithm: str = "RS256",
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize JWT verifier

        This provider is for simple, explicit token validation.

        Args:
            jwks_uri: URL to fetch JWKS
            issuer: Token issuer or list of allowed issuers
            audience: Token audience or list of allowed audiences (typically your MCP server's canonical URL)
            algorithm: Signature algorithm. Default RS256.
            cache_ttl: JWKS cache TTL in seconds
            verify_options: JWT verification options

        Raises:
            ValueError: If required fields not provided, algorithm unsupported, or verify_aud is True but audience is None

        Example:
            ```python
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            # Multiple issuers
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer=["https://auth1.example.com", "https://auth2.example.com"],
                audience="https://mcp.example.com/mcp",
            )

            # Multiple audiences (e.g., URL migration)
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com/mcp", "https://new-mcp.example.com/mcp"],
            )

            # Different algorithm
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                algorithm="ES256",
            )
            ```
        """
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Supported asymmetric algorithms: {', '.join(sorted(SUPPORTED_ALGORITHMS))}"
            )

        if verify_options is None:
            verify_options = JWTVerifyOptions()

        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.verify_options = verify_options

        self._cache_ttl = cache_ttl
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._jwks_cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS with caching.

        Returns:
            JWKS dictionary containing public keys

        Raises:
            AuthenticationError: If JWKS cannot be fetched
        """
        current_time = time.time()

        # Use cached JWKS if it's still valid
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
            Signing key in PEM format

        Raises:
            InvalidTokenError: If no matching key found or algorithm mismatch
        """
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        token_alg = unverified_header.get("alg")

        # Validate token algorithm matches configuration (prevent algorithm confusion)
        if token_alg and token_alg != self.algorithm:
            raise InvalidTokenError(
                f"Token algorithm '{token_alg}' doesn't match "
                f"configured algorithm '{self.algorithm}'"
            )

        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                key_alg = key_data.get("alg")

                if key_alg and key_alg != self.algorithm:
                    raise InvalidTokenError(
                        f"Key algorithm '{key_alg}' doesn't match "
                        f"configured algorithm '{self.algorithm}'"
                    )

                key_obj = jwk.construct(key_data, algorithm=self.algorithm)
                return key_obj.to_pem().decode("utf-8")

        raise InvalidTokenError("No matching key found in JWKS")

    def _decode_token(self, token: str, signing_key: str) -> dict[str, Any]:
        """Decode and verify the provided JWT token.

        Args:
            token: JWT token
            signing_key: Public key in PEM format

        Returns:
            Decoded token claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.JWTClaimsError: Token claims validation failed (audience/issuer mismatch)
            jwt.JWTError: Token is invalid
        """
        decode_options = {
            "verify_signature": True,  # We always verify signature. Impossible to disable.
            "verify_exp": self.verify_options.verify_exp,
            "verify_iat": self.verify_options.verify_iat,
            "verify_aud": False,  # We'll validate manually so that we can support multi-audience
            "verify_iss": False,  # We'll validate manually for better multi-issuer handling
        }

        # Decode token once without aud/iss validation
        decoded = cast(
            dict[str, Any],
            jwt.decode(
                token,
                signing_key,
                algorithms=[self.algorithm],
                options=decode_options,
            ),
        )

        # Manually validate issuer (if flag is enabled)
        if self.verify_options.verify_iss:
            token_iss = decoded.get("iss")
            if isinstance(self.issuer, list):
                if token_iss not in self.issuer:
                    raise InvalidTokenError(
                        f"Token issuer '{token_iss}' not in allowed issuers: {self.issuer}"
                    )
            else:
                if token_iss != self.issuer:
                    raise InvalidTokenError(
                        f"Token issuer '{token_iss}' doesn't match expected '{self.issuer}'"
                    )

        # Manually validate audience (if flag is enabled)
        if self.verify_options.verify_aud:
            token_aud = decoded.get("aud")
            token_audiences = [token_aud] if isinstance(token_aud, str) else (token_aud or [])
            expected_audiences = (
                [self.audience] if isinstance(self.audience, str) else self.audience
            )

            # Token is valid if any of its aud values match any of our expected values
            if not (set(token_audiences) & set(expected_audiences)):
                raise InvalidTokenError(
                    f"Token audience {token_aud} doesn't match expected {self.audience}"
                )

        return decoded

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

    def _extract_client_id(self, decoded: dict[str, Any]) -> str | None:
        """Extract client ID from decoded token.

        Args:
            decoded: Decoded token claims

        Returns:
            Client identifier or "unknown" if no client claim found
        """
        client_id = (
            decoded.get("client_id") or decoded.get("azp") or decoded.get("sub") or "unknown"
        )

        return client_id

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate JWT and return authenticated user.

        Validates:
        - Token signature using JWKS public key
        - Subject (sub claim) exists
        - Expiration (exp claim) (if verify_options.verify_exp is True, default True)
        - Issued-at time (iat claim) (if verify_options.verify_iat is True, default True)
        - Issuer (iss claim) matches configured issuer(s) (if verify_options.verify_iss is True, default True)
        - Audience (aud claim) matches configured audience(s) (if verify_options.verify_aud is True, default True)

        Note: All verify_options default to True, so by default all validations are enabled
        for max security.

        Args:
            token: JWT Bearer token

        Returns:
            AuthenticatedUser with user_id, client_id, and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature, algorithm, audience, or issuer is invalid
            AuthenticationError: Other validation errors
        """
        try:
            jwks = await self._fetch_jwks()
            signing_key = self._find_signing_key(jwks, token)
            decoded = self._decode_token(token, signing_key)
            user_id = self._extract_user_id(decoded)
            client_id = self._extract_client_id(decoded)
            email = decoded.get("email")

            return AuthenticatedUser(
                user_id=user_id,
                client_id=client_id,
                email=email,
                claims=decoded,
            )

        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except jwt.JWTClaimsError as e:
            raise InvalidTokenError(f"Token claims validation failed: {e}") from e
        except jwt.JWTError as e:
            raise InvalidTokenError(f"Invalid token: {e}") from e
        except (InvalidTokenError, TokenExpiredError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
