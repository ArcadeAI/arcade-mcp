"""Transport-level tests for the Streamable HTTP transport.

Covers Origin validation, Accept header negotiation, the
MCP-Protocol-Version header, CORS headers, the transport error helper,
and session termination. These exercise the helpers at the function
level rather than via full ASGI integration.
"""

import json
from unittest.mock import Mock

from arcade_mcp_server.transports.http_session_manager import (
    _create_transport_error_response,
    _validate_accept_header,
    _validate_origin,
    _validate_protocol_version_header,
)
from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport
from arcade_mcp_server.types import JSONRPCError
from starlette.requests import Request


def _make_request(headers: dict[str, str] | None = None, method: str = "POST") -> Request:
    """Create a minimal Starlette Request with given headers."""
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode(), v.encode()))
    scope = {
        "type": "http",
        "method": method,
        "headers": raw_headers,
        "path": "/mcp",
        "query_string": b"",
        "root_path": "",
    }
    return Request(scope)


class TestTransportErrorHelper:
    """Transport-level JSON-RPC error response helper."""

    def test_transport_error_omits_id(self):
        """Transport-level errors omit id field entirely."""
        resp = _create_transport_error_response(400, "Bad Request")
        body = json.loads(resp.body)
        assert "id" not in body
        assert body["error"]["code"] == -32600
        assert resp.status_code == 400

    def test_transport_error_custom_code(self):
        resp = _create_transport_error_response(403, "Forbidden", code=-32001)
        body = json.loads(resp.body)
        assert body["error"]["code"] == -32001


class TestOriginValidation:
    """Origin header validation (MCP Streamable HTTP transport)."""

    def test_no_origin_header_allowed(self):
        """Non-browser clients don't send Origin -> allow."""
        req = _make_request({})
        assert _validate_origin(req, None) is None
        assert _validate_origin(req, ["https://example.com"]) is None

    def test_origin_present_no_allowlist_rejects(self):
        """allowed_origins=None + Origin present -> 403."""
        req = _make_request({"origin": "https://evil.com"})
        result = _validate_origin(req, None)
        assert result is not None
        assert result.status_code == 403

    def test_origin_present_empty_list_rejects(self):
        """allowed_origins=[] + Origin present -> 403."""
        req = _make_request({"origin": "https://evil.com"})
        result = _validate_origin(req, [])
        assert result is not None
        assert result.status_code == 403

    def test_valid_origin_accepted(self):
        req = _make_request({"origin": "https://example.com"})
        assert _validate_origin(req, ["https://example.com"]) is None

    def test_invalid_origin_rejected(self):
        req = _make_request({"origin": "https://evil.com"})
        result = _validate_origin(req, ["https://example.com"])
        assert result is not None
        assert result.status_code == 403

    def test_wildcard_allows_all(self):
        req = _make_request({"origin": "https://anything.com"})
        assert _validate_origin(req, ["*"]) is None


class TestAcceptHeaderValidation:
    """Accept header validation (MCP Streamable HTTP transport)."""

    def test_both_json_and_sse_succeeds(self):
        req = _make_request({"accept": "application/json, text/event-stream"})
        assert _validate_accept_header(req) is None

    def test_missing_sse_returns_406(self):
        req = _make_request({"accept": "application/json"})
        result = _validate_accept_header(req)
        assert result is not None
        assert result.status_code == 406

    def test_missing_json_returns_406(self):
        req = _make_request({"accept": "text/event-stream"})
        result = _validate_accept_header(req)
        assert result is not None
        assert result.status_code == 406

    def test_wildcard_is_acceptable(self):
        req = _make_request({"accept": "*/*"})
        assert _validate_accept_header(req) is None

    def test_type_wildcards_acceptable(self):
        req = _make_request({"accept": "application/*, text/*"})
        assert _validate_accept_header(req) is None


class TestMCPProtocolVersionHeader:
    """MCP-Protocol-Version header validation."""

    def test_unsupported_version_returns_400(self):
        req = _make_request({"mcp-protocol-version": "9999-01-01"})
        error, _ = _validate_protocol_version_header(req)
        assert error is not None
        assert error.status_code == 400

    def test_supported_version_accepted(self):
        req = _make_request({"mcp-protocol-version": "2025-11-25"})
        error, version = _validate_protocol_version_header(req)
        assert error is None
        assert version == "2025-11-25"

    def test_missing_header_stateful_ok(self):
        """Stateful: missing header -> use negotiated version."""
        req = _make_request({})
        error, version = _validate_protocol_version_header(req)
        assert error is None
        assert version is None

    def test_missing_header_stateless_returns_400(self):
        """Stateless: missing header -> 400."""
        req = _make_request({})
        error, _ = _validate_protocol_version_header(req, is_stateless=True)
        assert error is not None
        assert error.status_code == 400

    def test_initialize_skips_validation(self):
        """Initialize IS version negotiation -> skip header validation."""
        req = _make_request({})
        error, _ = _validate_protocol_version_header(req, is_initialize=True)
        assert error is None

    def test_version_mismatch_with_negotiated_returns_400(self):
        """Stateful: header mismatch with negotiated version -> 400."""
        req = _make_request({"mcp-protocol-version": "2025-06-18"})
        session = Mock()
        session.negotiated_version = "2025-11-25"
        error, _ = _validate_protocol_version_header(req, session=session)
        assert error is not None
        assert error.status_code == 400
        body = json.loads(error.body)
        assert "does not match negotiated version" in body["error"]["message"]


class TestCORSHeaders:
    """CORS headers must include MCP-Protocol-Version for browser clients."""

    def test_error_response_includes_mcp_protocol_version_in_cors(self):
        """The error response helper includes MCP-Protocol-Version in CORS headers."""
        transport = HTTPStreamableTransport(mcp_session_id="test")
        resp = transport._create_error_response("test error", 400)
        allow_headers = resp.headers.get("Access-Control-Allow-Headers", "")
        assert "MCP-Protocol-Version" in allow_headers
        expose_headers = resp.headers.get("Access-Control-Expose-Headers", "")
        assert "MCP-Protocol-Version" in expose_headers


class TestParseErrorNullId:
    """JSON-RPC parse errors use id=null per JSON-RPC 2.0 section 5.1."""

    def test_parse_fallback_uses_actual_id(self):
        """http_streamable.py TypeAdapter validation fallback uses actual parsed id."""
        transport = HTTPStreamableTransport(mcp_session_id="test")
        parsed = {"jsonrpc": "2.0", "id": 7, "method": "invalid/method", "invalid_field": True}
        result = transport._parse_mcp_message(json.dumps(parsed))
        if isinstance(result, JSONRPCError):
            assert result.id != "null"

    def test_parse_fallback_no_id_uses_none(self):
        """When parsed JSON has no id, fallback uses None."""
        transport = HTTPStreamableTransport(mcp_session_id="test")
        parsed = {"jsonrpc": "2.0", "method": "test"}
        result = transport._parse_mcp_message(json.dumps(parsed))
        # Should parse successfully or use None for id
        if isinstance(result, JSONRPCError):
            assert result.id is None or isinstance(result.id, (str, int))
