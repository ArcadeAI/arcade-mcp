"""
JWT-based token verification provider.

Implements OAuth 2.1 Resource Server token validation using JWT with JWKS.
"""

import time
from typing import Any, cast

import httpx
from jose import jwk, jwt
from pydantic import BaseModel, Field

from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)
from arcade_mcp_server.settings import MCPSettings


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


# Supported asymmetric JWT signature algorithms
# Note: Only asymmetric algorithms supported - JWKS requires public key cryptography
# Symmetric algorithms (HS256/384/512) use shared secrets, not JWKS
SUPPORTED_ALGORITHMS = {
    "RS256",
    "RS384",
    "RS512",  # RSA
    "ES256",
    "ES384",
    "ES512",  # ECDSA (Elliptic Curve)
    "PS256",
    "PS384",
    "PS512",  # RSA-PSS
}


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
            audience="https://mcp.example.com/mcp",
        )
        ```
    """

    def __init__(
        self,
        jwks_uri: str | None = None,
        issuer: str | list[str] | None = None,
        audience: str | None = None,
        algorithm: str = "RS256",
        cache_ttl: int = 3600,
        verify_options: JWTVerifyOptions | None = None,
    ):
        """Initialize JWT verifier with optional env var support.

        Args:
            jwks_uri: URL to fetch JWKS (or MCP_SERVER_AUTH_JWKS_URI)
            issuer: Token issuer or list of issuers (or MCP_SERVER_AUTH_ISSUER)
            audience: Token audience (or MCP_SERVER_AUTH_CANONICAL_URL)
            algorithm: Signature algorithm (or MCP_SERVER_AUTH_ALGORITHM). Default RS256.
            cache_ttl: JWKS cache TTL in seconds
            verify_options: JWT verification options (or MCP_SERVER_AUTH_VERIFY_*)

        Raises:
            ValueError: If required fields not provided, algorithm unsupported, or verify_aud is True but audience is None

        Example:
            ```python
            # Option 1: Use environment variables
            auth = JWTVerifier()

            # Option 2: Explicit parameters
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            # Option 3: Multiple issuers
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer=["https://auth1.example.com", "https://auth2.example.com"],
                audience="https://mcp.example.com/mcp",
            )

            # Option 4: Different algorithm
            auth = JWTVerifier(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                algorithm="ES256",
            )
            ```
        """
        settings = MCPSettings.from_env()
        auth_settings = settings.server_auth

        # Environment variables take precedence
        jwks_uri = auth_settings.jwks_uri or jwks_uri
        issuer = auth_settings.issuer or issuer
        audience = auth_settings.canonical_url or audience

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
        if not jwks_uri:
            raise ValueError("jwks_uri required (parameter or MCP_SERVER_AUTH_JWKS_URI)")
        if not issuer:
            raise ValueError("issuer required (parameter or MCP_SERVER_AUTH_ISSUER)")

        # Validate algorithm is supported and asymmetric
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Supported asymmetric algorithms: {', '.join(sorted(SUPPORTED_ALGORITHMS))}"
            )

        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.algorithms = [algorithm]  # Keep as list for jwt.decode compatibility
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

        Security: Validates that token algorithm and key algorithm match the
        configured algorithm to prevent algorithm confusion attacks.

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

                # Validate key algorithm matches configuration
                if key_alg and key_alg != self.algorithm:
                    raise InvalidTokenError(
                        f"Key algorithm '{key_alg}' doesn't match "
                        f"configured algorithm '{self.algorithm}'"
                    )

                # Use configured algorithm (don't trust the key)
                key_obj = jwk.construct(key_data, algorithm=self.algorithm)
                return key_obj.to_pem().decode("utf-8")

        raise InvalidTokenError("No matching key found in JWKS")

    def _decode_token(self, token: str, signing_key: str) -> dict[str, Any]:
        """Decode and verify the JWT token.

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
            "verify_signature": True,  # Always verify signature
            "verify_exp": self.verify_options.verify_exp,
            "verify_iat": self.verify_options.verify_iat,
            "verify_aud": self.verify_options.verify_aud,
            "verify_iss": self.verify_options.verify_iss,
        }

        # Handle multi-issuer by trying each one
        if isinstance(self.issuer, list):
            last_error = None
            for iss in self.issuer:
                try:
                    return cast(
                        dict[str, Any],
                        jwt.decode(
                            token,
                            signing_key,
                            algorithms=self.algorithms,
                            issuer=iss,
                            options=decode_options,
                            audience=self.audience,
                        ),
                    )
                except jwt.JWTClaimsError as e:
                    last_error = e
                    continue
            # No issuer matched
            raise InvalidTokenError(
                f"Token issuer not in allowed issuers: {self.issuer}"
            ) from last_error

        # Single issuer - let library handle validation
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                signing_key,
                algorithms=self.algorithms,
                issuer=self.issuer,
                options=decode_options,
                audience=self.audience,
            ),
        )

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
        """Extract client ID from decoded token per OAuth 2.0 spec.

        OAuth 2.0 clients can be identified through several claims:
        1. client_id - Standard OAuth 2.0 client identifier
        2. azp (Authorized Party) - OIDC claim for the party to which token was issued

        Note: We do NOT fall back to 'sub' as it represents the end user,
        not the client application. Conflating these violates the OAuth model.

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
        - Token signature using JWKS public key (MANDATORY)
        - Expiration (exp claim) (MANDATORY)
        - Issued-at time (iat claim) (MANDATORY)
        - Issuer (iss claim) matches configured issuer(s) (MANDATORY)
        - Audience (aud claim) if configured (CONDITIONAL)
        - Subject (sub claim) exists (MANDATORY)

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

            # TODO: Determine if this user is allowed to access this MCP server

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
