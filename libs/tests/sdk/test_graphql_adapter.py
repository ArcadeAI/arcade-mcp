from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path
from types import ModuleType
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


# --- Fake `gql.transport.exceptions` modules, one per gql version profile ---
#
# These drive the REAL `_load_gql_transport_errors()` (unlike `_patch_loader`
# below, which bypasses it). gql 3.5.x does not define `TransportConnectionFailed`;
# gql 4.0.x does. That single missing attribute is TOO-1338.

GQL_35X = "gql-3.5.x"
GQL_40X = "gql-4.0.x"
GQL_VERSION_PROFILES = [GQL_35X, GQL_40X]


def _make_fake_gql_module(profile: str) -> ModuleType:
    """Build a stand-in `gql.transport.exceptions` with one version's class inventory."""

    class TransportError(Exception):
        pass

    class TransportProtocolError(TransportError):
        pass

    class TransportServerError(TransportError):
        def __init__(self, message: str, code: int | None = None) -> None:
            super().__init__(message)
            self.code = code

    class TransportQueryError(Exception):
        def __init__(
            self, msg: str = "GraphQL error", errors: list[dict[str, Any]] | None = None
        ) -> None:
            super().__init__(msg)
            self.errors = errors

    class TransportConnectionFailed(TransportError):
        pass

    module = ModuleType("gql.transport.exceptions")
    module.TransportError = TransportError  # type: ignore[attr-defined]
    module.TransportProtocolError = TransportProtocolError  # type: ignore[attr-defined]
    module.TransportServerError = TransportServerError  # type: ignore[attr-defined]
    module.TransportQueryError = TransportQueryError  # type: ignore[attr-defined]
    if profile == GQL_40X:
        module.TransportConnectionFailed = TransportConnectionFailed  # type: ignore[attr-defined]
    return module


@contextmanager
def _fake_gql_installed(profile: str) -> Iterator[ModuleType]:
    """Make the adapter's lazy import resolve to a fake gql of the given version."""
    module = _make_fake_gql_module(profile)
    real_import_module = importlib.import_module

    def fake_import(name: str) -> ModuleType:
        if name == "gql.transport.exceptions":
            return module
        return real_import_module(name)

    with patch.object(gql_adapter.importlib, "import_module", fake_import):
        yield module


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


class TestGqlVersionTolerance:
    """The loader must survive a gql version that omits a transport exception class.

    These drive the real `_load_gql_transport_errors()` against fake gql modules —
    using `_patch_loader()` here would bypass the code under test entirely.
    """

    @pytest.mark.parametrize("profile", GQL_VERSION_PROFILES)
    def test_loader_returns_five_classes_on_every_version(self, profile: str) -> None:
        """A missing class degrades to the sentinel instead of raising AttributeError."""
        with _fake_gql_installed(profile) as module:
            loaded = gql_adapter._load_gql_transport_errors()

        assert loaded is not None
        assert len(loaded) == 5
        connection_failed = loaded[3]

        if profile == GQL_35X:
            assert connection_failed is gql_adapter._MissingGqlError
        else:
            assert connection_failed is module.TransportConnectionFailed

        # Every class the installed gql *does* define still maps.
        assert loaded[0] is module.TransportError
        assert loaded[1] is module.TransportQueryError
        assert loaded[2] is module.TransportServerError
        assert loaded[4] is module.TransportProtocolError

    @pytest.mark.parametrize("profile", GQL_VERSION_PROFILES)
    def test_query_error_keeps_real_message_on_every_version(self, profile: str) -> None:
        """TOO-1338: the GraphQL message must reach the caller, not be swallowed."""
        with _fake_gql_installed(profile) as module:
            exc = module.TransportQueryError(
                errors=[{"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}}]
            )
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.developer_message == "GraphQL error codes: NOT_FOUND"

    def test_present_classes_still_map_when_a_sibling_is_missing(self) -> None:
        """One missing class must not disable the branches around it."""
        with _fake_gql_installed(GQL_35X) as module:
            exc = module.TransportProtocolError("Invalid response")
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE

    def test_sentinel_never_matches_a_real_exception(self) -> None:
        """The placeholder standing in for a missing class must not catch anything."""
        with _fake_gql_installed(GQL_35X):
            result = gql_adapter.GraphQLErrorAdapter().from_exception(RuntimeError("not gql"))

        assert result is None


class TestQueryErrorStatusSelection:
    """422 is the no-recognized-code fallback, not a floor that masks specific 4xx codes."""

    @staticmethod
    def _map(errors: list[dict[str, Any]]) -> UpstreamError:
        exc = DummyTransportQueryError(errors=errors)
        with _patch_loader():
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)
        assert isinstance(result, UpstreamError)
        return result

    @pytest.mark.parametrize(
        ("code", "expected_status"),
        [
            ("UNAUTHENTICATED", 401),
            ("NOT_AUTHENTICATED", 401),
            ("FORBIDDEN", 403),
            ("ACCESS_DENIED", 403),
            ("NOT_FOUND", 404),
            ("BAD_USER_INPUT", 400),
            ("GRAPHQL_VALIDATION_FAILED", 400),
            ("GRAPHQL_PARSE_FAILED", 400),
            ("INTERNAL_SERVER_ERROR", 500),
        ],
    )
    def test_lone_code_reports_its_own_status(self, code: str, expected_status: int) -> None:
        """A single recognized code is reported as itself, including codes below 422."""
        result = self._map([{"message": "boom", "extensions": {"code": code}}])

        assert result.status_code == expected_status

    def test_unknown_code_falls_back_to_422(self) -> None:
        """No recognized code → the unprocessable-entity fallback, code still reported."""
        result = self._map([{"message": "boom", "extensions": {"code": "WEIRD"}}])

        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert result.extra["gql_error_codes"] == ["WEIRD"]

    def test_unmapped_code_does_not_drown_a_mapped_one(self) -> None:
        """A mapped 404 wins over an unrecognized sibling code, which is still reported."""
        result = self._map([
            {"message": "missing", "extensions": {"code": "NOT_FOUND"}},
            {"message": "huh", "extensions": {"code": "WEIRD"}},
        ])

        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.extra["gql_error_codes"] == ["NOT_FOUND", "WEIRD"]

    def test_highest_mapped_status_wins_across_errors(self) -> None:
        """Multi-code responses keep the existing highest-wins contract (5xx over 4xx)."""
        result = self._map([
            {"message": "denied", "extensions": {"code": "FORBIDDEN"}},
            {"message": "boom", "extensions": {"code": "INTERNAL_SERVER_ERROR"}},
        ])

        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
