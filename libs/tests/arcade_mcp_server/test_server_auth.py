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

import jwt
import pytest
from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    InvalidTokenError,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.middleware import MCPAuthMiddleware
from arcade_mcp_server.server_auth.providers.jwt import JWTVerifier
from arcade_mcp_server.server_auth.providers.remote import RemoteOAuthProvider
from cryptography.hazmat.primitives.asymmetric import rsa


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
        "MCP_SERVER_AUTH_ALGORITHMS",
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
    async def test_validate_wrong_audience(self, rsa_keypair, jwks_data):
        """Test validating token with wrong audience."""
        private_key, _ = rsa_keypair

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
            private_key,
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
    async def test_validate_wrong_issuer(self, rsa_keypair, jwks_data):
        """Test validating token with wrong issuer."""
        private_key, _ = rsa_keypair

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
            private_key,
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
    async def test_validate_missing_sub_claim(self, rsa_keypair, jwks_data):
        """Test validating token without sub claim."""
        private_key, _ = rsa_keypair

        # Token without sub claim
        payload = {
            "iss": "https://auth.example.com",
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


# RemoteOAuthProvider Tests
class TestRemoteOAuthProvider:
    """Tests for RemoteOAuthProvider class."""

    def test_supports_oauth_discovery(self):
        """Test that RemoteOAuthProvider supports OAuth discovery."""
        provider = RemoteOAuthProvider(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            canonical_url="https://mcp.example.com",
            authorization_server="https://auth.example.com",
        )

        assert provider.supports_oauth_discovery() is True

    def test_get_resource_metadata(self):
        """Test getting OAuth Protected Resource Metadata."""
        provider = RemoteOAuthProvider(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            canonical_url="https://mcp.example.com",
            authorization_server="https://auth.example.com",
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

            provider = RemoteOAuthProvider(
                jwks_uri="https://auth.example.com/.well-known/jwks.json",
                issuer="https://auth.example.com",
                canonical_url="https://mcp.example.com",
                authorization_server="https://auth.example.com",
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
        monkeypatch.setenv("MCP_SERVER_AUTH_JWKS_URI", "https://env.example.com/jwks")
        monkeypatch.setenv("MCP_SERVER_AUTH_ISSUER", "https://env.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://env-mcp.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_AUTHORIZATION_SERVER", "https://env.example.com")

        auth = RemoteOAuthProvider(
            jwks_uri="https://param.example.com/jwks",
            issuer="https://param.example.com",
            canonical_url="https://param-mcp.example.com",
            authorization_server="https://param.example.com",
        )

        assert auth.jwks_uri == "https://env.example.com/jwks"
        assert auth.issuer == "https://env.example.com"
        assert auth.canonical_url == "https://env-mcp.example.com"
        assert auth.authorization_server == "https://env.example.com"

    @pytest.mark.asyncio
    async def test_remote_oauth_all_env_vars(self, monkeypatch):
        """Test RemoteOAuthProvider with all env vars, no parameters."""
        monkeypatch.setenv("MCP_SERVER_AUTH_JWKS_URI", "https://auth.example.com/jwks")
        monkeypatch.setenv("MCP_SERVER_AUTH_ISSUER", "https://auth.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://mcp.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_AUTHORIZATION_SERVER", "https://auth.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_ALGORITHMS", "RS256,RS384")
        monkeypatch.setenv("MCP_SERVER_AUTH_VERIFY_AUD", "false")

        auth = RemoteOAuthProvider()

        assert auth.jwks_uri == "https://auth.example.com/jwks"
        assert auth.canonical_url == "https://mcp.example.com"
        assert auth.algorithms == ["RS256", "RS384"]
        assert auth.verify_options.verify_aud is False

    def test_remote_oauth_missing_required(self):
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="RemoteOAuthProvider requires"):
            RemoteOAuthProvider(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                # Missing canonical_url and authorization_server
            )

    @pytest.mark.asyncio
    async def test_jwt_verifier_env_var_support(self, monkeypatch):
        """Test JWTVerifier with environment variables."""
        monkeypatch.setenv("MCP_SERVER_AUTH_JWKS_URI", "https://auth.example.com/jwks")
        monkeypatch.setenv("MCP_SERVER_AUTH_ISSUER", "https://auth.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://mcp.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_ALGORITHMS", "RS256,ES256")

        auth = JWTVerifier()

        assert auth.jwks_uri == "https://auth.example.com/jwks"
        assert auth.issuer == "https://auth.example.com"
        assert auth.audience == "https://mcp.example.com"
        assert auth.algorithms == ["RS256", "ES256"]

    @pytest.mark.asyncio
    async def test_worker_no_canonical_url_for_jwt_verifier(self, monkeypatch):
        """Test that worker doesn't require canonical_url for JWTVerifier."""
        from arcade_core.catalog import ToolCatalog
        from arcade_mcp_server.worker import create_arcade_mcp

        monkeypatch.setenv("MCP_SERVER_AUTH_JWKS_URI", "https://auth.example.com/jwks")
        monkeypatch.setenv("MCP_SERVER_AUTH_ISSUER", "https://auth.example.com")
        monkeypatch.setenv("MCP_SERVER_AUTH_CANONICAL_URL", "https://mcp.example.com")

        jwt_auth = JWTVerifier()

        catalog = ToolCatalog()
        # Shouldn't raise as JWTVerifier doesn't support OAuth discovery
        app = create_arcade_mcp(catalog, auth_provider=jwt_auth)
        assert app is not None

    def test_worker_requires_canonical_url_for_remote_oauth(self):
        """Test that RemoteOAuthProvider validation happens during init."""
        with pytest.raises(ValueError, match="RemoteOAuthProvider requires"):
            RemoteOAuthProvider(
                jwks_uri="https://auth.example.com/jwks",
                issuer="https://auth.example.com",
                authorization_server="https://auth.example.com",
                # Missing canonical_url
            )
