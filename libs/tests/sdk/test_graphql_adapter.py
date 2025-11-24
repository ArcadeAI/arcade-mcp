from __future__ import annotations

import sys
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from arcade_core.errors import UpstreamError, UpstreamRateLimitError

LIBS_DIR = Path(__file__).resolve().parents[2]
TDK_SRC = LIBS_DIR / "arcade-tdk"
if str(TDK_SRC) not in sys.path:
    sys.path.insert(0, str(TDK_SRC))

import arcade_tdk.providers.graphql.error_adapter as gql_error_adapter  # noqa: E402


class DummyTransportQueryError(Exception):
    """Minimal stand-in for gql.transport.exceptions.TransportQueryError."""

    def __init__(self, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__("query error")
        self.errors = errors


class DummyResponse:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}


class DummyTransportServerError(Exception):
    """Minimal stand-in for gql.transport.exceptions.TransportServerError."""

    def __init__(
        self, message: str, code: int | None = None, headers: dict[str, str] | None = None
    ):
        super().__init__(message)
        self.code = code
        if headers is not None:
            self.response = DummyResponse(headers)


@pytest.fixture(autouse=True)
def reset_gql_cache() -> Iterator[None]:
    """Ensure cached gql import state does not leak between tests."""
    gql_error_adapter._load_gql_transport_errors.cache_clear()
    yield
    gql_error_adapter._load_gql_transport_errors.cache_clear()


def _patch_gql_loader() -> Any:
    """Helper to patch the cached loader with dummy gql transport classes."""
    return patch.object(
        gql_error_adapter,
        "_load_gql_transport_errors",
        return_value=(DummyTransportQueryError, DummyTransportServerError),
    )


class TestGraphQLErrorAdapter:
    def test_adapter_skips_when_gql_missing_and_import_is_cached(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Import attempts should happen once even across multiple failures."""

        import_calls = {"count": 0}

        def fake_import(module_name: str) -> None:
            import_calls["count"] += 1
            raise ImportError("gql not installed")

        monkeypatch.setattr(gql_error_adapter.importlib, "import_module", fake_import)
        adapter = gql_error_adapter.GraphQLErrorAdapter()

        assert adapter.from_exception(Exception("boom")) is None
        assert adapter.from_exception(Exception("boom again")) is None
        assert import_calls["count"] == 1

    def test_query_error_maps_status_and_sanitizes_payload(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()
        errors = [
            {
                "message": "  multi-line   message\nwith secrets  ",
                "extensions": {"code": "FORBIDDEN"},
            },
            {
                "message": "Another issue",
                "extensions": {"code": "GRAPHQL_PARSE_FAILED"},
            },
        ]
        exc = DummyTransportQueryError(errors=errors)

        with _patch_gql_loader():
            result = adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.FORBIDDEN
        assert result.message.startswith(
            "Upstream GraphQL error:   multi-line   message\nwith secrets  ;"
        )
        assert result.message.endswith("Another issue")
        assert result.extra is not None
        assert result.developer_message == "GraphQL error codes: FORBIDDEN, GRAPHQL_PARSE_FAILED"
        assert result.extra["gql_error_count"] == 2
        assert result.extra["gql_error_codes"] == ["FORBIDDEN", "GRAPHQL_PARSE_FAILED"]

    def test_query_error_defaults_when_payload_is_missing(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()
        exc = DummyTransportQueryError(errors=None)

        with _patch_gql_loader():
            result = adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert result.message == "Upstream GraphQL error: Unknown GraphQL error"
        assert result.developer_message == "GraphQL error"
        assert result.extra is not None
        assert result.extra["gql_error_count"] == 0
        assert result.extra["gql_error_codes"] == []

    def test_transport_server_error_maps_rate_limits(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()
        exc = DummyTransportServerError(
            message="Too many requests\nplease slow down",
            code=HTTPStatus.TOO_MANY_REQUESTS,
            headers={"Retry-After": "7"},
        )

        with _patch_gql_loader():
            result = adapter.from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 7_000
        assert (
            result.message
            == "Upstream GraphQL transport error: Too many requests\nplease slow down"
        )
        assert result.extra is not None
        assert result.extra["service"] == "_graphql"

    def test_unknown_exception_is_ignored_even_when_gql_present(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()

        with _patch_gql_loader():
            assert adapter.from_exception(RuntimeError("not gql")) is None

    def test_returns_none_when_loader_missing_even_for_transport_error(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()

        with patch.object(gql_error_adapter, "_load_gql_transport_errors", return_value=None):
            assert adapter.from_exception(DummyTransportQueryError(errors=[])) is None

    def test_query_error_handles_missing_messages_and_extensions(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()
        errors: list[dict[str, Any]] = [
            {"extensions": {"code": "NOT_FOUND"}},
            {"message": None, "extensions": {}},
            {"message": object()},
        ]

        with _patch_gql_loader():
            result = adapter.from_exception(DummyTransportQueryError(errors))

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.NOT_FOUND
        assert "Unknown GraphQL error" in result.message
        assert result.extra is not None
        assert result.extra["gql_error_count"] == 3
        assert result.extra["gql_error_codes"] == ["NOT_FOUND"]

    def test_transport_server_error_without_status_defaults_to_500(self) -> None:
        adapter = gql_error_adapter.GraphQLErrorAdapter()
        exc = DummyTransportServerError("Server exploded", code=None, headers=None)

        with _patch_gql_loader():
            result = adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert result.message == "Upstream GraphQL transport error: Server exploded"
