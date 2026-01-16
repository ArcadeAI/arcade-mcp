"""
JWKS-based token validator for MCP Resource Servers.

Implements OAuth 2.1 Resource Server token validation using JWT with JWKS.
"""

import time
from typing import Any, cast

import httpx
from joserfc import jwt
from joserfc.errors import ExpiredTokenError, JoseError
from joserfc.jwk import KeySet
from joserfc.jws import JWSRegistry
from joserfc.registry import HeaderParameter

from arcade_mcp_server.resource_server.base import (
    AccessTokenValidationOptions,
    AuthenticationError,
    InvalidTokenError,
    ResourceOwner,
    ResourceServerValidator,
    TokenExpiredError,
)

SUPPORTED_ALGORITHMS = {
    # RSA
    "RS256",
    "RS384",
    "RS512",
    # ECDSA
    "ES256",
    "ES384",
    "ES512",
    # RSA-PSS
    "PS256",
    "PS384",
    "PS512",
    # EdDSA (RFC 9864)
    "Ed25519",
    "EdDSA",
}

# EdDSA algorithm aliases - joserfc uses "Ed25519" per RFC 9864
EDDSA_ALGORITHMS = {"Ed25519", "EdDSA"}

# Custom JWS registry that allows additional header parameters per RFC 9068 (JWT Access Tokens)
_ACCESS_TOKEN_REGISTRY = JWSRegistry(
    header_registry={
        "iss": HeaderParameter("Issuer", "str"),  # Issuer in header (RFC 9068)
        "aud": HeaderParameter("Audience", "str"),  # Audience in header (RFC 9068)
    },
    algorithms=list(SUPPORTED_ALGORITHMS),
)


