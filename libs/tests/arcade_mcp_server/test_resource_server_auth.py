import base64
import time
from unittest.mock import Mock, patch

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server.resource_server import (
    AccessTokenValidationOptions,
    AuthorizationServerEntry,
    InsufficientScopeError,
    JWKSTokenValidator,
    ResourceServerAuth,
)
from arcade_mcp_server.resource_server.base import (
    InvalidTokenError,
    ResourceOwner,
    TokenExpiredError,
)
from arcade_mcp_server.resource_server.middleware import ResourceServerMiddleware
from arcade_mcp_server.worker import create_arcade_mcp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from joserfc import jwt
from joserfc.jwk import OKPKey, RSAKey


# Test fixtures
@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    """Clean server auth environment variables before each test."""
    env_vars = [
        "MCP_RESOURCE_SERVER_CANONICAL_URL",
        "MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS",
        "MCP_RESOURCE_SERVER_SCOPES_SUPPORTED",
        "MCP_RESOURCE_SERVER_DEFAULT_CHALLENGE_SCOPES",
        # Defense-in-depth: scrub the legacy name even though it no
        # longer matches a setting field, so any stray copies in CI
        # shells cannot pollute the test process.
        "MCP_RESOURCE_SERVER_DEFAULT_ADVERTISED_SCOPES",
    ]

    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    yield


@pytest.fixture
def rsa_keypair():
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    return private_key, public_key


@pytest.fixture
def rsa_joserfc_key(rsa_keypair):
    """Generate joserfc RSAKey from keypair."""
    private_key, _ = rsa_keypair
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return RSAKey.import_key(pem)


@pytest.fixture
def serialized_private_key(rsa_keypair):
    """Generate private key as PEM format for testing."""
    private_key, _ = rsa_keypair
    # Serialize private key to PEM format
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return pem


@pytest.fixture
def jwks_data(rsa_keypair):
    """Generate JWKS data for testing."""
    _, public_key = rsa_keypair

    # Export public key in JWK format
    public_numbers = public_key.public_numbers()
    n = public_numbers.n
    e = public_numbers.e

    # Convert to base64url
    n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
    e_bytes = e.to_bytes((e.bit_length() + 7) // 8, byteorder="big")
    n_b64 = base64.urlsafe_b64encode(n_bytes).decode("utf-8").rstrip("=")
    e_b64 = base64.urlsafe_b64encode(e_bytes).decode("utf-8").rstrip("=")

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": n_b64,
                "e": e_b64,
            }
        ]
    }


@pytest.fixture
def valid_jwt_token(rsa_joserfc_key):
    """Generate valid JWT token for testing."""
    claims = {
        "sub": "user123",
        "email": "user@example.com",
        "iss": "https://auth.example.com",
        "aud": "https://mcp.example.com/mcp",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }

    header = {"alg": "RS256", "kid": "test-key-1"}
    token = jwt.encode(header, claims, rsa_joserfc_key)

    return token


@pytest.fixture
def expired_jwt_token(rsa_joserfc_key):
    """Generate expired JWT token for testing."""
    claims = {
        "sub": "user123",
        "email": "user@example.com",
        "iss": "https://auth.example.com",
        "aud": "https://mcp.example.com/mcp",
        "exp": int(time.time()) - 3600,
        "iat": int(time.time()) - 7200,
    }

    header = {"alg": "RS256", "kid": "test-key-1"}
    token = jwt.encode(header, claims, rsa_joserfc_key)

    return token


# Ed25519 fixtures
@pytest.fixture
def ed25519_keypair():
    """Generate Ed25519 key pair for testing."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def ed25519_joserfc_key(ed25519_keypair):
    """Generate joserfc OKPKey from Ed25519 keypair."""
    private_key, _ = ed25519_keypair
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return OKPKey.import_key(pem)


@pytest.fixture
def ed25519_jwks_data(ed25519_keypair):
    """Generate Ed25519 JWKS data for testing."""
    _, public_key = ed25519_keypair

    # Get the raw public key bytes
    public_bytes = public_key.public_bytes_raw()

    # Base64url encode the public key
    x_b64 = base64.urlsafe_b64encode(public_bytes).decode("utf-8").rstrip("=")

    return {
        "keys": [
            {
                "kty": "OKP",
                "kid": "ed25519-key-1",
                "use": "sig",
                "alg": "Ed25519",
                "crv": "Ed25519",
                "x": x_b64,
            }
        ]
    }


@pytest.fixture
def valid_ed25519_token(ed25519_joserfc_key):
    """Generate valid Ed25519 JWT token for testing."""
    claims = {
        "sub": "user456",
        "email": "ed25519user@example.com",
        "iss": "https://cloud.arcade.dev/oauth2",
        "aud": "urn:arcade:mcp",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }

    header = {"alg": "Ed25519", "kid": "ed25519-key-1"}
    # Ed25519 is not in joserfc's recommended algorithms, so we must explicitly allow it
    token = jwt.encode(header, claims, ed25519_joserfc_key, algorithms=["Ed25519"])

    return token


@pytest.fixture
def expired_ed25519_token(ed25519_joserfc_key):
    """Generate expired Ed25519 JWT token for testing."""
    claims = {
        "sub": "user456",
        "email": "ed25519user@example.com",
        "iss": "https://cloud.arcade.dev/oauth2",
        "aud": "urn:arcade:mcp",
        "exp": int(time.time()) - 3600,
        "iat": int(time.time()) - 7200,
    }

    header = {"alg": "Ed25519", "kid": "ed25519-key-1"}
    # Ed25519 is not in joserfc's recommended algorithms, so we must explicitly allow it
    token = jwt.encode(header, claims, ed25519_joserfc_key, algorithms=["Ed25519"])

    return token


class TestJWKSTokenValidator:
    """Tests for JWKSTokenValidator class."""

    @pytest.mark.asyncio
    async def test_validate_valid_token(self, valid_jwt_token, jwks_data):
        """Test validating a valid JWT token."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            user = await validator.validate_token(valid_jwt_token)

            assert isinstance(user, ResourceOwner)
            assert user.user_id == "user123"
            assert user.email == "user@example.com"
            assert user.claims["iss"] == "https://auth.example.com"

    @pytest.mark.asyncio
    async def test_validate_expired_token(self, expired_jwt_token, jwks_data):
        """Test validating an expired JWT token."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            with pytest.raises(TokenExpiredError):
                await validator.validate_token(expired_jwt_token)

    @pytest.mark.asyncio
    async def test_validate_wrong_audience(self, rsa_joserfc_key, jwks_data):
        """Test validating token with wrong audience."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://wrong-server.com",  # Wrong audience
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            with pytest.raises(InvalidTokenError, match="audience"):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_wrong_issuer(self, rsa_joserfc_key, jwks_data):
        """Test validating token with wrong issuer."""
        claims = {
            "sub": "user123",
            "iss": "https://wrong-issuer.com",  # Wrong issuer
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            with pytest.raises(InvalidTokenError, match="issuer"):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_missing_sub_claim(self, rsa_joserfc_key, jwks_data):
        """Test validating token without sub claim."""
        claims = {
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            with pytest.raises(InvalidTokenError, match="sub"):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_jwks_caching(self, valid_jwt_token, jwks_data):
        """Test that JWKS is cached to avoid repeated fetches."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                cache_ttl=3600,
            )

            # First validation should fetch JWKS
            await validator.validate_token(valid_jwt_token)
            assert mock_get.call_count == 1

            # Second validation should use cached JWKS
            await validator.validate_token(valid_jwt_token)
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_single_token_aud(self, rsa_joserfc_key, jwks_data):
        """Test validator with multiple audiences accepts token with matching single aud."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://old-mcp.example.com",  # Matches first audience
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            user = await validator.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_list_token_aud(self, rsa_joserfc_key, jwks_data):
        """Test validator with multiple audiences accepts token with list aud."""
        # Token with list of audiences where one matches the validator's accepted audiences
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": ["https://api1.com", "https://new-mcp.example.com"],  # Second matches
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            user = await validator.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_no_match(self, rsa_joserfc_key, jwks_data):
        """Test validator with multiple audiences rejects token with non-matching aud."""
        # Token with audience that doesn't match any of validator's accepted audiences
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://different-server.com",  # Doesn't match
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            with pytest.raises(InvalidTokenError, match="audience"):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_single_audience_with_list_token_aud(self, rsa_joserfc_key, jwks_data):
        """Test validator with single audience accepts token with list aud containing match."""
        # Token with list of audiences where one matches validator's single audience
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": ["https://api1.com", "https://mcp.example.com/mcp", "https://api2.com"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",  # Single audience
            )

            user = await validator.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_issuers_efficient(self, rsa_joserfc_key, jwks_data):
        """Test that multi-issuer validation is efficient (single decode)."""
        # Token from second issuer in list
        claims = {
            "sub": "user123",
            "iss": "https://auth2.example.com",  # Second in list
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with patch(
                "arcade_mcp_server.resource_server.validators.jwks.jwt.decode",
                wraps=jwt.decode,
            ) as mock_decode:
                validator = JWKSTokenValidator(
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    issuer=[
                        "https://auth1.example.com",
                        "https://auth2.example.com",
                        "https://auth3.example.com",
                    ],
                    audience="https://mcp.example.com/mcp",
                )

                user = await validator.validate_token(token)
                assert user.user_id == "user123"

                # Should only need to decode once, not 3 times
                assert mock_decode.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_nbf_claim_before_time(self, rsa_joserfc_key, jwks_data):
        """Test that token with nbf claim in the future is rejected."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 7200,  # expires in 2 hours
            "iat": int(time.time()),
            "nbf": int(time.time()) + 3600,  # Not valid for 1 hour
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                validation_options=AccessTokenValidationOptions(verify_nbf=True),
            )

            with pytest.raises(InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_nbf_claim_disabled(self, rsa_joserfc_key, jwks_data):
        """Test that token with nbf in future is accepted when verify_nbf=False."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 7200,  # expires in 2 hours
            "iat": int(time.time()),
            "nbf": int(time.time()) + 3600,  # Not valid for 1 hour
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                validation_options=AccessTokenValidationOptions(verify_nbf=False),
            )

            # Should accept the token when nbf verification is disabled
            user = await validator.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_with_leeway(self, rsa_joserfc_key, jwks_data):
        """Test that leeway allows slightly expired tokens."""
        # Token expired 30 seconds ago
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) - 30,
            "iat": int(time.time()) - 3600,
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Validator with 60 second leeway should accept this token
            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                validation_options=AccessTokenValidationOptions(leeway=60),
            )

            user = await validator.validate_token(token)
            assert user.user_id == "user123"


