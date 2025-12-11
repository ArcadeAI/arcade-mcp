import base64
import time
from unittest.mock import Mock, patch

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server.resource_server import (
    AccessTokenValidationOptions,
    AuthorizationServerEntry,
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
from jose import jwt


# Test fixtures
@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    """Clean server auth environment variables before each test."""
    env_vars = [
        "MCP_RESOURCE_SERVER_CANONICAL_URL",
        "MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS",
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
def serialized_private_key(rsa_keypair):
    """Generate private key as PEM format for testing."""
    private_key, _ = rsa_keypair
    # Serialize private key to PEM format for python-jose
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
def valid_jwt_token(rsa_keypair):
    """Generate valid JWT token for testing."""
    private_key, _ = rsa_keypair

    payload = {
        "sub": "user123",
        "email": "user@example.com",
        "iss": "https://auth.example.com",
        "aud": "https://mcp.example.com/mcp",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    return token


@pytest.fixture
def expired_jwt_token(rsa_keypair):
    """Generate expired JWT token for testing."""
    private_key, _ = rsa_keypair

    payload = {
        "sub": "user123",
        "email": "user@example.com",
        "iss": "https://auth.example.com",
        "aud": "https://mcp.example.com/mcp",
        "exp": int(time.time()) - 3600,
        "iat": int(time.time()) - 7200,
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

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
    async def test_validate_wrong_audience(self, serialized_private_key, jwks_data):
        """Test validating token with wrong audience."""
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://wrong-server.com",  # Wrong audience
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_wrong_issuer(self, serialized_private_key, jwks_data):
        """Test validating token with wrong issuer."""
        payload = {
            "sub": "user123",
            "iss": "https://wrong-issuer.com",  # Wrong issuer
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_missing_sub_claim(self, serialized_private_key, jwks_data):
        """Test validating token without sub claim."""
        payload = {
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_multiple_audiences_single_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test validator with multiple audiences accepts token with matching single aud."""
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://old-mcp.example.com",  # Matches first audience
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_multiple_audiences_list_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test validator with multiple audiences accepts token with list aud."""
        # Token with list of audiences where one matches the validator's accepted audiences
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": ["https://api1.com", "https://new-mcp.example.com"],  # Second matches
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_multiple_audiences_no_match(self, serialized_private_key, jwks_data):
        """Test validator with multiple audiences rejects token with non-matching aud."""
        # Token with audience that doesn't match any of validator's accepted audiences
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://different-server.com",  # Doesn't match
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_single_audience_with_list_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test validator with single audience accepts token with list aud containing match."""
        # Token with list of audiences where one matches validator's single audience
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": ["https://api1.com", "https://mcp.example.com/mcp", "https://api2.com"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_multiple_issuers_efficient(self, serialized_private_key, jwks_data):
        """Test that multi-issuer validation is efficient (single decode)."""
        # Token from second issuer in list
        payload = {
            "sub": "user123",
            "iss": "https://auth2.example.com",  # Second in list
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Patch jwt.decode to count calls
            with patch(
                "arcade_mcp_server.resource_server.validators.jwks.jwt.decode", wraps=jwt.decode
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
    async def test_validate_nbf_claim_before_time(self, serialized_private_key, jwks_data):
        """Test that token with nbf claim in the future is rejected."""
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 7200,  # expires in 2 hours
            "iat": int(time.time()),
            "nbf": int(time.time()) + 3600,  # Not valid for 1 hour
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_nbf_claim_disabled(self, serialized_private_key, jwks_data):
        """Test that token with nbf in future is accepted when verify_nbf=False."""
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 7200,  # expires in 2 hours
            "iat": int(time.time()),
            "nbf": int(time.time()) + 3600,  # Not valid for 1 hour
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_validate_with_leeway(self, serialized_private_key, jwks_data):
        """Test that leeway allows slightly expired tokens."""
        # Token expired 30 seconds ago
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) - 30,
            "iat": int(time.time()) - 3600,
        }

        token = jwt.encode(
            payload,
            serialized_private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_expected_audiences_override(self, rsa_keypair, jwks_data):
        """Test that expected_audiences overrides canonical_url for audience validation."""
        private_key, _ = rsa_keypair

        # Token with custom audience
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "my-authkit-client-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_expected_audiences_multiple_values(self, rsa_keypair, jwks_data):
        """Test that multiple expected_audiences work correctly."""
        private_key, _ = rsa_keypair

        # Token with one of the expected audiences
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "secondary-client-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_expected_audiences_defaults_to_canonical_url(self, rsa_keypair, jwks_data):
        """Test that without expected_audiences, canonical_url is used for audience validation."""
        private_key, _ = rsa_keypair

        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_expected_audiences_wrong_audience_rejected(self, rsa_keypair, jwks_data):
        """Test that tokens with wrong audience are rejected even with expected_audiences."""
        private_key, _ = rsa_keypair

        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": "wrong-client-id",  # Not in expected_audiences list
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_resource_server_multiple_as_different_jwks(self, rsa_keypair, jwks_data):
        """Test multiple AS with different JWKS (multi-IdP)."""
        private_key, _ = rsa_keypair

        payload1 = {
            "sub": "user123",
            "email": "user@workos.com",
            "iss": "https://workos.authkit.app",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token1 = jwt.encode(
            payload1,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

        payload2 = {
            "sub": "user456",
            "email": "user@keycloak.com",
            "iss": "http://localhost:8080/realms/mcp-test",
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token2 = jwt.encode(
            payload2,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
    async def test_resource_server_rejects_unconfigured_as(self, rsa_keypair, jwks_data):
        """Test that tokens from unlisted AS are rejected."""
        private_key, _ = rsa_keypair

        payload = {
            "sub": "user123",
            "email": "user@evil.com",
            "iss": "https://evil.com",  # Not in configured list (unauthorized issuer)
            "aud": "https://mcp.example.com/mcp",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

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
