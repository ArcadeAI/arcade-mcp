"""
Tests for front-door authentication functionality.

Tests cover:
- JWTVerifier token validation
- RemoteOAuthProvider discovery metadata
- MCPAuthMiddleware ASGI integration
- Token validation error handling
- WWW-Authenticate header compliance
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
from arcade_mcp_server.server_auth import JWTVerifier, RemoteOAuthProvider
from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    InvalidTokenError,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.middleware import MCPAuthMiddleware
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt


# Test fixtures
@pytest.fixture(autouse=True)
def clean_auth_env():
    """Clean server auth environment variables before each test."""
    # Store original values
    env_vars = [
        "MCP_SERVER_AUTH_ENABLED",
        "MCP_SERVER_AUTH_CANONICAL_URL",
        "MCP_SERVER_AUTH_JWKS_URI",
        "MCP_SERVER_AUTH_ISSUER",
        "MCP_SERVER_AUTH_AUTHORIZATION_SERVER",
        "MCP_SERVER_AUTH_AUTHORIZATION_SERVERS",
        "MCP_SERVER_AUTH_ALGORITHM",
        "MCP_SERVER_AUTH_VERIFY_AUD",
        "MCP_SERVER_AUTH_VERIFY_EXP",
        "MCP_SERVER_AUTH_VERIFY_IAT",
        "MCP_SERVER_AUTH_VERIFY_ISS",
    ]
    original_values = {var: os.environ.get(var) for var in env_vars}

    # Clear all auth-related env vars
    for var in env_vars:
        os.environ.pop(var, None)

    yield

    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


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
    import base64

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
        "aud": "https://mcp.example.com",
        "exp": int(time.time()) + 3600,  # Expires in 1 hour
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
        "aud": "https://mcp.example.com",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        "iat": int(time.time()) - 7200,
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    return token


# JWTVerifier Tests
class TestJWTVerifier:
    """Tests for JWTVerifier class."""

    @pytest.mark.asyncio
    async def test_validate_valid_token(self, valid_jwt_token, jwks_data):
        """Test validating a valid JWT token."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            user = await verifier.validate_token(valid_jwt_token)

            assert isinstance(user, AuthenticatedUser)
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            with pytest.raises(TokenExpiredError):
                await verifier.validate_token(expired_jwt_token)

    @pytest.mark.asyncio
    async def test_validate_wrong_audience(self, serialized_private_key, jwks_data):
        """Test validating token with wrong audience."""

        # Token with wrong audience
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            with pytest.raises(InvalidTokenError, match="audience"):
                await verifier.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_wrong_issuer(self, serialized_private_key, jwks_data):
        """Test validating token with wrong issuer."""

        # Token with wrong issuer
        payload = {
            "sub": "user123",
            "iss": "https://wrong-issuer.com",  # Wrong issuer
            "aud": "https://mcp.example.com",
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            with pytest.raises(InvalidTokenError, match="issuer"):
                await verifier.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_missing_sub_claim(self, serialized_private_key, jwks_data):
        """Test validating token without sub claim."""

        # Token without sub claim
        payload = {
            "iss": "https://auth.example.com",
            "aud": "https://mcp.example.com",
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            with pytest.raises(InvalidTokenError, match="sub"):
                await verifier.validate_token(token)

    @pytest.mark.asyncio
    async def test_jwks_caching(self, valid_jwt_token, jwks_data):
        """Test that JWKS is cached to avoid repeated fetches."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
                cache_ttl=3600,
            )

            # First validation - should fetch JWKS
            await verifier.validate_token(valid_jwt_token)
            assert mock_get.call_count == 1

            # Second validation - should use cached JWKS
            await verifier.validate_token(valid_jwt_token)
            assert mock_get.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_single_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test verifier with multiple audiences accepts token with matching single aud."""
        # Token with single audience that matches one of verifier's accepted audiences
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            user = await verifier.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_list_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test verifier with multiple audiences accepts token with list aud."""
        # Token with list of audiences where one matches verifier's accepted audiences
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            user = await verifier.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_audiences_no_match(self, serialized_private_key, jwks_data):
        """Test verifier with multiple audiences rejects token with non-matching aud."""
        # Token with audience that doesn't match any of verifier's accepted audiences
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience=["https://old-mcp.example.com", "https://new-mcp.example.com"],
            )

            with pytest.raises(InvalidTokenError, match="audience"):
                await verifier.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_single_audience_with_list_token_aud(
        self, serialized_private_key, jwks_data
    ):
        """Test verifier with single audience accepts token with list aud containing match."""
        # Token with list of audiences where one matches verifier's single audience
        payload = {
            "sub": "user123",
            "iss": "https://auth.example.com",
            "aud": ["https://api1.com", "https://mcp.example.com", "https://api2.com"],
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

            verifier = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",  # Single audience
            )

            user = await verifier.validate_token(token)
            assert user.user_id == "user123"

    @pytest.mark.asyncio
    async def test_validate_multiple_issuers_efficient(self, serialized_private_key, jwks_data):
        """Test that multi-issuer validation is efficient (single decode)."""
        # Token from second issuer in list
        payload = {
            "sub": "user123",
            "iss": "https://auth2.example.com",  # Second in list
            "aud": "https://mcp.example.com",
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
                "arcade_mcp_server.server_auth.providers.jwt.jwt.decode", wraps=jwt.decode
            ) as mock_decode:
                verifier = JWTVerifier(
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    issuer=[
                        "https://auth1.example.com",
                        "https://auth2.example.com",
                        "https://auth3.example.com",
                    ],
                    audience="https://mcp.example.com",
                )

                user = await verifier.validate_token(token)
                assert user.user_id == "user123"

                # Should only decode once (efficient), not 3 times (sequential)
                assert mock_decode.call_count == 1


# RemoteOAuthProvider Tests
class TestRemoteOAuthProvider:
    """Tests for RemoteOAuthProvider class."""

    def test_supports_oauth_discovery(self):
        """Test that RemoteOAuthProvider supports OAuth discovery."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig

        provider = RemoteOAuthProvider(
            canonical_url="https://mcp.example.com",
            authorization_servers=[
                AuthorizationServerConfig(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        )

        assert provider.supports_oauth_discovery() is True

    def test_get_resource_metadata(self):
        """Test getting OAuth Protected Resource Metadata."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig

        provider = RemoteOAuthProvider(
            canonical_url="https://mcp.example.com",
            authorization_servers=[
                AuthorizationServerConfig(
                    authorization_server_url="https://auth.example.com",
                    issuer="https://auth.example.com",
                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                )
            ],
        )

        metadata = provider.get_resource_metadata()

        assert metadata["resource"] == "https://mcp.example.com"
        assert metadata["authorization_servers"] == ["https://auth.example.com"]


# MCPAuthMiddleware Tests
class TestMCPAuthMiddleware:
    """Tests for MCPAuthMiddleware class."""

    @pytest.mark.asyncio
    async def test_authenticated_request(self, valid_jwt_token, jwks_data):
        """Test authenticated request passes through."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            provider = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            # Mock app
            app_called = False

            async def mock_app(scope, receive, send):
                nonlocal app_called
                app_called = True
                assert "authenticated_user" in scope
                assert scope["authenticated_user"].user_id == "user123"

            middleware = MCPAuthMiddleware(
                mock_app,
                provider,
                "https://mcp.example.com",
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

            provider = JWTVerifier(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                audience="https://mcp.example.com",
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = MCPAuthMiddleware(
                mock_app,
                provider,
                "https://mcp.example.com",
            )

            # Create mock request without auth header
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

            from arcade_mcp_server.server_auth import AuthorizationServerConfig

            provider = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/.well-known/jwks.json",
                    )
                ],
            )

            async def mock_app(scope, receive, send):
                pytest.fail("App should not be called")

            middleware = MCPAuthMiddleware(
                mock_app,
                provider,
                "https://mcp.example.com",
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

            # Should include Bearer scheme
            assert "Bearer" in www_auth
            # Should include resource_metadata URL
            assert "resource_metadata=" in www_auth
            assert "/.well-known/oauth-protected-resource" in www_auth


class TestEnvVarConfiguration:
    """Tests for front-door auth env var configuration support."""

    @pytest.mark.asyncio
    async def test_remote_oauth_env_var_precedence(self, monkeypatch):
        """Test that environment variables override parameters."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig

        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://env-mcp.example.com")
        monkeypatch.setenv(
            "MCP_SERVER_AUTH_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url":"https://env.example.com","issuer":"https://env.example.com","jwks_uri":"https://env.example.com/jwks"}]',
        )

        auth = RemoteOAuthProvider(
            canonical_url="https://param-mcp.example.com",
            authorization_servers=[
                AuthorizationServerConfig(
                    authorization_server_url="https://param.example.com",
                    issuer="https://param.example.com",
                    jwks_uri="https://param.example.com/jwks",
                )
            ],
        )

        assert auth.canonical_url == "https://env-mcp.example.com"
        metadata = auth.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://env.example.com"]

    @pytest.mark.asyncio
    async def test_remote_oauth_all_env_vars(self, monkeypatch):
        """Test RemoteOAuthProvider with all env vars, no parameters."""
        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://mcp.example.com")
        monkeypatch.setenv(
            "MCP_SERVER_AUTH_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url":"https://auth.example.com","issuer":"https://auth.example.com","jwks_uri":"https://auth.example.com/jwks","algorithm":"RS256","verify_aud":false}]',
        )

        auth = RemoteOAuthProvider()

        assert auth.canonical_url == "https://mcp.example.com"
        metadata = auth.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://auth.example.com"]

    def test_remote_oauth_missing_required(self):
        """Test that missing required fields raise ValueError."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig

        with pytest.raises(ValueError, match="'canonical_url' required"):
            RemoteOAuthProvider(
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
                # Missing canonical_url
            )

    @pytest.mark.asyncio
    async def test_worker_no_canonical_url_for_jwt_verifier(self):
        """Test that worker doesn't require canonical_url for JWTVerifier."""
        from arcade_core.catalog import ToolCatalog
        from arcade_mcp_server.worker import create_arcade_mcp

        # JWTVerifier uses explicit parameters (no env vars)
        jwt_auth = JWTVerifier(
            jwks_uri="https://auth.example.com/jwks",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com",
        )

        catalog = ToolCatalog()
        # Shouldn't raise as JWTVerifier doesn't support OAuth discovery
        app = create_arcade_mcp(catalog, server_auth_provider=jwt_auth)
        assert app is not None

    def test_worker_requires_canonical_url_for_remote_oauth(self):
        """Test that RemoteOAuthProvider validation happens during init."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig

        with pytest.raises(ValueError, match="'canonical_url' required"):
            RemoteOAuthProvider(
                authorization_servers=[
                    AuthorizationServerConfig(
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
    async def test_remote_oauth_provider_multiple_as_shared_jwks(self, jwks_data, valid_jwt_token):
        """Test multiple AS URLs with same JWKS (regional endpoints)."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig, RemoteOAuthProvider

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            auth = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth-us.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    ),
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth-eu.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    ),
                ],
            )

            # Verify metadata returns all AS URLs
            metadata = auth.get_resource_metadata()
            assert metadata["resource"] == "https://mcp.example.com"
            assert metadata["authorization_servers"] == [
                "https://auth-us.example.com",
                "https://auth-eu.example.com",
            ]

            # Verify token validation works
            user = await auth.validate_token(valid_jwt_token)
            assert user.user_id == "user123"
            assert user.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_remote_oauth_provider_multiple_as_different_jwks(self, rsa_keypair, jwks_data):
        """Test multiple AS with different JWKS (multi-IdP)."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig, RemoteOAuthProvider

        private_key, _ = rsa_keypair

        # Create token from first issuer
        payload1 = {
            "sub": "user123",
            "email": "user@workos.com",
            "iss": "https://workos.authkit.app",
            "aud": "https://mcp.example.com",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token1 = jwt.encode(
            payload1,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

        # Create token from second issuer
        payload2 = {
            "sub": "user456",
            "email": "user@github.com",
            "iss": "https://github.com",
            "aud": "https://mcp.example.com",
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

            auth = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://workos.authkit.app",
                        issuer="https://workos.authkit.app",
                        jwks_uri="https://workos.authkit.app/oauth2/jwks",
                    ),
                    AuthorizationServerConfig(
                        authorization_server_url="https://github.com/login/oauth",
                        issuer="https://github.com",
                        jwks_uri="https://token.actions.githubusercontent.com/.well-known/jwks",
                    ),
                ],
            )

            # Verify metadata returns all AS URLs
            metadata = auth.get_resource_metadata()
            assert metadata["authorization_servers"] == [
                "https://workos.authkit.app",
                "https://github.com/login/oauth",
            ]

            # Verify tokens from both issuers work
            user1 = await auth.validate_token(token1)
            assert user1.user_id == "user123"
            assert user1.email == "user@workos.com"

            user2 = await auth.validate_token(token2)
            assert user2.user_id == "user456"
            assert user2.email == "user@github.com"

    @pytest.mark.asyncio
    async def test_remote_oauth_provider_rejects_unconfigured_as(self, rsa_keypair, jwks_data):
        """Test that tokens from unlisted AS are rejected."""
        from arcade_mcp_server.server_auth import RemoteOAuthProvider
        from arcade_mcp_server.server_auth.base import InvalidTokenError

        private_key, _ = rsa_keypair

        # Create token from unauthorized issuer
        payload = {
            "sub": "user123",
            "email": "user@evil.com",
            "iss": "https://evil.com",  # Not in configured list
            "aud": "https://mcp.example.com",
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

            from arcade_mcp_server.server_auth import AuthorizationServerConfig

            auth = RemoteOAuthProvider(
                canonical_url="https://mcp.example.com",
                authorization_servers=[
                    AuthorizationServerConfig(
                        authorization_server_url="https://auth.example.com",
                        issuer="https://auth.example.com",
                        jwks_uri="https://auth.example.com/jwks",
                    )
                ],
            )

            # Should reject token from unauthorized issuer
            with pytest.raises(
                InvalidTokenError,
                match="Token validation failed for all configured authorization servers",
            ):
                await auth.validate_token(token)

    def test_authorization_servers_env_var_parsing_json(self, monkeypatch):
        """Test parsing JSON array of AS configs from env var."""
        from arcade_mcp_server.server_auth import RemoteOAuthProvider

        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://mcp.example.com")
        monkeypatch.setenv(
            "MCP_SERVER_AUTH_AUTHORIZATION_SERVERS",
            '[{"authorization_server_url": "https://auth1.com", "issuer": "https://auth1.com", "jwks_uri": "https://auth1.com/jwks"}]',
        )

        auth = RemoteOAuthProvider()

        metadata = auth.get_resource_metadata()
        assert metadata["authorization_servers"] == ["https://auth1.com"]

    def test_resource_metadata_multiple_as(self):
        """Test that resource metadata returns all AS URLs."""
        from arcade_mcp_server.server_auth import AuthorizationServerConfig, RemoteOAuthProvider

        auth = RemoteOAuthProvider(
            canonical_url="https://mcp.example.com",
            authorization_servers=[
                AuthorizationServerConfig(
                    authorization_server_url="https://auth1.example.com",
                    issuer="https://auth1.example.com",
                    jwks_uri="https://auth1.example.com/jwks",
                ),
                AuthorizationServerConfig(
                    authorization_server_url="https://auth2.example.com",
                    issuer="https://auth2.example.com",
                    jwks_uri="https://auth2.example.com/jwks",
                ),
                AuthorizationServerConfig(
                    authorization_server_url="https://auth3.example.com",
                    issuer="https://auth3.example.com",
                    jwks_uri="https://auth3.example.com/jwks",
                ),
            ],
        )

        metadata = auth.get_resource_metadata()
        assert metadata["resource"] == "https://mcp.example.com"
        assert len(metadata["authorization_servers"]) == 3
        assert "https://auth1.example.com" in metadata["authorization_servers"]
        assert "https://auth2.example.com" in metadata["authorization_servers"]
        assert "https://auth3.example.com" in metadata["authorization_servers"]