class TestJWKSTokenValidatorEd25519:
    """Tests for JWKSTokenValidator with Ed25519 algorithm."""

    @pytest.mark.asyncio
    async def test_validate_valid_ed25519_token(self, valid_ed25519_token, ed25519_jwks_data):
        """Test validating a valid Ed25519 JWT token."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://cloud.arcade.dev/oauth2",
                audience="urn:arcade:mcp",
                algorithm="Ed25519",
            )

            user = await validator.validate_token(valid_ed25519_token)

            assert isinstance(user, ResourceOwner)
            assert user.user_id == "user456"
            assert user.email == "ed25519user@example.com"
            assert user.claims["iss"] == "https://cloud.arcade.dev/oauth2"

    @pytest.mark.asyncio
    async def test_validate_expired_ed25519_token(self, expired_ed25519_token, ed25519_jwks_data):
        """Test validating an expired Ed25519 JWT token."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://cloud.arcade.dev/oauth2",
                audience="urn:arcade:mcp",
                algorithm="Ed25519",
            )

            with pytest.raises(TokenExpiredError):
                await validator.validate_token(expired_ed25519_token)

    @pytest.mark.asyncio
    async def test_ed25519_algorithm_mismatch(self, valid_jwt_token, ed25519_jwks_data):
        """Test that RS256 token is rejected when validator expects Ed25519."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
                algorithm="Ed25519",
            )

            # RS256 token should be rejected when Ed25519 is expected
            with pytest.raises(InvalidTokenError, match="algorithm"):
                await validator.validate_token(valid_jwt_token)

    @pytest.mark.asyncio
    async def test_ed25519_wrong_audience(self, ed25519_joserfc_key, ed25519_jwks_data):
        """Test Ed25519 token with wrong audience is rejected."""
        claims = {
            "sub": "user456",
            "iss": "https://cloud.arcade.dev/oauth2",
            "aud": "wrong:audience",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "Ed25519", "kid": "ed25519-key-1"}
        token = jwt.encode(header, claims, ed25519_joserfc_key, algorithms=["Ed25519"])

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://cloud.arcade.dev/oauth2",
                audience="urn:arcade:mcp",
                algorithm="Ed25519",
            )

            with pytest.raises(InvalidTokenError, match="audience"):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_eddsa_algorithm_alias(self, ed25519_joserfc_key, ed25519_jwks_data):
        """Test that EdDSA algorithm alias works for Ed25519."""
        claims = {
            "sub": "user456",
            "email": "ed25519user@example.com",
            "iss": "https://cloud.arcade.dev/oauth2",
            "aud": "urn:arcade:mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "Ed25519", "kid": "ed25519-key-1"}
        token = jwt.encode(header, claims, ed25519_joserfc_key, algorithms=["Ed25519"])

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Use EdDSA alias
            validator = JWKSTokenValidator(
                jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                issuer="https://cloud.arcade.dev/oauth2",
                audience="urn:arcade:mcp",
                algorithm="EdDSA",  # Using EdDSA alias
            )

            user = await validator.validate_token(token)
            assert user.user_id == "user456"

    def test_ed25519_supported_algorithm(self):
        """Test that Ed25519 is in supported algorithms."""
        # Should not raise
        validator = JWKSTokenValidator(
            jwks_uri="https://example.com/jwks",
            issuer="https://example.com",
            audience="https://example.com",
            algorithm="Ed25519",
        )
        assert validator.algorithm == "Ed25519"

    def test_eddsa_supported_algorithm(self):
        """Test that EdDSA is in supported algorithms."""
        # Should not raise
        validator = JWKSTokenValidator(
            jwks_uri="https://example.com/jwks",
            issuer="https://example.com",
            audience="https://example.com",
            algorithm="EdDSA",
        )
        assert validator.algorithm == "EdDSA"


class TestArcadeASConfiguration:
    """Tests for Arcade AS configuration."""

    @pytest.mark.asyncio
    async def test_arcade_as_config(self, valid_ed25519_token, ed25519_jwks_data):
        """Test configuration matching Arcade AS."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = ed25519_jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Configuration matching Arcade AS
            resource_server_auth = ResourceServerAuth(
                canonical_url="https://gateway-manager.arcade.dev/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://cloud.arcade.dev/oauth2",
                        issuer="https://cloud.arcade.dev/oauth2",
                        jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                        algorithm="Ed25519",
                        expected_audiences=[
                            "urn:arcade:mcp",
                            "https://gateway-manager.arcade.dev/mcp",
                        ],
                    )
                ],
            )

            user = await resource_server_auth.validate_token(valid_ed25519_token)
            assert user.user_id == "user456"
            assert user.email == "ed25519user@example.com"

    def test_arcade_as_metadata(self):
        """Test OAuth metadata for Arcade AS configuration."""
        resource_server_auth = ResourceServerAuth(
            canonical_url="https://gateway-manager.arcade.dev/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://cloud.arcade.dev/oauth2",
                    issuer="https://cloud.arcade.dev/oauth2",
                    jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
                    algorithm="Ed25519",
                    expected_audiences=["urn:arcade:mcp"],
                )
            ],
        )

        metadata = resource_server_auth.get_resource_metadata()
        assert metadata["resource"] == "https://gateway-manager.arcade.dev/mcp"
        assert metadata["authorization_servers"] == ["https://cloud.arcade.dev/oauth2"]


