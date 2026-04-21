from __future__ import annotations

import sys
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from arcade_core.errors import (
    ErrorKind,
    NetworkTransportError,
    UpstreamError,
    UpstreamRateLimitError,
)

LIBS_DIR = Path(__file__).resolve().parents[2]
TDK_SRC = LIBS_DIR / "arcade-tdk"
if str(TDK_SRC) not in sys.path:
    sys.path.insert(0, str(TDK_SRC))

import arcade_tdk.providers.graphql.error_adapter as gql_adapter  # noqa: E402

# --- Dummy exception classes for testing ---


class DummyTransportError(Exception):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class DummyTransportQueryError(Exception):
    def __init__(self, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__("query error")
        self.errors = errors


class DummyResponse:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}


class DummyTransportServerError(Exception):
    def __init__(
        self, message: str, code: int | None = None, headers: dict[str, str] | None = None
    ):
        super().__init__(message)
        self.code = code
        if headers is not None:
            self.response = DummyResponse(headers)


class DummyTransportConnectionFailed(DummyTransportError):
    pass


class DummyTransportProtocolError(DummyTransportError):
    pass


@pytest.fixture(autouse=True)
def reset_cache() -> Iterator[None]:
    """Clear cached gql import state between tests."""
    gql_adapter._load_gql_transport_errors.cache_clear()
    yield
    gql_adapter._load_gql_transport_errors.cache_clear()


def _patch_loader() -> Any:
    """Patch the loader to return our dummy classes."""
    return patch.object(
        gql_adapter,
        "_load_gql_transport_errors",
        return_value=(
            DummyTransportError,
            DummyTransportQueryError,
            DummyTransportServerError,
            DummyTransportConnectionFailed,
            DummyTransportProtocolError,
        ),
    )


