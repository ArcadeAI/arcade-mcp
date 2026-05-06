"""Tests for the inline OAuth scope check in ``MCPServer._handle_call_tool``.

These tests pin the consolidation in Round 5: the inline JSON-RPC 403 path
and the ASGI middleware 403 path produce byte-identical headers via the
shared ``build_insufficient_scope_www_authenticate`` helper. They also
pin the fix to ``_resolve_resource_metadata_url``: the inline path now
correctly reads ``settings.resource_server.canonical_url`` instead of the
non-existent ``settings.server.canonical_url``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from arcade_mcp_server.resource_server import (
    InsufficientScopeError,
    ResourceOwner,
    build_insufficient_scope_www_authenticate,
)
from arcade_mcp_server.server import (
    INSUFFICIENT_SCOPE_ERROR_CODE,
    MCPServer,
)
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import JSONRPCError


@pytest_asyncio.fixture
async def initialized_session(
    mcp_server: MCPServer, mock_read_stream: AsyncMock, mock_write_stream: AsyncMock
) -> ServerSession:
    """Create a session negotiated at 2025-11-25, ready to dispatch tools/call."""
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


def _scoped_call_message(msg_id: int = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tools/call",
        "params": {
            "name": "TestToolkit.scoped_tool",
            "arguments": {"text": "hello"},
        },
    }


class TestInlineScopeCheckUsesGrantedScopes:
    """Pin: the inline JSON-RPC path reads ``ResourceOwner.granted_scopes``,
    NOT the legacy ``_extract_scopes(claims)`` path.

    Round 4 added the validator-time grammar filter so a malformed claim
    string never produces a survivor token. The inline path must consume
    the filtered field, not the unfiltered claim parser, so the
    middleware emit and the inline emit agree on the granted set.
    """

    @pytest.mark.asyncio
    async def test_inline_oauth_scope_check_uses_granted_scopes_field(
        self,
        mcp_server: MCPServer,
        initialized_session: ServerSession,
    ) -> None:
        # The malformed token in ``claims["scope"]`` is filtered out by
        # the Round 4 grammar filter at validator time. We simulate that
        # outcome by setting only the filtered token on ``granted_scopes``.
        # The inline path MUST treat granted as ``{"files:read"}`` only.
        resource_owner = ResourceOwner(
            user_id="alice",
            granted_scopes=frozenset({"files:read"}),
            claims={
                "scope": "files:read malformed\\token",
                "iss": "https://auth.example.com",
                "sub": "alice",
            },
        )

        response = await mcp_server.handle_message(
            _scoped_call_message(),
            session=initialized_session,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == INSUFFICIENT_SCOPE_ERROR_CODE
        # The malformed token is NOT in granted_scopes (Round 4 filter).
        # The inline path consumes ``granted_scopes`` directly, so the
        # data payload reflects the filtered set.
        assert response.error["data"]["granted_scopes"] == ["files:read"]

    @pytest.mark.asyncio
    async def test_inline_403_emits_resource_metadata_when_canonical_set_via_env(
        self,
        mcp_server: MCPServer,
        initialized_session: ServerSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Pin Codex Finding 1: the inline path now correctly reads from
        ``settings.resource_server.canonical_url``. Before the fix the path
        read ``settings.server.canonical_url`` (which does not exist),
        silently dropping ``resource_metadata`` from every inline 403.
        """
        # Set env var; reload the server's settings to pick it up.
        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com/mcp"
        )
        from arcade_mcp_server.settings import MCPSettings

        mcp_server.settings = MCPSettings.from_env()

        resource_owner = ResourceOwner(
            user_id="alice",
            granted_scopes=frozenset({"files:read"}),
        )

        response = await mcp_server.handle_message(
            _scoped_call_message(),
            session=initialized_session,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        www_auth = response.error["data"]["_transport"]["www_authenticate"]
        assert (
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
            in www_auth
        )

    @pytest.mark.asyncio
    async def test_inline_403_omits_resource_metadata_when_canonical_unset(
        self,
        mcp_server: MCPServer,
        initialized_session: ServerSession,
    ) -> None:
        """When neither init_options nor settings carry a canonical URL,
        the inline path gracefully omits ``resource_metadata=`` rather
        than emitting a corrupted parameter.
        """
        # Initialized session uses {"transport_type": "http"} (no canonical_url),
        # and the autouse fixture clears MCP_RESOURCE_SERVER_CANONICAL_URL.
        resource_owner = ResourceOwner(
            user_id="alice",
            granted_scopes=frozenset({"files:read"}),
        )

        response = await mcp_server.handle_message(
            _scoped_call_message(),
            session=initialized_session,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        www_auth = response.error["data"]["_transport"]["www_authenticate"]
        assert "resource_metadata=" not in www_auth


class TestInlineAndMiddlewareEmitIdenticalHeader:
    """Pin R15: the two emit sites produce byte-identical headers.

    The inline JSON-RPC path keeps the JSON-RPC framing (stdio transport
    has no ASGI middleware), but the ``WWW-Authenticate`` *string* itself
    must match the middleware-emitted version exactly. Both call
    ``build_insufficient_scope_www_authenticate`` with the same inputs.
    """

    @pytest.mark.asyncio
    async def test_inline_403_and_middleware_403_emit_identical_www_authenticate(
        self,
        mcp_server: MCPServer,
        initialized_session: ServerSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "MCP_RESOURCE_SERVER_CANONICAL_URL", "https://mcp.example.com/mcp"
        )
        from arcade_mcp_server.settings import MCPSettings

        mcp_server.settings = MCPSettings.from_env()

        resource_owner = ResourceOwner(
            user_id="alice",
            granted_scopes=frozenset({"files:read"}),
        )

        response = await mcp_server.handle_message(
            _scoped_call_message(),
            session=initialized_session,
            resource_owner=resource_owner,
        )

        assert isinstance(response, JSONRPCError)
        inline_www_auth = response.error["data"]["_transport"]["www_authenticate"]

        # Build the same header via the public helper.
        expected = build_insufficient_scope_www_authenticate(
            required_scopes=["files:read", "files:write"],
            resource_metadata_url=(
                "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
            ),
            error_description=None,
        )
        assert inline_www_auth == expected


class TestExtractScopesShim:
    """Pin: ``server._extract_scopes`` is retained as a thin shim, not
    removed. Any legacy importer keeps working; new code consumes
    ``ResourceOwner.granted_scopes`` directly.
    """

    def test_extract_scopes_function_still_importable(self) -> None:
        from arcade_mcp_server.server import _extract_scopes

        # Behaves like the legacy parser: parses scope claim into a set
        # without applying the Round 4 grammar filter.
        result = _extract_scopes({"scope": "read write"})
        assert result == {"read", "write"}