# ResourceServerAuth Tests
class TestResourceServerAuth:
    """Tests for ResourceServerAuth class."""

    def test_supports_oauth_discovery(self):
        """Test that ResourceServerAuth supports OAuth discovery."""
        resource_server_auth = ResourceServerAuth(
            canonical_url="https://mcp.example.com/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        )

        assert resource_server_auth.supports_oauth_discovery() is True

    def test_get_resource_metadata(self):
        """Test getting OAuth Protected Resource Metadata."""
        resource_server_auth = ResourceServerAuth(
            canonical_url="https://mcp.example.com/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        )

        metadata = resource_server_auth.get_resource_metadata()

        assert metadata["resource"] == "https://mcp.example.com/mcp"
        assert metadata["authorization_servers"] == ["https://auth.example.com"]
        assert metadata["bearer_methods_supported"] == ["header"]

    @pytest.mark.asyncio
    async def test_expected_audiences_override(self, rsa_keypair, jwks_data, rsa_joserfc_key):
        """Test that expected_audiences overrides canonical_url for audience validation."""
        # Token with custom audience
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "my-authkit-client-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                        expected_audiences=["my-authkit-client-id"],
                    )
                ],
            )

            user = await resource_server_auth.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_expected_audiences_multiple_values(
        self, rsa_keypair, jwks_data, rsa_joserfc_key
    ):
        """Test that multiple expected_audiences work correctly."""
        # Token with one of the expected audiences
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "secondary-client-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                        expected_audiences=[
                            "primary-client-id",
                            "secondary-client-id",
                            "tertiary-client-id",
                        ],
                    )
                ],
            )

            user = await resource_server_auth.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_expected_audiences_defaults_to_canonical_url(
        self, rsa_keypair, jwks_data, rsa_joserfc_key
    ):
        """Test that without expected_audiences, canonical_url is used for audience validation."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    )
                ],
            )

            user = await resource_server_auth.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_expected_audiences_wrong_audience_rejected(
        self, rsa_keypair, jwks_data, rsa_joserfc_key
    ):
        """Test that tokens with wrong audience are rejected even with expected_audiences."""
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "wrong-client-id",  # Not in expected_audiences list
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                        expected_audiences=["correct-client-id"],
                    )
                ],
            )

            with pytest.raises(InvalidTokenError):
                await resource_server_auth.validate_token(token)


# ResourceServerMiddleware Tests
class TestResourceServerMiddleware:
    """Tests for ResourceServerMiddleware class."""

    @pytest.mark.asyncio
    async def test_authenticated_request(self, valid_jwt_token, jwks_data):
        """Test authenticated request passes through."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            # Mock app
            app_called = False

            async def mock_app(scope, receive, send):
                nonlocal app_called
                app_called = True
                assert "resource_owner" in scope
                assert scope["resource_owner"].user_id == "user123"

            middleware = ResourceServerMiddleware(
                mock_app,
                validator,
                "https://mcp.example.com/mcp",
            )

            # Create mock request
            scope = {
                "type": "http",
                "method": "POST",
                "headers": [(b"authorization", f"Bearer {valid_jwt_token}".encode())],
            }

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                pass

            await middleware(scope, receive, send)
            assert app_called is True

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, jwks_data):
        """Test request without Authorization header returns 401."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            validator = JWKSTokenValidator(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com/mcp",
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = ResourceServerMiddleware(
                mock_app,
                validator,
                "https://mcp.example.com/mcp",
            )

            # mock request w/o auth header
            scope = {
                "type": "http",
                "method": "POST",
                "headers": [],
            }

            async def receive():
                return {"type": "http.request", "body": b""}

            response_sent = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_sent["status"] = message["status"]
                    response_sent["headers"] = dict(message.get("headers", []))

            await middleware(scope, receive, send)

            assert response_sent["status"] == 401
            assert any(k.lower() == b"www-authenticate" for k in response_sent["headers"])

    @pytest.mark.asyncio
    async def test_www_authenticate_header_format(self, jwks_data):
        """Test WWW-Authenticate header format compliance."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    )
                ],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = ResourceServerMiddleware(
                mock_app,
                resource_server,
                "https://mcp.example.com/mcp",
            )

            scope = {
                "type": "http",
                "method": "POST",
                "headers": [],
            }

            async def receive():
                return {"type": "http.request", "body": b""}

            response_headers = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))

            await middleware(scope, receive, send)

            www_auth = response_headers.get(b"www-authenticate", b"").decode()

            assert "Bearer" in www_auth
            assert "resource_metadata=" in www_auth
            assert "/.well-known/oauth-protected-resource" in www_auth
            # No default_challenge_scopes configured -> no `scope=` advertised.
            # Spec lets the absence trigger the client's fallback selection
            # strategy; emitting ``scope=""`` would be wrong (zero-scope token).
            assert "scope=" not in www_auth

    @pytest.mark.asyncio
    async def test_www_authenticate_advertises_default_scopes(self, jwks_data):
        """When ``default_challenge_scopes`` is configured, the entry-401
        WWW-Authenticate header MUST include a space-separated ``scope=...``
        parameter per the MCP spec (SHOULD-rule).
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    )
                ],
                default_challenge_scopes=["read", "write"],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            # Middleware reads default_challenge_scopes from the validator,
            # no separate kwarg needed.
            middleware = ResourceServerMiddleware(
                mock_app,
                resource_server,
                "https://mcp.example.com/mcp",
            )

            scope = {"type": "http", "method": "POST", "headers": []}

            async def receive():
                return {"type": "http.request", "body": b""}

            response_headers: dict[bytes, bytes] = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))

            await middleware(scope, receive, send)

            www_auth = response_headers.get(b"www-authenticate", b"").decode()
            assert 'scope="read write"' in www_auth, www_auth

    def test_resource_metadata_includes_scopes_supported(self):
        """When ``scopes_supported`` is configured, the RFC 9728
        Protected Resource Metadata document MUST include the field
        so clients without a WWW-Authenticate ``scope`` parameter can fall
        back per the MCP spec scope-selection strategy.
        """
        resource_server = ResourceServerAuth(
            canonical_url="https://mcp.example.com/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
            scopes_supported=["read", "write"],
        )

        metadata = resource_server.get_resource_metadata()
        assert metadata["scopes_supported"] == ["read", "write"]

    def test_resource_metadata_omits_scopes_supported_when_unset(self):
        """When ``scopes_supported`` is not configured, the RFC 9728
        metadata document MUST NOT include ``scopes_supported`` (the field is
        OPTIONAL per RFC 9728 and an empty array would be misleading).
        """
        resource_server = ResourceServerAuth(
            canonical_url="https://mcp.example.com/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        )

        metadata = resource_server.get_resource_metadata()
        assert "scopes_supported" not in metadata

    @pytest.mark.asyncio
    async def test_middleware_reads_scopes_from_validator(self, jwks_data):
        """Middleware reads ``default_challenge_scopes`` directly from the
        validator instance, not from a duplicate constructor parameter.

        One source of truth (the validator) keeps the contract typed and
        avoids the ``getattr`` plumbing that previously lived in
        ``worker.create_arcade_mcp``.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    )
                ],
                default_challenge_scopes=["read", "write"],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            # NO ``default_challenge_scopes=`` kwarg on the middleware,
            # which reads from ``resource_server.default_challenge_scopes``.
            middleware = ResourceServerMiddleware(
                mock_app,
                resource_server,
                "https://mcp.example.com/mcp",
            )

            scope = {"type": "http", "method": "POST", "headers": []}

            async def receive():
                return {"type": "http.request", "body": b""}

            response_headers: dict[bytes, bytes] = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))

            await middleware(scope, receive, send)

            www_auth = response_headers.get(b"www-authenticate", b"").decode()
            assert 'scope="read write"' in www_auth, www_auth

    def test_middleware_construction_rejects_default_scopes_param(self):
        """``default_challenge_scopes`` is not a constructor parameter
        on ``ResourceServerMiddleware``. Source of truth is the validator.

        Passing it as a kwarg raises ``TypeError`` (unexpected keyword
        argument). This pins the API simplification: having two ways to set
        the same value is a documented anti-pattern (DRY) and makes the
        relationship between validator and middleware ambiguous.
        """
        validator = JWKSTokenValidator(
            jwks_uri="https://auth.example.com/jwks",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com/mcp",
        )

        async def app(scope, receive, send):
            pass

        with pytest.raises(TypeError, match="default_challenge_scopes"):
            ResourceServerMiddleware(
                app,
                validator,
                "https://mcp.example.com/mcp",
                default_challenge_scopes=["x"],  # type: ignore[call-arg]
            )


class TestResourceServerValidatorContract:
    """Tests for the ``ResourceServerValidator`` ABC public contract.

    These tests pin the contract that any custom validator (third-party
    subclass) can rely on. The MCP 2025-11-25 spec (driven by SEP-835)
    treats two scope surfaces as independent: ``scopes_supported`` (RFC
    9728 PRM) and ``default_challenge_scopes`` (RFC 6750 entry-401).
    Both attributes are part of the ABC contract so middleware reads
    them directly with no defensive ``getattr``.
    """

    def test_validator_abc_exposes_scopes_supported_class_attribute(self):
        """The ABC declares ``scopes_supported`` as a class-level
        attribute defaulting to ``None``.

        Concrete validators inherit this default and can override via instance
        assignment in ``__init__``. The class-level default of ``None`` (not
        ``[]``) avoids the mutable-default footgun.
        """
        from arcade_mcp_server.resource_server.base import ResourceServerValidator

        assert ResourceServerValidator.scopes_supported is None
        annotations = ResourceServerValidator.__annotations__
        assert "scopes_supported" in annotations

    def test_validator_abc_exposes_default_challenge_scopes_class_attribute(self):
        """The ABC declares ``default_challenge_scopes`` as a class-level
        attribute defaulting to ``None``. Independent of ``scopes_supported``
        per the SEP-835 surface split.
        """
        from arcade_mcp_server.resource_server.base import ResourceServerValidator

        assert ResourceServerValidator.default_challenge_scopes is None
        annotations = ResourceServerValidator.__annotations__
        assert "default_challenge_scopes" in annotations

    def test_jwks_validator_inherits_both_scope_attributes_default_none(self):
        """``JWKSTokenValidator`` (no scope-advertisement support) inherits
        ``scopes_supported = None`` and ``default_challenge_scopes = None``
        from the ABC. Middleware reading either attribute therefore always
        finds it (no AttributeError), which is why we can drop the
        ``getattr``.
        """
        validator = JWKSTokenValidator(
            jwks_uri="https://auth.example.com/jwks",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com/mcp",
        )
        assert validator.scopes_supported is None
        assert validator.default_challenge_scopes is None


