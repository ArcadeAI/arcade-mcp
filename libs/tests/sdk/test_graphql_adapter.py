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
        """Should extract messages and map error codes to status."""
        errors = [
            {"message": "Not authorized", "extensions": {"code": "FORBIDDEN"}},
            {"message": "Server error", "extensions": {"code": "INTERNAL_SERVER_ERROR"}},
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR  # Highest mapped status
        assert "Not authorized" in result.message
        assert "Server error" in result.message
        assert result.extra["gql_error_codes"] == ["FORBIDDEN", "INTERNAL_SERVER_ERROR"]

    def test_query_error_defaults_when_empty(self) -> None:
        """Should handle empty/missing errors gracefully."""
        exc = DummyTransportQueryError(errors=None)

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "Unknown GraphQL error" in result.message

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

    # --- Status-code selection (secondary bug: TOO-1338) ---

    def test_query_error_single_not_found_maps_to_404(self) -> None:
        """A lone NOT_FOUND must win over the 422 default, not be masked by it."""
        exc = DummyTransportQueryError(
            errors=[{"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}}]
        )

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.NOT_FOUND
        assert "Entity not found" in result.message

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("UNAUTHENTICATED", HTTPStatus.UNAUTHORIZED),
            ("FORBIDDEN", HTTPStatus.FORBIDDEN),
            ("NOT_FOUND", HTTPStatus.NOT_FOUND),
            ("BAD_USER_INPUT", HTTPStatus.BAD_REQUEST),
        ],
    )
    def test_query_error_specific_4xx_codes_are_not_masked_by_422(
        self, code: str, expected: HTTPStatus
    ) -> None:
        """Every mapped 4xx code below the 422 floor must be reported as itself."""
        exc = DummyTransportQueryError(errors=[{"message": "boom", "extensions": {"code": code}}])

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == expected

    def test_query_error_unknown_code_still_defaults_to_422(self) -> None:
        """An unrecognized code carries no mapped status → 422 fallback stands."""
        exc = DummyTransportQueryError(
            errors=[{"message": "weird", "extensions": {"code": "SOMETHING_ELSE"}}]
        )

        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert result.extra["gql_error_codes"] == ["SOMETHING_ELSE"]


# --- Regression: graceful degradation across gql versions (TOO-1338) ---
#
# gql is not a test dependency, so these tests do not import a real gql. Instead
# they build a fake ``gql.transport.exceptions`` module holding only the
# exception classes a given gql version defines, and drive the *real* loader
# through it. This covers both the stable 3.5.x profile (no
# TransportConnectionFailed) and the 4.0.x profile (all present) deterministically
# and without installing multiple gql builds.


class _FakeTransportError(Exception):
    def __init__(self, message: str = "", code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class _FakeTransportQueryError(_FakeTransportError):
    def __init__(self, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__("query error")
        self.errors = errors


class _FakeTransportServerError(_FakeTransportError):
    pass


class _FakeTransportProtocolError(_FakeTransportError):
    pass


class _FakeTransportConnectionFailed(_FakeTransportError):
    pass


# Mirrors gql's real inventory per version. 3.5.x has no TransportConnectionFailed;
# 4.0.x adds it. Both keep TransportProtocolError (present on both lines).
_GQL_VERSION_PROFILES = {
    "3.5.x": {
        "TransportError": _FakeTransportError,
        "TransportQueryError": _FakeTransportQueryError,
        "TransportServerError": _FakeTransportServerError,
        "TransportProtocolError": _FakeTransportProtocolError,
    },
    "4.0.x": {
        "TransportError": _FakeTransportError,
        "TransportQueryError": _FakeTransportQueryError,
        "TransportServerError": _FakeTransportServerError,
        "TransportProtocolError": _FakeTransportProtocolError,
        "TransportConnectionFailed": _FakeTransportConnectionFailed,
    },
}


def _install_fake_gql(monkeypatch: pytest.MonkeyPatch, profile: str) -> None:
    """Point the real loader at a fake gql module for the given version profile."""
    from types import ModuleType

    fake_module = ModuleType("gql.transport.exceptions")
    for name, cls in _GQL_VERSION_PROFILES[profile].items():
        setattr(fake_module, name, cls)

    def fake_import(name: str) -> ModuleType:
        assert name == "gql.transport.exceptions"
        return fake_module

    monkeypatch.setattr(gql_adapter.importlib, "import_module", fake_import)
    gql_adapter._load_gql_transport_errors.cache_clear()


@pytest.mark.parametrize("profile", ["3.5.x", "4.0.x"])
def test_loader_degrades_when_transport_class_missing(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    """The loader must never raise AttributeError, even when a class is absent."""
    _install_fake_gql(monkeypatch, profile)

    types_tuple = gql_adapter._load_gql_transport_errors()

    assert types_tuple is not None
    assert len(types_tuple) == 5
    # TransportConnectionFailed (index 3) is the sentinel on 3.5.x, real on 4.0.x.
    if profile == "3.5.x":
        assert types_tuple[3] is gql_adapter._MissingGqlError
    else:
        assert types_tuple[3] is _FakeTransportConnectionFailed


@pytest.mark.parametrize("profile", ["3.5.x", "4.0.x"])
def test_query_error_maps_to_upstream_even_when_class_missing(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    """The core TOO-1338 regression: a TransportQueryError must map to an
    UpstreamError carrying the real message on gql 3.5.x, where
    TransportConnectionFailed is missing — not fall through to FatalToolError."""
    _install_fake_gql(monkeypatch, profile)

    exc = _FakeTransportQueryError(
        errors=[{"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}}]
    )
    result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

    assert isinstance(result, UpstreamError)
    assert result.status_code == HTTPStatus.NOT_FOUND
    assert result.message == "Upstream GraphQL error: Entity not found"


def test_protocol_error_still_maps_on_35x_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sentinel substituted for the missing TransportConnectionFailed must not
    swallow TransportProtocolError, which DOES exist on 3.5.x."""
    _install_fake_gql(monkeypatch, "3.5.x")

    result = gql_adapter.GraphQLErrorAdapter().from_exception(
        _FakeTransportProtocolError("Invalid response")
    )

    assert isinstance(result, NetworkTransportError)
    assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE


def test_missing_sentinel_never_matches_real_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 3.5.x a connection-style error unknown to the adapter must fall through
    (return None), NOT be misclassified by the sentinel standing in for the
    missing TransportConnectionFailed."""
    _install_fake_gql(monkeypatch, "3.5.x")

    # An arbitrary non-gql exception is not a TransportError subclass here.
    result = gql_adapter.GraphQLErrorAdapter().from_exception(RuntimeError("unrelated"))

    assert result is None