class TestGraphQLErrorAdapter:
    # --- Import/caching tests ---

    def test_skips_when_gql_not_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None and cache the import failure."""
        call_count = {"n": 0}

        def fake_import(name: str) -> None:
            call_count["n"] += 1
            raise ImportError("no gql")

        monkeypatch.setattr(gql_adapter.importlib, "import_module", fake_import)
        adapter = gql_adapter.GraphQLErrorAdapter()

        assert adapter.from_exception(Exception("x")) is None
        assert adapter.from_exception(Exception("y")) is None
        assert call_count["n"] == 1  # Only tried once

    def test_ignores_non_gql_exceptions(self) -> None:
        """Non-gql exceptions should return None."""
        with _patch_loader():
            adapter = gql_adapter.GraphQLErrorAdapter()
            assert adapter.from_exception(RuntimeError("not gql")) is None

    # --- TransportQueryError tests ---

    def test_query_error_extracts_messages_and_codes(self) -> None:
        """Maps codes to status; raw upstream messages live in developer_message."""
        errors = [
            {"message": "Not authorized", "extensions": {"code": "FORBIDDEN"}},
            {"message": "Server error", "extensions": {"code": "INTERNAL_SERVER_ERROR"}},
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR  # Highest mapped status
        # Agent-facing message is a safe template — no raw upstream text.
        assert result.message == "Upstream GraphQL request failed (Internal Server Error)."
        assert "Not authorized" not in result.message
        # Raw content is in developer_message for server-side logs.
        assert "Not authorized" in result.developer_message
        assert "Server error" in result.developer_message
        assert "FORBIDDEN" in result.developer_message
        assert "INTERNAL_SERVER_ERROR" in result.developer_message
        assert result.extra["gql_error_codes"] == ["FORBIDDEN", "INTERNAL_SERVER_ERROR"]

    def test_query_error_defaults_when_empty(self) -> None:
        """Should handle empty/missing errors gracefully with a safe template."""
        exc = DummyTransportQueryError(errors=None)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        # Safe template for agent; no leaked upstream text.
        # (The exact phrase for 422 varies by Python version — "Unprocessable
        # Entity" pre-3.13, "Unprocessable Content" from 3.13+.)
        assert result.message.startswith("Upstream GraphQL request failed (Unprocessable ")
        assert result.message.endswith(").")
        # Developer message still records the absence of details.
        assert "(no details)" in result.developer_message

    def test_query_error_deduplicates_codes(self) -> None:
        """Duplicate error codes should be deduplicated."""
        errors = [
            {"message": "A", "extensions": {"code": "FORBIDDEN"}},
            {"message": "B", "extensions": {"code": "FORBIDDEN"}},
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.extra["gql_error_codes"] == ["FORBIDDEN"]

    def test_query_error_preserves_paths(self) -> None:
        """GraphQL-spec ``path`` arrays should land in ``extra['gql_error_paths']``."""
        errors = [
            {
                "message": "bad",
                "path": ["issue", "creator", "email"],
                "extensions": {"code": "FORBIDDEN"},
            },
            {"message": "also bad", "path": ["viewer", "id"]},
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.extra["gql_error_paths"] == [
            ["issue", "creator", "email"],
            ["viewer", "id"],
        ]

    # --- Vendor-provided numeric status hints ---

    def test_query_error_prefers_extensions_http_status(self) -> None:
        """Apollo-convention ``extensions.http.status`` is authoritative."""
        errors = [
            {
                "message": 'Cannot query field "foo"',
                "extensions": {
                    "http": {"status": 400, "headers": {}},
                    "code": "GRAPHQL_VALIDATION_FAILED",
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream GraphQL request failed (Bad Request)."

    def test_query_error_prefers_extensions_status_code(self) -> None:
        """Linear-convention ``extensions.statusCode`` is authoritative."""
        errors = [
            {
                "message": "Authentication required",
                "extensions": {
                    "statusCode": 401,
                    "code": "AUTHENTICATION_ERROR",
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 401
        assert result.message == "Upstream GraphQL request failed (Unauthorized)."

    def test_numeric_hint_wins_over_code_lookup(self) -> None:
        """If numeric hint disagrees with the code map, numeric wins."""
        errors = [
            {
                "message": "teapot",
                "extensions": {
                    "statusCode": 418,
                    # code would normally resolve to 401
                    "code": "UNAUTHENTICATED",
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.status_code == 418

    def test_status_code_boolean_is_ignored(self) -> None:
        """``bool`` subclasses ``int``; don't treat ``True`` as status 1."""
        errors = [
            {
                "message": "x",
                "extensions": {
                    "statusCode": True,
                    "code": "FORBIDDEN",  # falls back to 403
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.status_code == 403

    # --- Rate-limit routing on 429 (numeric hint or code) ---

    def test_rate_limited_code_produces_rate_limit_error(self) -> None:
        """``code: RATE_LIMITED`` routes to ``UpstreamRateLimitError``."""
        errors = [{"message": "slow down", "extensions": {"code": "RATE_LIMITED"}}]
        exc = DummyTransportQueryError(errors=errors)
        cause = Exception("inner")
        cause.response = DummyResponse({"retry-after": "15"})  # type: ignore[attr-defined]
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 15_000

    def test_shopify_throttled_code_produces_rate_limit_error(self) -> None:
        """Shopify's ``THROTTLED`` spelling is also routed."""
        errors = [{"message": "throttled", "extensions": {"code": "THROTTLED"}}]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)

    def test_numeric_429_hint_produces_rate_limit_error(self) -> None:
        """A 429 numeric hint alone is enough — no matching code string needed."""
        errors = [{"message": "slow down", "extensions": {"statusCode": 429}}]
        exc = DummyTransportQueryError(errors=errors)
        cause = Exception("inner")
        cause.response = DummyResponse({"retry-after": "7"})  # type: ignore[attr-defined]
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 7_000

    def test_rate_limit_agent_message_includes_retry_hint(self) -> None:
        """Mirror the HTTP adapter's pattern: retry-after info in agent message."""
        errors = [{"message": "slow down", "extensions": {"code": "RATE_LIMITED"}}]
        exc = DummyTransportQueryError(errors=errors)
        cause = Exception("inner")
        cause.response = DummyResponse({"retry-after": "12"})  # type: ignore[attr-defined]
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.message == (
            "Upstream GraphQL request failed (Too Many Requests). Retry after 12 second(s)."
        )

    def test_rate_limit_agent_message_without_retry_after(self) -> None:
        """Without a retry header, fall back to a generic rate-limit phrase."""
        errors = [{"message": "x", "extensions": {"code": "RATE_LIMITED"}}]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        # _parse_retry_ms defaults to 1000ms when no rate-limit header is present,
        # which is 1 second — shown in the message.
        assert "Retry after 1 second(s)." in result.message

    # --- Curated agent-facing message ---

    def test_user_presentable_message_preferred(self) -> None:
        """``extensions.userPresentableMessage`` (Linear) wins over raw joined messages."""
        errors = [
            {
                "message": "Entity not found: Issue - Could not find referenced Issue.",
                "extensions": {
                    "statusCode": 400,
                    "code": "INPUT_ERROR",
                    "userPresentableMessage": "Could not find referenced Issue.",
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.message == "Could not find referenced Issue."

    def test_user_presentable_message_absent_uses_safe_template(self) -> None:
        """Without userPresentableMessage, agent sees a fixed template — no raw text."""
        errors = [{"message": "unauthorized", "extensions": {"code": "UNAUTHENTICATED"}}]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        # Agent sees fixed template, not raw upstream text.
        assert result.message == "Upstream GraphQL request failed (Unauthorized)."
        assert "unauthorized" not in result.message
        # Raw text lives in developer_message.
        assert "unauthorized" in result.developer_message
        assert "UNAUTHENTICATED" in result.developer_message

    # --- Real Linear payloads end-to-end (captured from live probe) ---

    def test_real_linear_authentication_error_payload(self) -> None:
        """Verbatim payload from live api.linear.app probe (bogus API key)."""
        errors = [
            {
                "message": "Authentication required, not authenticated",
                "extensions": {
                    "type": "authentication error",
                    "code": "AUTHENTICATION_ERROR",
                    "statusCode": 401,
                    "userError": True,
                    "userPresentableMessage": (
                        "You need to authenticate to access this operation."
                    ),
                    "meta": {},
                    "http": {"status": 401},
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 401
        # Curated user-safe text surfaces as agent message.
        assert result.message == "You need to authenticate to access this operation."
        # Raw upstream text + code in developer_message.
        assert "Authentication required" in result.developer_message
        assert "AUTHENTICATION_ERROR" in result.developer_message

    def test_real_linear_not_found_payload(self) -> None:
        """Verbatim payload from live probe (fake issue UUID)."""
        errors = [
            {
                "message": "Entity not found: Issue",
                "path": ["issue"],
                "locations": [{"line": 2, "column": 3}],
                "extensions": {
                    "type": "invalid input",
                    "code": "INPUT_ERROR",
                    "statusCode": 400,
                    "userError": True,
                    "userPresentableMessage": "Could not find referenced Issue.",
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.status_code == 400
        assert result.message == "Could not find referenced Issue."
        assert result.extra["gql_error_paths"] == [["issue"]]

    def test_real_linear_validation_error_payload(self) -> None:
        """Verbatim payload from live probe (unknown field). Uses ``http.status`` only."""
        errors = [
            {
                "message": 'Cannot query field "nonexistentFieldFoo" on type "User".',
                "locations": [{"line": 3, "column": 5}],
                "extensions": {
                    "http": {"status": 400, "headers": {}},
                    "code": "GRAPHQL_VALIDATION_FAILED",
                    "type": "graphql error",
                    "userError": True,
                },
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert result.status_code == 400
        # No userPresentableMessage in this payload → safe template for agent.
        assert result.message == "Upstream GraphQL request failed (Bad Request)."
        # Raw upstream text preserved for developers.
        assert 'nonexistentFieldFoo' in result.developer_message
        assert "GRAPHQL_VALIDATION_FAILED" in result.developer_message

    # --- TransportServerError tests ---

    def test_server_error_detects_rate_limit(self) -> None:
        """Should detect rate limits from status + headers."""
        exc = DummyTransportServerError(
            message="Too many requests",
            code=429,
            headers={"retry-after": "5"},
        )

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 5000

    def test_server_error_defaults_to_500(self) -> None:
        """Should default to 500 when no status code."""
        exc = DummyTransportServerError("Server error", code=None)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert result.message == "Upstream GraphQL request failed with status code 500."
        assert result.developer_message == "Server error"

    def test_server_error_extracts_headers_from_cause(self) -> None:
        """Should extract headers from __cause__ if not on exception."""
        exc = DummyTransportServerError("Error", code=429)
        # No headers on exc, but on __cause__
        cause = Exception("inner")
        cause.response = DummyResponse({"retry-after": "10"})  # type: ignore
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 10000

    def test_server_error_extracts_url_from_cause_aiohttp(self) -> None:
        """Should extract URL from __cause__ (aiohttp pattern)."""
        exc = DummyTransportServerError("Error", code=500)

        # aiohttp style: request_info.url
        class FakeRequestInfo:
            url = "https://api.github.com/graphql"
            method = "POST"

        cause = Exception("inner")
        cause.request_info = FakeRequestInfo()  # type: ignore
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.extra is not None
        assert result.extra.get("endpoint") == "https://api.github.com/graphql"
        assert result.extra.get("http_method") == "POST"

    def test_server_error_extracts_url_from_cause_httpx(self) -> None:
        """Should extract URL from __cause__ (httpx/requests pattern)."""
        exc = DummyTransportServerError("Error", code=500)

        # httpx style: response.request.url
        class FakeRequest:
            url = "https://api.stripe.com/graphql"
            method = "POST"

        class FakeResponse:
            request = FakeRequest()

        cause = Exception("inner")
        cause.response = FakeResponse()  # type: ignore
        exc.__cause__ = cause

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.extra is not None
        assert result.extra.get("endpoint") == "https://api.stripe.com/graphql"
        assert result.extra.get("http_method") == "POST"

    # --- Connection/Protocol error tests ---

    def test_connection_failed_maps_to_network_transport_unreachable(self) -> None:
        """Connection failures never reached upstream — NetworkTransportError."""
        exc = DummyTransportConnectionFailed("Connection refused")

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE
        assert result.can_retry is True
        assert result.status_code is None
        assert result.extra["error_type"] == "DummyTransportConnectionFailed"

    def test_protocol_error_maps_to_network_transport_unreachable(self) -> None:
        """Protocol errors (incomplete / malformed exchange) → NetworkTransportError."""
        exc = DummyTransportProtocolError("Invalid response")

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE
        assert result.can_retry is True
        assert result.status_code is None
        assert result.extra["error_type"] == "DummyTransportProtocolError"

    # --- Generic TransportError catch-all ---

    def test_generic_transport_error_handled(self) -> None:
        """Unknown TransportError subclasses should be caught."""
        exc = DummyTransportError("Unknown error", code=503)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.message == "Upstream GraphQL request failed with status code 503."
        assert result.developer_message == "Unknown error"

    # --- Edge cases ---

    def test_extract_message_handles_bad_str(self) -> None:
        """Should handle objects that fail str()."""

        class BadStr:
            def __str__(self) -> str:
                raise ValueError("nope")

        assert gql_adapter._extract_error_message(BadStr()) == "Unknown GraphQL error"

    def test_extract_message_handles_empty(self) -> None:
        """Should handle empty/None messages."""
        assert gql_adapter._extract_error_message(None) == "Unknown GraphQL error"
        assert gql_adapter._extract_error_message("") == "Unknown GraphQL error"