class TestAdvertisedScopesValidation:
    """Tests for RFC 6750 scope-token validation across both scope surfaces.

    RFC 6750 ABNF: ``scope-token = 1*( %x21 / %x23-5B / %x5D-7E )``,
    at least one printable ASCII character, excluding ``"`` (0x22),
    ``\\`` (0x5C), space, control characters, and non-ASCII.

    Validating at construction time surfaces malformed scope tokens with a
    clear error rather than emitting a malformed ``WWW-Authenticate`` header
    or PRM document at runtime (where the bug would be much harder to
    diagnose).

    Parametrized over both ``scopes_supported`` and
    ``default_challenge_scopes``: validation discipline is identical
    on both surfaces.
    """

    def _minimal_kwargs(self):
        """Helper: minimal valid ``ResourceServerAuth`` kwargs."""
        return {
            "canonical_url": "https://mcp.example.com/mcp",
            "authorization_servers": [
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        }

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    @pytest.mark.parametrize(
        "bad_input,expected_error",
        [
            # Empty / whitespace-only
            ([""], "empty"),
            (["   "], "empty"),
            # Whitespace inside the token
            (["scope with space"], "whitespace"),
            (["tab\there"], "whitespace"),
            (["newline\nhere"], "whitespace"),
            # Non-ASCII
            (["unicode-é"], "non-ASCII|ASCII"),
            (["日本語"], "non-ASCII|ASCII"),
            # Specifically excluded by RFC 6750 grammar
            (['quote"here'], "RFC 6750"),
            (["back\\slash"], "RFC 6750"),
            # Control characters (< 0x20)
            (["bell\x07char"], "RFC 6750|whitespace"),
            (["null\x00byte"], "RFC 6750|whitespace"),
        ],
    )
    def test_invalid_scope_token_rejected(self, field_name, bad_input, expected_error):
        """Each invalid token shape raises ValueError at construction."""
        with pytest.raises(ValueError, match=expected_error):
            ResourceServerAuth(
                **self._minimal_kwargs(),
                **{field_name: bad_input},
            )

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    @pytest.mark.parametrize(
        "valid_input",
        [
            # Common OAuth scope shapes
            ["mcp"],
            ["mcp", "offline_access"],
            ["files:read", "files:write"],
            ["user.profile", "user.email"],
            # Provider-style URI scopes (Google convention)
            ["https://www.googleapis.com/auth/gmail.readonly"],
            # Edge of the allowed grammar
            ["!"],  # 0x21, minimum legal scope
            ["~"],  # 0x7E, maximum legal scope
            ["a!b#c$d%e&f'g(h)i*j+k,l-m.n/o:p;q<r=s>t?u@v[w]x^y_z`{|}"],  # all allowed punctuation
        ],
    )
    def test_valid_scope_tokens_accepted(self, field_name, valid_input):
        """Tokens conforming to RFC 6750 grammar are accepted unchanged."""
        rs = ResourceServerAuth(
            **self._minimal_kwargs(),
            **{field_name: valid_input},
        )
        assert getattr(rs, field_name) == valid_input

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_invalid_token_error_names_offending_token(self, field_name):
        """Error message includes the offending token for fast debugging."""
        with pytest.raises(ValueError, match="bad token"):
            ResourceServerAuth(
                **self._minimal_kwargs(),
                **{field_name: ["good_token", "bad token"]},
            )

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_duplicate_scopes_are_deduplicated_first_seen_order(self, field_name):
        """Operators may pass duplicates (e.g., from concatenated lists);
        the validator dedupes with first-seen ordering preserved.

        First-seen ordering is important: it matches what operators
        intuitively expect when they declare ``["mcp", "offline_access"]``,
        the order in PRM and the wire is THEIR order, not lexical.
        """
        rs = ResourceServerAuth(
            **self._minimal_kwargs(),
            **{field_name: ["c", "a", "b", "a", "c", "d"]},
        )
        assert getattr(rs, field_name) == ["c", "a", "b", "d"]

    @pytest.mark.asyncio
    async def test_challenge_scopes_order_preserved_in_401(self, jwks_data):
        """The 401 ``WWW-Authenticate`` ``scope=...`` value MUST echo the
        operator's declared order. No alphabetical sort, no rearrangement.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server = ResourceServerAuth(
                **self._minimal_kwargs(),
                default_challenge_scopes=["c", "a", "b"],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = ResourceServerMiddleware(
                mock_app,
                resource_server,
                "https://mcp.example.com/mcp",
            )

            scope = {"type": "http", "method": "POST", "headers": []}

            async def receive():
                return {"type": "http.request", "body": b""}

            response_headers: dict[bytes, bytes] = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))

            await middleware(scope, receive, send)

            www_auth = response_headers.get(b"www-authenticate", b"").decode()
            assert 'scope="c a b"' in www_auth, www_auth

    def test_scopes_supported_order_preserved_in_prm(self):
        """RFC 9728 ``scopes_supported`` MUST echo the operator's declared
        order.
        """
        rs = ResourceServerAuth(
            **self._minimal_kwargs(),
            scopes_supported=["zebra", "alpha", "mike"],
        )
        metadata = rs.get_resource_metadata()
        assert metadata["scopes_supported"] == ["zebra", "alpha", "mike"]


_SCOPE_FIELD_TO_ENV_VAR = {
    "scopes_supported": "MCP_RESOURCE_SERVER_SCOPES_SUPPORTED",
    "default_challenge_scopes": "MCP_RESOURCE_SERVER_DEFAULT_CHALLENGE_SCOPES",
}


class TestAdvertisedScopesEnvVar:
    """Tests for the env var entry point for both scope surfaces.

    Both ``MCP_RESOURCE_SERVER_SCOPES_SUPPORTED`` and
    ``MCP_RESOURCE_SERVER_DEFAULT_CHALLENGE_SCOPES`` use **space-separated**
    format (``"mcp offline_access"``) matching OAuth wire convention (RFC
    6749 ``scope`` parameter is space-separated).

    Empty / whitespace-only values are treated as "unset" (None): they
    must never produce an empty list (an empty advertisement is
    semantically wrong; see middleware's empty-scope-loop comment).

    Parametrized over both env vars: parsing discipline is identical.
    """

    def _minimal_kwargs(self):
        """Minimal valid ``ResourceServerAuth`` kwargs (no scope arg)."""
        return {
            "canonical_url": "https://mcp.example.com/mcp",
            "authorization_servers": [
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        }

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_scopes_from_env(self, monkeypatch, field_name):
        """Setting the env var (no constructor kwarg) configures the field."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "mcp offline_access")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        assert getattr(rs, field_name) == ["mcp", "offline_access"]

    def test_scopes_supported_env_surfaces_in_prm(self, monkeypatch):
        """``MCP_RESOURCE_SERVER_SCOPES_SUPPORTED`` populates PRM
        ``scopes_supported`` (RFC 9728).
        """
        monkeypatch.setenv("MCP_RESOURCE_SERVER_SCOPES_SUPPORTED", "mcp offline_access")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        metadata = rs.get_resource_metadata()
        assert metadata["scopes_supported"] == ["mcp", "offline_access"]

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_explicit_param_overrides_env(self, monkeypatch, field_name):
        """Explicit constructor kwarg takes precedence over env var."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "from-env")
        rs = ResourceServerAuth(
            **self._minimal_kwargs(),
            **{field_name: ["from-param"]},
        )
        assert getattr(rs, field_name) == ["from-param"]

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_empty_env_var_treated_as_none(self, monkeypatch, field_name):
        """Empty env var means "no advertisement" (None), NOT empty list."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        assert getattr(rs, field_name) is None

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_whitespace_only_env_var_treated_as_none(self, monkeypatch, field_name):
        """Whitespace-only env var is treated identically to empty: None."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "   \t  \n")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        assert getattr(rs, field_name) is None

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_env_var_collapses_whitespace_runs(self, monkeypatch, field_name):
        """``str.split()`` (no args) collapses whitespace runs."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "  mcp   offline_access\t\n")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        assert getattr(rs, field_name) == ["mcp", "offline_access"]

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_invalid_scope_in_env_raises(self, monkeypatch, field_name):
        """RFC 6750 grammar applies to env-var-sourced values too."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "valid badéscope")
        with pytest.raises(ValueError, match="non-ASCII|ASCII"):
            ResourceServerAuth(**self._minimal_kwargs())

    @pytest.mark.parametrize(
        "field_name", ["scopes_supported", "default_challenge_scopes"]
    )
    def test_env_var_dedupes_with_first_seen_order(self, monkeypatch, field_name):
        """Dedup + ordering applies to env-var-sourced values too."""
        env_var = _SCOPE_FIELD_TO_ENV_VAR[field_name]
        monkeypatch.setenv(env_var, "c a b a c d")
        rs = ResourceServerAuth(**self._minimal_kwargs())
        assert getattr(rs, field_name) == ["c", "a", "b", "d"]


class TestWWWAuthenticateRFC6750Format:
    """Tests for RFC 6750 ``WWW-Authenticate`` header conformance.

    RFC 6750 specifies the header format as
    ``WWW-Authenticate: Bearer realm="...", scope="..."`` — auth-scheme
    ``Bearer``, then comma-separated ``key="value"`` parameters with
    quoted-string values.

    Behavioral tests already cover scope content (Rounds 1-5). These tests
    pin the *format* invariants — the kind of thing a regex-based MCP
    compliance tool would check before grading.
    """

    def _minimal_kwargs(self):
        return {
            "canonical_url": "https://mcp.example.com/mcp",
            "authorization_servers": [
                AuthorizationServerEntry(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        }

    @pytest.mark.asyncio
    async def _drive_401(self, resource_server):
        """Drive a missing-Authorization 401 and return the decoded
        WWW-Authenticate header value.
        """

        async def mock_app(scope, receive, send):
            pytest.fail("App should not be called")

        middleware = ResourceServerMiddleware(
            mock_app,
            resource_server,
            "https://mcp.example.com/mcp",
        )

        scope = {"type": "http", "method": "POST", "headers": []}

        async def receive():
            return {"type": "http.request", "body": b""}

        response_headers: dict[bytes, bytes] = {}

        async def send(message):
            if message["type"] == "http.response.start":
                response_headers.update(dict(message.get("headers", [])))

        await middleware(scope, receive, send)
        return response_headers.get(b"www-authenticate", b"").decode()

    @pytest.mark.asyncio
    async def test_header_uses_bearer_auth_scheme_prefix(self, jwks_data):
        """RFC 6750: header MUST begin with the ``Bearer`` auth-scheme."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **self._minimal_kwargs(),
                default_challenge_scopes=["read", "write"],
            )

            www_auth = await self._drive_401(rs)
            assert www_auth.startswith("Bearer "), www_auth

    @pytest.mark.asyncio
    async def test_scope_param_uses_quoted_string_format(self, jwks_data):
        """RFC 6750: parameters use ``key="value"`` quoted-string form.

        Specifically the scope parameter must be ``scope="..."`` (with
        double quotes), not ``scope=...`` (bare) or ``scope='...'``
        (single quotes).
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **self._minimal_kwargs(),
                default_challenge_scopes=["read", "write"],
            )

            www_auth = await self._drive_401(rs)
            assert 'scope="read write"' in www_auth, www_auth
            assert "scope=read" not in www_auth, www_auth  # not bare
            assert "scope='read" not in www_auth, www_auth  # not single-quoted

    @pytest.mark.asyncio
    async def test_quotes_are_balanced(self, jwks_data):
        """Even number of double quotes (every parameter is paired).

        An odd count would mean a malformed quoted-string somewhere.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **self._minimal_kwargs(),
                default_challenge_scopes=["read", "write"],
            )

            www_auth = await self._drive_401(rs)
            assert www_auth.count('"') % 2 == 0, www_auth

    @pytest.mark.asyncio
    async def test_no_semicolons_in_header(self, jwks_data):
        """RFC 6750: parameters are comma-separated, NOT
        semicolon-separated. Semicolons are HTTP-cookie-style; using them
        in WWW-Authenticate is a non-conformance bug some servers ship.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **self._minimal_kwargs(),
                default_challenge_scopes=["read"],
            )

            www_auth = await self._drive_401(rs)
            assert ";" not in www_auth, www_auth

    @pytest.mark.asyncio
    async def test_no_empty_scope_when_unset(self, jwks_data):
        """When ``default_challenge_scopes`` is unset, the header MUST
        omit the ``scope`` parameter entirely, not emit ``scope=""``.

        Per spec, an empty ``scope=""`` would tell compliant OAuth clients
        to acquire a zero-scope token, which is semantically wrong and a
        known cause of empty-scope token loops.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(**self._minimal_kwargs())

            www_auth = await self._drive_401(rs)
            assert "scope=" not in www_auth, www_auth
            assert 'scope=""' not in www_auth, www_auth


