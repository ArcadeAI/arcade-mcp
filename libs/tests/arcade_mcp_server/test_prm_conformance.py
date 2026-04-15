"""Tests for OAuth/PRM conformance — Phase 8.

Covers:
- _extract_scopes helper (pure unit tests)
- Insufficient-scope handler-level error (via handle_message)
- _transport metadata stripping in HTTP transport
- Stdio _transport passthrough
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from arcade_mcp_server.resource_server.base import (
    InsufficientScopeError,
    ResourceOwner,
)
from arcade_mcp_server.server import (
    INSUFFICIENT_SCOPE_ERROR_CODE,
    MCPServer,
    _extract_scopes,
)
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport
from arcade_mcp_server.types import JSONRPCError


# ---------------------------------------------------------------------------
# TestExtractScopes — pure unit tests
# ---------------------------------------------------------------------------


class TestExtractScopes:
    """Tests for _extract_scopes helper -- normalizes scope extraction across
    OAuth provider formats (RFC 6749 space-delimited string, Azure AD 'scp' claim,
    array-of-strings format). See AD 11 scope-check architecture."""

    def test_scope_claim_space_delimited_string(self) -> None:
        """Standard RFC 6749 section 3.3 format: space-delimited string in 'scope' claim."""
        claims = {"scope": "files:read files:write profile"}
        assert _extract_scopes(claims) == {"files:read", "files:write", "profile"}

    def test_scp_claim_space_delimited_string(self) -> None:
        """Azure AD / Microsoft Entra uses 'scp' claim instead of 'scope'."""
        claims = {"scp": "User.Read Mail.Send"}
        assert _extract_scopes(claims) == {"User.Read", "Mail.Send"}

    def test_scope_claim_array_of_strings(self) -> None:
        """Some providers (Auth0 custom claims) emit scopes as a JSON array."""
        claims = {"scope": ["files:read", "files:write"]}
        assert _extract_scopes(claims) == {"files:read", "files:write"}

    def test_scp_claim_array_of_strings(self) -> None:
        """Azure AD v2 can emit 'scp' as array."""
        claims = {"scp": ["User.Read", "Mail.Send"]}
        assert _extract_scopes(claims) == {"User.Read", "Mail.Send"}

    def test_scope_takes_precedence_over_scp(self) -> None:
        """When both 'scope' and 'scp' are present, 'scope' wins (checked first)."""
        claims = {"scope": "a b", "scp": "c d"}
        assert _extract_scopes(claims) == {"a", "b"}

    def test_no_scope_claims_returns_empty_set(self) -> None:
        """Token with neither 'scope' nor 'scp' claim returns empty set."""
        claims = {"sub": "alice", "iss": "https://example.com"}
        assert _extract_scopes(claims) == set()

    def test_empty_scope_string_returns_empty_set(self) -> None:
        """Empty string scope returns empty set (not a set containing empty string)."""
        claims = {"scope": ""}
        result = _extract_scopes(claims)
        assert result == set()  # "".split() == []

    def test_array_with_non_string_elements_filtered(self) -> None:
        """Non-string elements in array format are filtered out."""
        claims = {"scope": ["valid", 123, None, "also_valid"]}
        assert _extract_scopes(claims) == {"valid", "also_valid"}


# ---------------------------------------------------------------------------
# TestInsufficientScopeError — exception dataclass sanity
# ---------------------------------------------------------------------------


class TestInsufficientScopeErrorException:
    """Verify InsufficientScopeError carries the expected attributes."""

    def test_attributes(self) -> None:
        err = InsufficientScopeError(
            required_scopes=["a", "b"],
            granted_scopes=["a"],
            message="nope",
        )
        assert err.required_scopes == ["a", "b"]
        assert err.granted_scopes == ["a"]
        assert str(err) == "nope"

    def test_default_message(self) -> None:
        err = InsufficientScopeError(required_scopes=[], granted_scopes=[])
        assert str(err) == "Insufficient scope"


# ---------------------------------------------------------------------------
# TestInsufficientScopeServerHandler — unit-level via handle_message
# ---------------------------------------------------------------------------


class TestInsufficientScopeServerHandler:
    """Handler-level scope check returning INSUFFICIENT_SCOPE_ERROR_CODE.
    Uses handle_message() directly with a mock resource_owner."""

    @pytest_asyncio.fixture
    async def initialized_session_2025_11_25(
        self, mcp_server: MCPServer, mock_read_stream: AsyncMock, mock_write_stream: AsyncMock
    ) -> ServerSession:
        """Create a session negotiated at 2025-11-25."""
        session = ServerSession(
            server=mcp_server,
            read_stream=mock_read_stream,
            write_stream=mock_write_stream,
            init_options={"transport_type": "http"},
        )
        session.mark_initialized()
        session.negotiated_version = "2025-11-25"
        session._negotiated_capabilities = {
            "tools": {"listChanged": True},
            "tasks": {"list": {}, "cancel": {}, "requests": {"tools": {"call": {}}}},
        }
        return session

    @staticmethod
    def _call_scoped_tool_message(msg_id: int = 1) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.scoped_tool",
                "arguments": {"text": "hello"},
            },
        }

    @pytest.mark.asyncio
    async def test_handler_returns_insufficient_scope_error(
        self,
        mcp_server: MCPServer,
        initialized_session_2025_11_25: ServerSession,
    ) -> None:
        """Token with only files:read when tool requires files:read + files:write
        must return INSUFFICIENT_SCOPE_ERROR_CODE with _transport metadata."""
        resource_owner = ResourceOwner(
            user_id="alice",
            claims={"scope": "files:read", "iss": "https://auth.example.com", "sub": "alice"},
        )

        response = await mcp_server.handle_message(
            self._call_scoped_tool_message(),
            session=initialized_session_2025_11_25,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == INSUFFICIENT_SCOPE_ERROR_CODE
        assert response.error["message"] == "Insufficient scope"

        data = response.error["data"]
        assert data["_transport"]["http_status"] == 403
        assert "files:write" in data["required_scopes"]
        assert "files:read" in data["required_scopes"]
        assert "files:read" in data["granted_scopes"]

    @pytest.mark.asyncio
    async def test_handler_transport_hint_includes_www_authenticate(
        self,
        mcp_server: MCPServer,
        initialized_session_2025_11_25: ServerSession,
    ) -> None:
        """_transport.www_authenticate must contain error=insufficient_scope
        and the required scopes."""
        resource_owner = ResourceOwner(
            user_id="alice",
            claims={"scope": "files:read", "iss": "https://auth.example.com", "sub": "alice"},
        )

        response = await mcp_server.handle_message(
            self._call_scoped_tool_message(),
            session=initialized_session_2025_11_25,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        www_auth = response.error["data"]["_transport"]["www_authenticate"]
        assert 'error="insufficient_scope"' in www_auth
        assert "files:read" in www_auth
        assert "files:write" in www_auth

    @pytest.mark.asyncio
    async def test_handler_passes_when_scopes_sufficient(
        self,
        mcp_server: MCPServer,
        initialized_session_2025_11_25: ServerSession,
    ) -> None:
        """Token with all required scopes should NOT trigger scope error.
        The tool may still fail for other reasons (e.g. no Arcade API key),
        but it must NOT be INSUFFICIENT_SCOPE_ERROR_CODE."""
        resource_owner = ResourceOwner(
            user_id="alice",
            claims={
                "scope": "files:read files:write",
                "iss": "https://auth.example.com",
                "sub": "alice",
            },
        )

        response = await mcp_server.handle_message(
            self._call_scoped_tool_message(),
            session=initialized_session_2025_11_25,
            resource_owner=resource_owner,
        )

        # Response may be an error (e.g., missing Arcade key) but must NOT
        # be the insufficient_scope error.
        if isinstance(response, JSONRPCError):
            assert response.error["code"] != INSUFFICIENT_SCOPE_ERROR_CODE

    @pytest.mark.asyncio
    async def test_handler_no_scope_check_without_resource_owner(
        self,
        mcp_server: MCPServer,
        initialized_session_2025_11_25: ServerSession,
    ) -> None:
        """Without a resource_owner (e.g. stdio transport), the scope check
        is skipped entirely -- no INSUFFICIENT_SCOPE_ERROR_CODE."""
        response = await mcp_server.handle_message(
            self._call_scoped_tool_message(),
            session=initialized_session_2025_11_25,
            resource_owner=None,
        )

        if isinstance(response, JSONRPCError):
            assert response.error["code"] != INSUFFICIENT_SCOPE_ERROR_CODE


# ---------------------------------------------------------------------------
# TestTransportMetadataStripping — HTTP transport strips _transport
# ---------------------------------------------------------------------------


class TestTransportMetadataStripping:
    """Tests for _transport metadata handling per AD 11's contract.
    HTTP transport MUST strip _transport from response body; stdio sends as-is."""

    def test_http_transport_strips_transport_metadata(self) -> None:
        """_create_json_response must strip _transport from the error data
        and set the HTTP status + WWW-Authenticate header."""
        error = JSONRPCError(
            id=1,
            error={
                "code": INSUFFICIENT_SCOPE_ERROR_CODE,
                "message": "Insufficient scope",
                "data": {
                    "_transport": {
                        "http_status": 403,
                        "www_authenticate": 'Bearer error="insufficient_scope", scope="files:read files:write"',
                    },
                    "required_scopes": ["files:read", "files:write"],
                    "granted_scopes": ["files:read"],
                },
            },
        )

        transport = HTTPStreamableTransport(mcp_session_id="test-session")
        response = transport._create_json_response(error)

        # HTTP status should be 403
        assert response.status_code == 403

        # WWW-Authenticate header should be set
        assert "WWW-Authenticate" in response.headers
        assert 'error="insufficient_scope"' in response.headers["WWW-Authenticate"]

        # Body should NOT contain _transport
        body = json.loads(response.body)
        error_data = body.get("error", {}).get("data", {})
        assert "_transport" not in error_data
        # But other data should remain
        assert "required_scopes" in error_data

    def test_http_transport_drops_empty_data_after_strip(self) -> None:
        """If _transport is the only key in data, data should be removed entirely."""
        error = JSONRPCError(
            id=1,
            error={
                "code": INSUFFICIENT_SCOPE_ERROR_CODE,
                "message": "Insufficient scope",
                "data": {
                    "_transport": {
                        "http_status": 403,
                        "www_authenticate": "Bearer",
                    },
                },
            },
        )

        transport = HTTPStreamableTransport(mcp_session_id="test-session")
        response = transport._create_json_response(error)

        assert response.status_code == 403
        body = json.loads(response.body)
        # data should be absent or empty
        assert "data" not in body.get("error", {})

    def test_http_transport_ignores_non_scope_errors(self) -> None:
        """Errors with a different code should NOT be modified."""
        error = JSONRPCError(
            id=1,
            error={
                "code": -32600,
                "message": "Invalid request",
                "data": {"_transport": {"http_status": 403}},
            },
        )

        transport = HTTPStreamableTransport(mcp_session_id="test-session")
        response = transport._create_json_response(error)

        # Status should remain default (200)
        assert response.status_code == 200
        # _transport should still be in body (not stripped for non-scope errors)
        body = json.loads(response.body)
        assert "_transport" in body["error"]["data"]

    def test_stdio_includes_transport_metadata_as_is(self) -> None:
        """Stdio transport sends JSONRPCError as-is with _transport intact.
        This is tested by simply serializing the model without the HTTP layer."""
        error = JSONRPCError(
            id=1,
            error={
                "code": INSUFFICIENT_SCOPE_ERROR_CODE,
                "message": "Insufficient scope",
                "data": {
                    "_transport": {
                        "http_status": 403,
                        "www_authenticate": 'Bearer error="insufficient_scope"',
                    },
                    "required_scopes": ["files:read"],
                    "granted_scopes": [],
                },
            },
        )

        # Stdio transport uses model_dump_json directly -- no stripping
        raw = json.loads(error.model_dump_json(by_alias=True))
        error_data = raw["error"]["data"]
        assert "_transport" in error_data
        assert error_data["_transport"]["http_status"] == 403

    def test_sse_event_data_strips_transport_metadata(self) -> None:
        """_create_event_data (SSE path) should also strip _transport."""
        from arcade_mcp_server.transports.http_streamable import EventMessage

        error = JSONRPCError(
            id=1,
            error={
                "code": INSUFFICIENT_SCOPE_ERROR_CODE,
                "message": "Insufficient scope",
                "data": {
                    "_transport": {
                        "http_status": 403,
                        "www_authenticate": "Bearer",
                    },
                    "required_scopes": ["a"],
                    "granted_scopes": [],
                },
            },
        )

        transport = HTTPStreamableTransport(mcp_session_id="test-session")
        event_msg = EventMessage(message=error)
        event_data = transport._create_event_data(event_msg)

        parsed = json.loads(event_data["data"])
        error_data = parsed.get("error", {}).get("data", {})
        assert "_transport" not in error_data
        assert "required_scopes" in error_data


# ---------------------------------------------------------------------------
# TestMiddlewareScopeParam — 401 WWW-Authenticate includes scope=""
# ---------------------------------------------------------------------------


class TestMiddlewareScopeParam:
    """Verify that the 401 response from ResourceServerMiddleware includes
    the scope= parameter (SEP-985 SHOULD)."""

    def test_401_www_authenticate_includes_scope(self) -> None:
        """The _create_401_response should include scope="" in WWW-Authenticate."""
        from unittest.mock import Mock

        from arcade_mcp_server.resource_server.middleware import ResourceServerMiddleware

        validator = Mock()
        validator.supports_oauth_discovery.return_value = False

        middleware = ResourceServerMiddleware(
            app=Mock(),
            validator=validator,
            canonical_url=None,
        )

        response = middleware._create_401_response()
        www_auth = response.headers.get("WWW-Authenticate", "")
        assert 'scope=""' in www_auth

    def test_401_with_discovery_includes_scope(self) -> None:
        """With OAuth discovery enabled, scope="" should still appear."""
        from unittest.mock import Mock

        from arcade_mcp_server.resource_server.middleware import ResourceServerMiddleware

        validator = Mock()
        validator.supports_oauth_discovery.return_value = True

        middleware = ResourceServerMiddleware(
            app=Mock(),
            validator=validator,
            canonical_url="https://example.com/mcp",
        )

        response = middleware._create_401_response(
            error="invalid_token",
            error_description="Token expired",
        )
        www_auth = response.headers.get("WWW-Authenticate", "")
        assert 'scope=""' in www_auth
        assert "resource_metadata=" in www_auth
        assert 'error="invalid_token"' in www_auth
