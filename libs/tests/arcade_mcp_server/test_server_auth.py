"""
Tests for front-door authentication functionality.

Tests cover:
- JWTVerifier token validation
- RemoteOAuthProvider discovery metadata
- MCPAuthMiddleware ASGI integration
- Token validation error handling
- WWW-Authenticate header compliance
"""

import json
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import jwt
import pytest
from arcade_mcp_server.server_auth.base import (
    AuthenticatedUser,
    AuthenticationError,
    InvalidTokenError,
    ServerAuthProvider,
    TokenExpiredError,
)
from arcade_mcp_server.server_auth.middleware import MCPAuthMiddleware
from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider
from arcade_mcp_server.server_auth.providers.jwt import JWTVerifier
from arcade_mcp_server.server_auth.providers.remote import RemoteOAuthProvider
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send


# Test fixtures
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
            audience="https://mcp.example.com",
            authorization_server="https://auth.example.com",
        )

        assert provider.supports_oauth_discovery() is True

    def test_get_resource_metadata(self):
        """Test getting OAuth Protected Resource Metadata."""
        provider = RemoteOAuthProvider(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="https://mcp.example.com",
            authorization_server="https://auth.example.com",
        )

        metadata = provider.get_resource_metadata("https://mcp.example.com")

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
            assert any(b"WWW-Authenticate" in k for k in response_sent["headers"].keys())

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
                audience="https://mcp.example.com",
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


# AuthKitProvider Tests
class TestAuthKitProvider:
    """Tests for AuthKitProvider class."""

    def test_automatic_jwks_configuration(self):
        """Test that AuthKitProvider automatically configures JWKS endpoint."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app",
            canonical_url="https://mcp.example.com",
        )

        assert provider.jwks_uri == "https://test-app.authkit.app/oauth2/jwks"
        assert provider.issuer == "https://test-app.authkit.app"
        assert provider.audience is None  # AuthKit doesn't use audience claim
        assert provider.authorization_server == "https://test-app.authkit.app"

    def test_supports_oauth_discovery(self):
        """Test that AuthKitProvider supports OAuth discovery."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app",
            canonical_url="https://mcp.example.com",
        )

        assert provider.supports_oauth_discovery() is True

    def test_supports_authorization_server_metadata_forwarding(self):
        """Test that AuthKitProvider supports metadata forwarding."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app",
            canonical_url="https://mcp.example.com",
        )

        assert provider.supports_authorization_server_metadata_forwarding() is True

    def test_get_authorization_server_metadata_url(self):
        """Test getting authorization server metadata URL."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app",
            canonical_url="https://mcp.example.com",
        )

        metadata_url = provider.get_authorization_server_metadata_url()
        assert metadata_url == "https://test-app.authkit.app/.well-known/oauth-authorization-server"

    def test_url_normalization(self):
        """Test that trailing slashes are removed from URLs."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app/",  # Trailing slash
            canonical_url="https://mcp.example.com/",  # Trailing slash
        )

        assert provider.authkit_domain == "https://test-app.authkit.app"
        assert provider.canonical_url == "https://mcp.example.com"

    def test_get_resource_metadata(self):
        """Test getting protected resource metadata."""
        provider = AuthKitProvider(
            authkit_domain="https://test-app.authkit.app",
            canonical_url="https://mcp.example.com",
        )

        metadata = provider.get_resource_metadata("https://mcp.example.com")

        assert metadata["resource"] == "https://mcp.example.com"
        assert metadata["authorization_servers"] == ["https://test-app.authkit.app"]

    @pytest.mark.asyncio
    async def test_validate_token_without_audience(self, rsa_keypair, jwks_data):
        """Test that AuthKitProvider accepts tokens without audience claim."""
        private_key, _ = rsa_keypair

        # AuthKit tokens don't have audience claim
        payload = {
            "sub": "user123",
            "email": "user@example.com",
            "iss": "https://test-app.authkit.app",
            # No 'aud' claim - this is normal for AuthKit
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

        # Mock JWKS response
        authkit_jwks = {
            "keys": [
                {
                    **jwks_data["keys"][0],
                    # AuthKit returns keys at /oauth2/jwks
                }
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = authkit_jwks
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            provider = AuthKitProvider(
                authkit_domain="https://test-app.authkit.app",
                canonical_url="https://mcp.example.com",
            )

            # Should validate successfully without audience claim
            user = await provider.validate_token(token)

            assert isinstance(user, AuthenticatedUser)
            assert user.user_id == "user123"
            assert user.email == "user@example.com"
            assert user.claims["iss"] == "https://test-app.authkit.app"
            assert "aud" not in user.claims  # No audience claim


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