class TestAdvertisedScopesMultiAS:
    """Tests for multi-AS interaction with the two scope surfaces.

    Advertised scopes are *server-wide*, not per-AS: they describe what
    THIS resource accepts at the lobby, regardless of which AS the client
    chose. They MUST surface identically whether the resource is fronted
    by one AS or many. The two surfaces (PRM ``scopes_supported`` and
    entry-401 ``scope=``) are independent per the SEP-835 split, but
    each one is still server-wide rather than per-AS.
    """

    @pytest.mark.asyncio
    async def test_scopes_supported_with_multi_as_in_prm(self, jwks_data):
        """RFC 9728 ``scopes_supported`` is a property of the resource,
        not per-AS. Multi-AS configurations advertise the same scope set.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth1.example.com",
                        issuer="https://auth1.example.com",
                        jwks_uri="https://auth1.example.com/jwks",
                    ),
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth2.example.com",
                        issuer="https://auth2.example.com",
                        jwks_uri="https://auth2.example.com/jwks",
                    ),
                ],
                scopes_supported=["mcp", "offline_access"],
            )
            metadata = rs.get_resource_metadata()
            assert metadata["scopes_supported"] == ["mcp", "offline_access"]
            # Both ASes still listed
            assert metadata["authorization_servers"] == [
                "https://auth1.example.com",
                "https://auth2.example.com",
            ]

    @pytest.mark.asyncio
    async def test_default_challenge_scopes_with_multi_as_in_401(self, jwks_data):
        """Same scope set surfaces on the 401 ``WWW-Authenticate`` for
        multi-AS configurations.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth1.example.com",
                        issuer="https://auth1.example.com",
                        jwks_uri="https://auth1.example.com/jwks",
                    ),
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth2.example.com",
                        issuer="https://auth2.example.com",
                        jwks_uri="https://auth2.example.com/jwks",
                    ),
                ],
                default_challenge_scopes=["mcp", "offline_access"],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = ResourceServerMiddleware(
                mock_app,
                rs,
                "https://mcp.example.com/mcp",
            )

            scope = {"type": "http", "method": "POST", "headers": []}

            async def receive():
                return {"type": "http.request", "body": b""}

            response_headers: dict[bytes, bytes] = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))

            await middleware(scope, receive, send)
            www_auth = response_headers.get(b"www-authenticate", b"").decode()
            assert 'scope="mcp offline_access"' in www_auth, www_auth


class TestEnvVarConfiguration:
    """Tests for front-door auth env var configuration support."""

    @pytest.mark.asyncio
    async def test_resource_server_param_precedence(self, monkeypatch):
        """Test that explicit parameters take precedence over environment variables."""
        monkeypatch.setenv("MCP_RESOURCE_SERVER_CANONICAL_URL", "https://env-mcp.example.com")
        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url":"https://env.example.com","issuer":"https://env.example.com","jwks_uri":"https://env.example.com/jwks"}]',
        )

        resource_server = ResourceServerAuth(
            canonical_url="https://param-mcp.example.com",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://param.example.com",
                    issuer="https://param.example.com",
                    jwks_uri="https://param.example.com/jwks",
                )
            ],
        )

        # Explicit parameters should take precedence over env vars
        assert resource_server.canonical_url == "https://param-mcp.example.com"
        metadata = resource_server.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://param.example.com"]

    @pytest.mark.asyncio
    async def test_resource_server_all_env_vars(self, monkeypatch):
        """Test ResourceServerAuth with all env vars, no parameters."""
        monkeypatch.setenv("MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com/mcp")
        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url":"https://auth.example.com","issuer":"https://auth.example.com","jwks_uri":"https://auth.example.com/jwks","algorithm":"RS256","expected_audiences":["custom-client-id"]}]',
        )

        resource_server_auth = ResourceServerAuth()

        assert resource_server_auth.canonical_url == "https://mcp.example.com/mcp"
        metadata = resource_server_auth.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://auth.example.com"]

    def test_resource_server_missing_required(self):
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="'canonical_url' required"):
            ResourceServerAuth(
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
                # Missing canonical_url
            )

    @pytest.mark.asyncio
    async def test_worker_no_canonical_url_for_jwks_validator(self):
        """Test that worker doesn't require canonical_url for JWKSTokenValidator."""
        jwt_validator = JWKSTokenValidator(
            jwks_uri="https://auth.example.com/jwks",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com/mcp",
        )

        catalog = ToolCatalog()
        # Shouldn't raise b/c JWKSTokenValidator doesn't support OAuth discovery
        app = create_arcade_mcp(catalog, resource_server_validator=jwt_validator)
        assert app is not None

    def test_worker_requires_canonical_url_for_resource_server(self):
        """Test that ResourceServerAuth validation happens during init."""
        with pytest.raises(ValueError, match="'canonical_url' required"):
            ResourceServerAuth(
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
                # Missing canonical_url
            )