class JWKSTokenValidator(ResourceServerValidator):
    """JWKS-based JWT token validator for simple, explicit token validation.

    This validator fetches public keys from a JWKS endpoint and validates
    JWT access tokens against them. Use this when you need direct control
    over token validation without OAuth discovery support.
    """

    def __init__(
        self,
        jwks_uri: str,
        issuer: str | list[str],
        audience: str | list[str],
        algorithm: str = "RS256",
        cache_ttl: int = 3600,
        validation_options: AccessTokenValidationOptions | None = None,
    ):
        """Initialize JWKS token validator.

        Args:
            jwks_uri: URL to fetch JWKS
            issuer: Token issuer or list of allowed issuers
            audience: Token audience or list of allowed audiences (typically your MCP server's canonical URL)
            algorithm: Signature algorithm. Default RS256.
            cache_ttl: JWKS cache TTL in seconds
            validation_options: Access token validation options

        Raises:
            ValueError: If required fields not provided or algorithm unsupported

        Example:
            ```python
            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            # Multiple issuers
            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/jwks",
                issuer=["https://auth1.example.com", "https://auth2.example.com"],
                audience="https://mcp.example.com/mcp",
            )

            # Multiple audiences (e.g., URL migration)
            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com/mcp", "https://new-mcp.example.com/mcp"],
            )

            # Different algorithm
            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                algorithm="ES256",
            )

            # Ed25519 algorithm (for Arcade Intermediate AS)
            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://cloud.arcade.dev/oauth2",
                audience="urn:arcade:mcp",
                algorithm="Ed25519",
            )
            ```
        """
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Supported asymmetric algorithms: {', '.join(sorted(SUPPORTED_ALGORITHMS))}"
            )

        if validation_options is None:
            validation_options = AccessTokenValidationOptions()

        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.validation_options = validation_options

        self._cache_ttl = cache_ttl
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._jwks_cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0

    def _normalize_algorithm(self, alg: str) -> str:
        """Normalize algorithm name for comparison.

        EdDSA has multiple names (EdDSA, Ed25519) that should be treated as equivalent.

        Args:
            alg: Algorithm name

        Returns:
            Normalized algorithm name
        """
        if alg in EDDSA_ALGORITHMS:
            return "Ed25519"
        return alg

    def _algorithms_match(self, alg1: str, alg2: str) -> bool:
        """Check if two algorithm names match (considering EdDSA aliases).

        Args:
            alg1: First algorithm name
            alg2: Second algorithm name

        Returns:
            True if algorithms match
        """
        return self._normalize_algorithm(alg1) == self._normalize_algorithm(alg2)

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

    def _get_unverified_header(self, token: str) -> dict[str, Any]:
        """Extract header from JWT without verification.

        Args:
            token: JWT token string

        Returns:
            Header dictionary

        Raises:
            InvalidTokenError: If token format is invalid
        """
        try:
            # Split token and decode header (first part)
            parts = token.split(".")
            if len(parts) != 3:
                raise InvalidTokenError("Invalid JWT format")

            import base64

            # Add padding if needed
            header_b64 = parts[0]
            padding = 4 - len(header_b64) % 4
            if padding != 4:
                header_b64 += "=" * padding

            import json

            header_bytes = base64.urlsafe_b64decode(header_b64)
            return cast(dict[str, Any], json.loads(header_bytes))
        except (ValueError, json.JSONDecodeError) as e:
            raise InvalidTokenError(f"Invalid JWT header: {e}") from e

    def _find_signing_key(self, jwks: dict[str, Any], token: str) -> Any:
        """Find the signing key from JWKS that matches the token's kid.

        Args:
            jwks: JSON Web Key Set
            token: JWT token

        Returns:
            Key object from joserfc KeySet

        Raises:
            InvalidTokenError: If no matching key found or algorithm mismatch
        """
        header = self._get_unverified_header(token)
        kid = header.get("kid")
        token_alg = header.get("alg")

        # Validate token algorithm matches configuration (prevent algorithm confusion)
        if token_alg and not self._algorithms_match(token_alg, self.algorithm):
            raise InvalidTokenError(
                f"Token algorithm '{token_alg}' doesn't match "
                f"configured algorithm '{self.algorithm}'"
            )

        # Import JWKS as KeySet
        try:
            key_set = KeySet.import_key_set(jwks)
        except Exception as e:
            raise InvalidTokenError(f"Failed to import JWKS: {e}") from e

        # Find key by kid
        for key in key_set.keys:
            if key.kid == kid:
                key_alg = key.alg
                if key_alg and not self._algorithms_match(key_alg, self.algorithm):
                    raise InvalidTokenError(
                        f"Key algorithm '{key_alg}' doesn't match "
                        f"configured algorithm '{self.algorithm}'"
                    )
                return key

        raise InvalidTokenError("No matching key found in JWKS")

    def _decode_token(self, token: str, signing_key: Any) -> dict[str, Any]:
        """Decode and verify the provided JWT token.

        Args:
            token: JWT token
            signing_key: Key object from joserfc

        Returns:
            Decoded token claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token validation failed
        """
        # Build the list of algorithms to accept
        # For EdDSA, we accept both "Ed25519" and "EdDSA" in case the token uses either
        if self.algorithm in EDDSA_ALGORITHMS:
            algorithms = list(EDDSA_ALGORITHMS)
        else:
            algorithms = [self.algorithm]

        try:
            result = jwt.decode(
                token, signing_key, algorithms=algorithms, registry=_ACCESS_TOKEN_REGISTRY
            )
            decoded = dict(result.claims)
        except ExpiredTokenError as e:
            raise TokenExpiredError("Token has expired") from e
        except JoseError as e:
            raise InvalidTokenError(f"Token validation failed: {e}") from e

        # Manual validation of timing claims based on options
        current_time = int(time.time())
        leeway = self.validation_options.leeway

        if self.validation_options.verify_exp:
            exp = decoded.get("exp")
            if exp is not None and exp + leeway < current_time:
                raise TokenExpiredError("Token has expired")

        if self.validation_options.verify_iat:
            iat = decoded.get("iat")
            if iat is not None and iat - leeway > current_time:
                raise InvalidTokenError("Token issued in the future")

        if self.validation_options.verify_nbf:
            nbf = decoded.get("nbf")
            if nbf is not None and nbf - leeway > current_time:
                raise InvalidTokenError("Token not yet valid")

        # Manually validate issuer (if flag is enabled)
        if self.validation_options.verify_iss:
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

        # Always validate audience
        token_aud = decoded.get("aud")
        token_audiences = [token_aud] if isinstance(token_aud, str) else (token_aud or [])
        expected_audiences = [self.audience] if isinstance(self.audience, str) else self.audience

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
        client_id = decoded.get("client_id") or decoded.get("azp") or "unknown"

        return client_id

    async def validate_token(self, token: str) -> ResourceOwner:
        """Validate JWT and return authenticated resource owner.

        Always validates (cannot be disabled):
        - Token signature using JWKS public key
        - Subject (sub claim) exists
        - Audience (aud claim) matches configured audience(s)

        Optionally validates (controlled by validation_options, all default to True):
        - Expiration (exp claim) - verify_exp
        - Issued-at time (iat claim) - verify_iat
        - Not-before time (nbf claim) - verify_nbf
        - Issuer (iss claim) matches configured issuer(s) - verify_iss

        Clock skew tolerance can be configured via validation_options.leeway (in seconds).

        Args:
            token: JWT Bearer token

        Returns:
            ResourceOwner with user_id, client_id, and claims

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

            return ResourceOwner(
                user_id=user_id,
                client_id=client_id,
                email=email,
                claims=decoded,
            )

        except (InvalidTokenError, TokenExpiredError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