class TestMultipleAuthorizationServers:
    """Tests for multiple authorization server support."""

    @pytest.mark.asyncio
    async def test_resource_server_multiple_as_shared_jwks(self, jwks_data, valid_jwt_token):
        """Test multiple AS URLs with same JWKS"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth-us.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    ),
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth-eu.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    ),
                ],
            )

            # Verify that metadata returns all Auth Server URLs
            metadata = resource_server_auth.get_resource_metadata()
            assert metadata["resource"] == "https://mcp.example.com/mcp"
            assert metadata["authorization_servers"] == [
                "https://auth-us.example.com",
                "https://auth-eu.example.com",
            ]

            # Verify that token validation works
            user = await resource_server_auth.validate_token(valid_jwt_token)
            assert user.user_id == "user123"
            assert user.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_resource_server_multiple_as_different_jwks(
        self, rsa_keypair, jwks_data, rsa_joserfc_key
    ):
        """Test multiple AS with different JWKS (multi-IdP)."""
        claims1 = {
            "sub": "user123",
            "email": "user@workos.com",
            "iss": "https://workos.authkit.app",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        header1 = {"alg": "RS256", "kid": "test-key-1"}
        token1 = jwt.encode(header1, claims1, rsa_joserfc_key)

        claims2 = {
            "sub": "user456",
            "email": "user@keycloak.com",
            "iss": "http://localhost:8080/realms/mcp-test",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        header2 = {"alg": "RS256", "kid": "test-key-1"}
        token2 = jwt.encode(header2, claims2, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://workos.authkit.app",
                        issuer="https://workos.authkit.app",
                        jwks_uri="https://workos.authkit.app/oauth2/jwks",
                    ),
                    AuthorizationServerEntry(
                        authorization_server_url="http://localhost:8080/realms/mcp-test",
                        issuer="http://localhost:8080/realms/mcp-test",
                        jwks_uri="http://localhost:8080/realms/mcp-test/protocol/openid-connect/certs",
                        algorithm="RS256",
                    ),
                ],
            )

            # Verify metadata returns all Auth Server URLs
            metadata = resource_server_auth.get_resource_metadata()
            assert metadata["authorization_servers"] == [
                "https://workos.authkit.app",
                "http://localhost:8080/realms/mcp-test",
            ]

            # Verify tokens from both Auth Servers work
            user1 = await resource_server_auth.validate_token(token1)
            assert user1.user_id == "user123"
            assert user1.email == "user@workos.com"

            user2 = await resource_server_auth.validate_token(token2)
            assert user2.user_id == "user456"
            assert user2.email == "user@keycloak.com"

    @pytest.mark.asyncio
    async def test_resource_server_rejects_unconfigured_as(
        self, rsa_keypair, jwks_data, rsa_joserfc_key
    ):
        """Test that tokens from unlisted AS are rejected."""
        claims = {
            "sub": "user123",
            "email": "user@evil.com",
            "iss": "https://evil.com",  # Not in configured list (unauthorized issuer)
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource_server_auth = ResourceServerAuth(
                canonical_url="https://mcp.example.com/mcp",
                authorization_servers=[
                    AuthorizationServerEntry(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
            )

            # Should reject token from unauthorized Auth Server (issuer)
            with pytest.raises(
                InvalidTokenError,
                match="Token validation failed for all configured authorization servers",
            ):
                await resource_server_auth.validate_token(token)

    def test_authorization_servers_env_var_parsing_json(self, monkeypatch):
        """Test parsing JSON array of AS configs from env var."""
        monkeypatch.setenv("MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com/mcp")
        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url": "https://auth1.com", "issuer": "https://auth1.com", "jwks_uri": "https://auth1.com/jwks"}]',
        )

        resource_server_auth = ResourceServerAuth()

        metadata = resource_server_auth.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://auth1.com"]

    def test_resource_metadata_multiple_as(self):
        """Test that resource metadata returns all AS URLs."""
        resource_server_auth = ResourceServerAuth(
            canonical_url="https://mcp.example.com/mcp",
            authorization_servers=[
                AuthorizationServerEntry(
                    authorization_server_url="https://auth1.example.com",
                    issuer="https://auth1.example.com",
                    jwks_uri="https://auth1.example.com/jwks",
                ),
                AuthorizationServerEntry(
                    authorization_server_url="https://auth2.example.com",
                    issuer="https://auth2.example.com",
                    jwks_uri="https://auth2.example.com/jwks",
                ),
                AuthorizationServerEntry(
                    authorization_server_url="https://auth3.example.com",
                    issuer="https://auth3.example.com",
                    jwks_uri="https://auth3.example.com/jwks",
                ),
            ],
        )

        metadata = resource_server_auth.get_resource_metadata()
        assert metadata["resource"] == "https://mcp.example.com/mcp"
        assert len(metadata["authorization_servers"]) == 3
        assert "https://auth1.example.com" in metadata["authorization_servers"]
        assert "https://auth2.example.com" in metadata["authorization_servers"]
        assert "https://auth3.example.com" in metadata["authorization_servers"]


# ---------------------------------------------------------------------------
# Round 1 RED tests: canonical_url intake validation
# ---------------------------------------------------------------------------


def _minimal_kwargs(canonical_url=None):
    """Helper for canonical_url tests: minimal valid kwargs."""
    return {
        "canonical_url": canonical_url
        if canonical_url is not None
        else "https://mcp.example.com/mcp",
        "authorization_servers": [
            AuthorizationServerEntry(
                authorization_server_url="https://auth.example.com",
                issuer="https://auth.example.com",
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
            )
        ],
    }


class TestCanonicalUrlIntakeValidation:
    """Tests for ``ResourceServerAuth(canonical_url=...)`` intake validation.

    Four layers of enforcement:

    1. RFC 6750 ``error-char`` (no DQUOTE / backslash / HTAB / CR / LF
       / CTLs / non-ASCII).
    2. RFC 3986 URI structure plus RFC 9728 scheme rule with the
       documented loopback exception.
    3. RFC 3986 character correctness (no unencoded whitespace, no
       malformed percent-escapes).
    4. MCP canonical-URI rule (no fragment).
    """

    def test_resource_server_auth_rejects_canonical_url_with_space(self):
        # ``"hello world"`` has no scheme, so urlsplit yields an empty
        # netloc; the empty-host check fires before the whitespace check.
        # Either rejection classification is acceptable since the value
        # is rejected at intake.
        with pytest.raises(ValueError, match="empty netloc|whitespace|forbidden"):
            ResourceServerAuth(**_minimal_kwargs(canonical_url="hello world"))

    def test_resource_server_auth_rejects_canonical_url_without_scheme(self):
        with pytest.raises(ValueError, match="empty netloc|https|scheme"):
            ResourceServerAuth(**_minimal_kwargs(canonical_url="example.com/mcp"))

    def test_resource_server_auth_rejects_canonical_url_with_non_http_scheme(self):
        with pytest.raises(ValueError, match="https"):
            ResourceServerAuth(**_minimal_kwargs(canonical_url="ftp://example.com/mcp"))

    def test_resource_server_auth_rejects_canonical_url_http_for_non_loopback_host(self):
        with pytest.raises(ValueError, match="https|loopback|RFC 9728"):
            ResourceServerAuth(**_minimal_kwargs(canonical_url="http://api.example.com/mcp"))

    def test_resource_server_auth_rejects_canonical_url_http_for_0_0_0_0(self):
        with pytest.raises(ValueError, match="loopback"):
            ResourceServerAuth(**_minimal_kwargs(canonical_url="http://0.0.0.0:8000/mcp"))

    def test_resource_server_auth_rejects_canonical_url_http_for_private_ip(self):
        with pytest.raises(ValueError, match="loopback"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="http://192.168.1.50:8000/mcp")
            )

    def test_resource_server_auth_rejects_canonical_url_http_for_mdns_local(self):
        with pytest.raises(ValueError, match="loopback"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="http://my-dev-host.local:8000/mcp")
            )

    def test_resource_server_auth_accepts_canonical_url_http_for_127_0_0_1(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="http://127.0.0.1:8000/mcp")
        )
        assert rs.canonical_url == "http://127.0.0.1:8000/mcp"

    def test_resource_server_auth_accepts_canonical_url_http_for_localhost(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="http://localhost:8000/mcp")
        )
        assert rs.canonical_url == "http://localhost:8000/mcp"

    def test_resource_server_auth_accepts_canonical_url_http_for_ipv6_loopback(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="http://[::1]:8000/mcp")
        )
        assert rs.canonical_url == "http://[::1]:8000/mcp"

    def test_resource_server_auth_accepts_canonical_url_http_for_localhost_uppercase(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="http://LocalHost:8000/mcp")
        )
        assert rs.canonical_url == "http://LocalHost:8000/mcp"

    def test_resource_server_auth_rejects_canonical_url_with_dquote(self):
        with pytest.raises(ValueError, match="forbidden|RFC 6750"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url='https://example.com/"x"')
            )

    def test_resource_server_auth_rejects_canonical_url_with_unencoded_whitespace_in_host(
        self,
    ):
        with pytest.raises(ValueError, match="whitespace|forbidden"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://exa mple.com/mcp")
            )

    def test_resource_server_auth_rejects_canonical_url_with_unencoded_whitespace_in_path(
        self,
    ):
        with pytest.raises(ValueError, match="whitespace|forbidden"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://mcp.example.com/a b")
            )

    def test_resource_server_auth_rejects_canonical_url_with_malformed_percent_escape(
        self,
    ):
        with pytest.raises(ValueError, match="percent-escape"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://mcp.example.com/%zz")
            )

    def test_resource_server_auth_rejects_canonical_url_with_truncated_percent_escape(
        self,
    ):
        with pytest.raises(ValueError, match="percent-escape"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://mcp.example.com/path%2")
            )

    def test_resource_server_auth_accepts_canonical_url_with_well_formed_percent_escape(
        self,
    ):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="https://mcp.example.com/space%20path")
        )
        assert rs.canonical_url == "https://mcp.example.com/space%20path"

    def test_resource_server_auth_rejects_canonical_url_with_fragment(self):
        with pytest.raises(ValueError, match="fragment"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://mcp.example.com#fragment")
            )

    def test_resource_server_auth_rejects_canonical_url_with_bare_hash(self):
        with pytest.raises(ValueError, match="fragment"):
            ResourceServerAuth(
                **_minimal_kwargs(canonical_url="https://mcp.example.com/mcp#")
            )

    def test_resource_server_auth_rejects_canonical_url_with_path_and_fragment(self):
        with pytest.raises(ValueError, match="fragment"):
            ResourceServerAuth(
                **_minimal_kwargs(
                    canonical_url="https://mcp.example.com/server/mcp#section"
                )
            )

    def test_resource_server_auth_accepts_well_formed_canonical_url(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="https://mcp.example.com/mcp")
        )
        assert rs.canonical_url == "https://mcp.example.com/mcp"

    def test_resource_server_auth_accepts_canonical_url_with_query(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="https://mcp.example.com/mcp?tenant=acme")
        )
        assert rs.canonical_url == "https://mcp.example.com/mcp?tenant=acme"

    def test_resource_server_auth_accepts_canonical_url_with_port(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(canonical_url="https://mcp.example.com:8443")
        )
        assert rs.canonical_url == "https://mcp.example.com:8443"


class TestResourceServerSettingsCanonicalUrlValidation:
    """Tests for ``ResourceServerSettings`` env-var canonical_url validation.

    Pydantic field_validator runs on the ``MCP_RESOURCE_SERVER_CANONICAL_URL``
    env var path so a misconfiguration fails at ``MCPSettings.from_env()``
    rather than at first 401/403 emit.
    """

    def test_settings_rejects_canonical_url_with_space(self, monkeypatch):
        from pydantic import ValidationError

        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv("MCP_RESOURCE_SERVER_CANONICAL_URL", "hello world")
        with pytest.raises(ValidationError):
            MCPSettings.from_env()

    def test_settings_rejects_canonical_url_with_fragment(self, monkeypatch):
        from pydantic import ValidationError

        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com#fragment"
        )
        with pytest.raises(ValidationError):
            MCPSettings.from_env()

    def test_settings_rejects_canonical_url_http_for_non_loopback_host(self, monkeypatch):
        from pydantic import ValidationError

        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "http://api.example.com/mcp"
        )
        with pytest.raises(ValidationError):
            MCPSettings.from_env()

    def test_settings_accepts_canonical_url_http_for_127_0_0_1(self, monkeypatch):
        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "http://127.0.0.1:8000/mcp"
        )
        settings = MCPSettings.from_env()
        assert settings.resource_server.canonical_url == "http://127.0.0.1:8000/mcp"

    def test_settings_rejects_canonical_url_with_malformed_percent_escape(self, monkeypatch):
        from pydantic import ValidationError

        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com/%zz"
        )
        with pytest.raises(ValidationError):
            MCPSettings.from_env()

    def test_settings_accepts_canonical_url_with_query(self, monkeypatch):
        from arcade_mcp_server.settings import MCPSettings

        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL",
            "https://mcp.example.com/mcp?tenant=acme",
        )
        settings = MCPSettings.from_env()
        assert (
            settings.resource_server.canonical_url
            == "https://mcp.example.com/mcp?tenant=acme"
        )

    def test_settings_accepts_none(self, monkeypatch):
        from arcade_mcp_server.settings import MCPSettings

        # No MCP_RESOURCE_SERVER_CANONICAL_URL set; cleaned by autouse fixture.
        settings = MCPSettings.from_env()
        assert settings.resource_server.canonical_url is None


# ---------------------------------------------------------------------------
# Round 1 RED tests: PRM URL preserves query
# ---------------------------------------------------------------------------


class TestPRMMetadataUrlQueryPreservation:
    """Tests for RFC 8707 Section 2 / RFC 9728 Section 3 query preservation.

    The PRM ``resource`` field MUST match the resource identifier the
    metadata URL was derived from. The ``_build_metadata_url`` helper
    must therefore retain query components from ``canonical_url``.
    """

    def test_prm_metadata_resource_preserves_query_from_canonical_url(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(
                canonical_url="https://mcp.example.com/mcp?tenant=acme"
            )
        )
        metadata = rs.get_resource_metadata()
        assert metadata["resource"] == "https://mcp.example.com/mcp?tenant=acme"

    def test_prm_well_known_url_preserves_query(self):
        rs = ResourceServerAuth(
            **_minimal_kwargs(
                canonical_url="https://mcp.example.com/mcp?tenant=acme"
            )
        )
        middleware = ResourceServerMiddleware(
            app=Mock(),
            validator=rs,
            canonical_url="https://mcp.example.com/mcp?tenant=acme",
        )
        url = middleware._build_metadata_url()
        assert url == (
            "https://mcp.example.com/.well-known/oauth-protected-resource/mcp?tenant=acme"
        )


# ---------------------------------------------------------------------------
# Round 2 RED: behavior matrix integration tests
# ---------------------------------------------------------------------------


async def _drive_401_against(rs: ResourceServerAuth) -> str:
    """Drive a missing-Authorization 401 and return the
    decoded WWW-Authenticate header value.
    """

    async def mock_app(scope, receive, send):
        pytest.fail("App should not be called")

    middleware = ResourceServerMiddleware(
        mock_app,
        rs,
        rs.canonical_url,
    )

    scope = {"type": "http", "method": "POST", "headers": []}

    async def receive():
        return {"type": "http.request", "body": b""}

    response_headers: dict[bytes, bytes] = {}

    async def send(message):
        if message["type"] == "http.response.start":
            response_headers.update(dict(message.get("headers", [])))

    await middleware(scope, receive, send)
    return response_headers.get(b"www-authenticate", b"").decode()


class TestScopeSurfaceCombinations:
    """Tests pinning the four matrix rows: PRM and 401 scope surfaces are
    independent.
    """

    @pytest.mark.parametrize(
        "scopes_supported,challenge_scopes,expect_prm,expect_scope_in_401",
        [
            (None, None, None, None),
            (["files:read"], None, ["files:read"], None),
            (None, ["files:read"], None, "files:read"),
            (
                ["files:read"],
                ["files:read", "files:write"],
                ["files:read"],
                "files:read files:write",
            ),
        ],
        ids=[
            "both-unset",
            "prm-only",
            "challenge-only-unadvertised",
            "both-set-different",
        ],
    )
    @pytest.mark.asyncio
    async def test_scope_surface_combinations(
        self,
        jwks_data,
        scopes_supported,
        challenge_scopes,
        expect_prm,
        expect_scope_in_401,
    ):
        kwargs = {}
        if scopes_supported is not None:
            kwargs["scopes_supported"] = scopes_supported
        if challenge_scopes is not None:
            kwargs["default_challenge_scopes"] = challenge_scopes

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(**_minimal_kwargs(), **kwargs)

            metadata = rs.get_resource_metadata()
            if expect_prm is None:
                assert "scopes_supported" not in metadata
            else:
                assert metadata["scopes_supported"] == expect_prm

            www_auth = await _drive_401_against(rs)
            if expect_scope_in_401 is None:
                assert "scope=" not in www_auth, www_auth
            else:
                assert f'scope="{expect_scope_in_401}"' in www_auth, www_auth

    @pytest.mark.asyncio
    async def test_unadvertised_challenge_scope_pattern(self, jwks_data):
        """Pin the spec-permitted "challenge advertises an unadvertised scope"
        pattern: PRM omits the scope, 401 emits it.
        """
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **_minimal_kwargs(),
                default_challenge_scopes=["vendor:write"],
            )

            metadata = rs.get_resource_metadata()
            assert "scopes_supported" not in metadata

            www_auth = await _drive_401_against(rs)
            assert 'scope="vendor:write"' in www_auth, www_auth


# ---------------------------------------------------------------------------
# Round 3 RED: InsufficientScopeError + middleware 403 emit path
# ---------------------------------------------------------------------------


class TestInsufficientScopeErrorConstruction:
    """Unit tests for ``InsufficientScopeError`` construction-time validation."""

    def test_carries_required_and_granted(self):
        from arcade_mcp_server.resource_server.base import (
            AuthenticationError,
        )

        exc = InsufficientScopeError(
            required_scopes=["read"], granted_scopes=["existing"]
        )
        assert exc.required_scopes == ("read",)
        assert exc.granted_scopes == frozenset({"existing"})
        # 401 vs 403 distinction.
        assert not isinstance(exc, AuthenticationError)

    def test_validates_required_scopes_rfc6750(self):
        with pytest.raises(ValueError):
            InsufficientScopeError(required_scopes=["bad token"])

    def test_validates_granted_scopes_rfc6750(self):
        with pytest.raises(ValueError):
            InsufficientScopeError(["read"], granted_scopes=["bad token"])

    @pytest.mark.parametrize(
        "bad_description",
        [
            'has "quote"',
            r"path\to\thing",
            "col1\tcol2",
            "line1\r\nline2",
            "ctrl\x00null",
            "ctrl\x1fend",
            "ctrl\x7fdel",
            "café",
        ],
    )
    def test_rejects_bad_error_description(self, bad_description):
        with pytest.raises(ValueError):
            InsufficientScopeError(["read"], error_description=bad_description)

    def test_accepts_pure_error_char_description(self):
        exc = InsufficientScopeError(
            ["read"], error_description="needs files:write scope"
        )
        assert exc.error_description == "needs files:write scope"


class TestRFC6750QuotedValueHelpers:
    """Tests for the strict and sanitize-and-omit RFC 6750 helpers."""

    @pytest.mark.parametrize(
        "valid_value",
        [
            "safe",
            "hello world",
            "error: needs files:read",
            "!#$%&()*+,-./0123456789:;<=>?@ABC[]^_`abc{|}~",
        ],
    )
    def test_validate_accepts_valid_values(self, valid_value):
        from arcade_mcp_server.resource_server.base import (
            _validate_rfc6750_quoted_value,
        )

        assert _validate_rfc6750_quoted_value(valid_value) == valid_value

    @pytest.mark.parametrize(
        "bad_value",
        [
            '"',
            "\\",
            "\t",
            "\r",
            "\n",
            "\x00",
            "\x1f",
            "\x7f",
            "café",
            "日本語",
        ],
    )
    def test_validate_rejects_invalid_values(self, bad_value):
        from arcade_mcp_server.resource_server.base import (
            _validate_rfc6750_quoted_value,
        )

        with pytest.raises(ValueError):
            _validate_rfc6750_quoted_value(bad_value)

    @pytest.mark.parametrize(
        "valid_value",
        ["safe", "hello world"],
    )
    def test_sanitize_returns_valid_unchanged(self, valid_value):
        from arcade_mcp_server.resource_server.base import (
            _sanitize_rfc6750_quoted_value,
        )

        assert (
            _sanitize_rfc6750_quoted_value(valid_value, field="error_description")
            == valid_value
        )

    @pytest.mark.parametrize(
        "bad_value",
        ['"', "\\", "\r", "\x7f", "café"],
    )
    def test_sanitize_returns_none_for_invalid(self, bad_value):
        from arcade_mcp_server.resource_server.base import (
            _sanitize_rfc6750_quoted_value,
        )

        assert (
            _sanitize_rfc6750_quoted_value(bad_value, field="error_description")
            is None
        )


class TestInsufficientScope403Response:
    """Tests for the middleware-emitted 403 ``insufficient_scope`` response."""

    def _build_middleware_with_validator(self, jwks_data, canonical_url=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(
                **_minimal_kwargs(canonical_url=canonical_url)
            )
            return ResourceServerMiddleware(
                app=Mock(),
                validator=rs,
                canonical_url=rs.canonical_url,
            )

    def _drive_403(self, middleware, exc):
        response = middleware._create_403_insufficient_scope_response(exc)
        return response.status_code, response.headers.get("WWW-Authenticate", "")

    def test_403_returns_status_403(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        status, _ = self._drive_403(
            middleware, InsufficientScopeError(["read"])
        )
        assert status == 403

    def test_403_www_authenticate_starts_with_bearer(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware, InsufficientScopeError(["read"])
        )
        assert www_auth.startswith("Bearer ")

    def test_403_www_authenticate_includes_error_insufficient_scope(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware, InsufficientScopeError(["read"])
        )
        assert 'error="insufficient_scope"' in www_auth

    def test_403_www_authenticate_includes_required_scope_param(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware, InsufficientScopeError(["read", "write"])
        )
        assert 'scope="read write"' in www_auth

    def test_403_www_authenticate_includes_resource_metadata_url(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware, InsufficientScopeError(["read"])
        )
        assert (
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
            in www_auth
        )

    def test_403_includes_error_description_when_provided(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware,
            InsufficientScopeError(["read"], error_description="needs write"),
        )
        assert 'error_description="needs write"' in www_auth

    def test_403_omits_error_description_when_absent(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware, InsufficientScopeError(["read"])
        )
        assert "error_description=" not in www_auth

    def test_403_emits_required_scopes_only(self, jwks_data):
        """Pin the "minimum approach" choice: the header advertises only
        operation-required scopes, not the granted set.
        """
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware,
            InsufficientScopeError(
                required_scopes=["write"],
                granted_scopes=["read"],
            ),
        )
        assert 'scope="write"' in www_auth

    def test_403_does_not_include_unrelated_granted_scopes(self, jwks_data):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware,
            InsufficientScopeError(
                required_scopes=["files:write"],
                granted_scopes=["files:read", "user:email"],
            ),
        )
        assert 'scope="files:write"' in www_auth
        assert "files:read" not in www_auth
        assert "user:email" not in www_auth

    @pytest.mark.parametrize(
        "required,granted,expected",
        [
            (["read"], ["read"], "read"),
            (["write"], ["read"], "write"),
            (["read", "write"], ["read"], "read write"),
            (["files:write"], ["files:read", "user:email"], "files:write"),
        ],
    )
    def test_403_scope_param_emits_required_set(
        self, jwks_data, required, granted, expected
    ):
        middleware = self._build_middleware_with_validator(jwks_data)
        _, www_auth = self._drive_403(
            middleware,
            InsufficientScopeError(
                required_scopes=required,
                granted_scopes=granted,
            ),
        )
        assert f'scope="{expected}"' in www_auth


class TestInsufficientScope403FromHandler:
    """End-to-end test: middleware catches ``InsufficientScopeError`` raised
    from the wrapped app and emits the 403.
    """

    @pytest.mark.asyncio
    async def test_insufficient_scope_raised_during_app_dispatch_returns_403(
        self, jwks_data, rsa_joserfc_key
    ):
        """A ``InsufficientScopeError`` raised inside the wrapped ASGI
        application is caught by the middleware and translated to a 403.
        """
        # Build a token that the validator will accept so we land in the app.
        claims = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        header = {"alg": "RS256", "kid": "test-key-1"}
        token = jwt.encode(header, claims, rsa_joserfc_key)

        async def raising_app(scope, receive, send):
            raise InsufficientScopeError(["read"])

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(**_minimal_kwargs())
            middleware = ResourceServerMiddleware(
                raising_app, rs, rs.canonical_url
            )

            scope = {
                "type": "http",
                "method": "POST",
                "headers": [(b"authorization", f"Bearer {token}".encode())],
            }

            async def receive():
                return {"type": "http.request", "body": b""}

            captured: dict[str, int | dict[bytes, bytes]] = {}

            async def send(message):
                if message["type"] == "http.response.start":
                    captured["status"] = message["status"]
                    captured["headers"] = dict(message.get("headers", []))

            await middleware(scope, receive, send)

            assert captured["status"] == 403
            www_auth = captured["headers"].get(b"www-authenticate", b"").decode()
            assert 'error="insufficient_scope"' in www_auth
            assert 'scope="read"' in www_auth


class TestSanitize401HeaderEmit:
    """Tests for the 401 sanitize-and-omit policy on ``error_description``.

    The MCP spec MUST is: invalid Bearer tokens receive HTTP 401. The
    response MUST NOT fail to render when an upstream library emits a
    non-conformant ``error_description``.
    """

    def _drive_401_with_error_description(self, jwks_data, description):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rs = ResourceServerAuth(**_minimal_kwargs())
            middleware = ResourceServerMiddleware(
                app=Mock(),
                validator=rs,
                canonical_url=rs.canonical_url,
            )
            response = middleware._create_401_response(
                error="invalid_token", error_description=description
            )
            return response.status_code, response.headers.get(
                "WWW-Authenticate", ""
            )

    def test_returns_401_and_omits_error_description_when_dquote(self, jwks_data):
        status, www_auth = self._drive_401_with_error_description(
            jwks_data, 'has "quote"'
        )
        assert status == 401
        assert www_auth.startswith("Bearer ")
        assert 'error="invalid_token"' in www_auth
        assert "resource_metadata=" in www_auth
        assert "error_description=" not in www_auth

    def test_returns_401_and_omits_error_description_when_crlf(self, jwks_data):
        status, www_auth = self._drive_401_with_error_description(
            jwks_data, "line1\r\nline2"
        )
        assert status == 401
        assert "error_description=" not in www_auth

    def test_returns_401_and_omits_error_description_when_non_ascii(self, jwks_data):
        status, www_auth = self._drive_401_with_error_description(
            jwks_data, "café"
        )
        assert status == 401
        assert "error_description=" not in www_auth


# ---------------------------------------------------------------------------
# Round 4 RED: granted_scopes parsed from JWT
# ---------------------------------------------------------------------------


class TestResourceOwnerGrantedScopes:
    """Tests for ``ResourceOwner.granted_scopes`` parsed from JWT claims."""

    def _validator(self):
        return JWKSTokenValidator(
            jwks_uri="https://auth.example.com/jwks",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com/mcp",
        )

    def test_parsed_from_scope_string_claim(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scope": "read write", "sub": "u"}
        )
        assert result == frozenset({"read", "write"})

    def test_parsed_from_scp_list_claim(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scp": ["read", "write"], "sub": "u"}
        )
        assert result == frozenset({"read", "write"})

    def test_prefers_scope_string_over_scp_when_both_present(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scope": "read", "scp": ["write"], "sub": "u"}
        )
        assert result == frozenset({"read"})

    def test_empty_when_neither_claim_present(self):
        validator = self._validator()
        assert validator._extract_granted_scopes({"sub": "u"}) == frozenset()

    def test_strips_extraneous_whitespace_in_scope_string(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scope": "  read   write  ", "sub": "u"}
        )
        assert result == frozenset({"read", "write"})

    def test_handles_non_string_scope_gracefully(self):
        validator = self._validator()
        assert validator._extract_granted_scopes(
            {"scope": 12345, "sub": "u"}
        ) == frozenset()

    def test_handles_string_scp_gracefully(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scp": "read", "sub": "u"}
        )
        assert result == frozenset({"read"})

    def test_filters_rfc6750_grammar_violations(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scope": "valid bad\\token", "sub": "u"}
        )
        assert result == frozenset({"valid"})

    def test_filters_whitespace_violations_in_scp_list(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scp": ["valid", "bad token"], "sub": "u"}
        )
        assert result == frozenset({"valid"})

    def test_filters_non_ascii_tokens(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scope": "valid café", "sub": "u"}
        )
        assert result == frozenset({"valid"})

    def test_filters_empty_strings_in_scp_list(self):
        validator = self._validator()
        result = validator._extract_granted_scopes(
            {"scp": ["", "read"], "sub": "u"}
        )
        assert result == frozenset({"read"})

    def test_resource_owner_default_factory_yields_empty_frozenset(self):
        owner = ResourceOwner(user_id="u")
        assert owner.granted_scopes == frozenset()

    def test_granted_scopes_is_frozenset_type(self):
        owner = ResourceOwner(user_id="u")
        assert isinstance(owner.granted_scopes, frozenset)
