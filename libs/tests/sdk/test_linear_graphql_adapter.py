from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from arcade_core.errors import UpstreamError, UpstreamRateLimitError

LIBS_DIR = Path(__file__).resolve().parents[2]
TDK_SRC = LIBS_DIR / "arcade-tdk"
if str(TDK_SRC) not in sys.path:
    sys.path.insert(0, str(TDK_SRC))

import arcade_tdk.providers.graphql.error_adapter as gql_adapter  # noqa: E402
from arcade_tdk.auth import Linear  # noqa: E402
from arcade_tdk.error_adapters.utils import get_adapter_for_auth_provider  # noqa: E402
from arcade_tdk.providers.linear import LinearGraphQLAdapter  # noqa: E402


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
    gql_adapter._load_gql_transport_errors.cache_clear()
    yield
    gql_adapter._load_gql_transport_errors.cache_clear()


def _patch_loader() -> Any:
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


def _invoke(errors: list[dict[str, Any]] | None) -> Any:
    exc = DummyTransportQueryError(errors=errors)
    with _patch_loader():
        return LinearGraphQLAdapter().from_exception(exc)


class TestLinearGraphQLAdapter:
    # --- Wire-format extensions.type lookups ---

    def test_feature_not_accessible_maps_to_403(self) -> None:
        """The original bug: 'feature not accessible' should surface as 403."""
        result = _invoke([
            {
                "message": "access denied to field email",
                "path": ["issue", "creator", "email"],
                "extensions": {"type": "feature not accessible"},
            }
        ])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 403
        assert result.extra is not None
        assert result.extra["service"] == "_linear_graphql"
        assert result.extra["linear_error_types"] == ["feature not accessible"]

    def test_authentication_error_maps_to_401(self) -> None:
        result = _invoke([{"message": "bad token", "extensions": {"type": "authentication error"}}])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 401

    def test_invalid_input_maps_to_400(self) -> None:
        result = _invoke([{"message": "bad input", "extensions": {"type": "invalid input"}}])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 400

    def test_lock_timeout_maps_to_503(self) -> None:
        result = _invoke([{"message": "timed out", "extensions": {"type": "lock timeout"}}])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 503

    # --- Rate limit handling ---

    def test_ratelimited_type_produces_rate_limit_error_with_retry_after(self) -> None:
        """Wire 'ratelimited' type plus retry-after on __cause__.response.headers."""
        exc = DummyTransportQueryError(
            errors=[
                {
                    "message": "Too many requests",
                    "extensions": {"type": "ratelimited"},
                }
            ]
        )
        cause = Exception("inner")
        cause.response = DummyResponse({"retry-after": "30"})  # type: ignore[attr-defined]
        exc.__cause__ = cause

        with _patch_loader():
            result = LinearGraphQLAdapter().from_exception(exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30000
        assert result.extra is not None
        assert result.extra["linear_error_types"] == ["ratelimited"]

    def test_ratelimited_code_fallback_produces_rate_limit_error(self) -> None:
        """When 'type' is missing, 'RATELIMITED' code should still trigger rate limiting."""
        result = _invoke([
            {
                "message": "Too many requests",
                "extensions": {"code": "RATELIMITED"},
            }
        ])
        assert isinstance(result, UpstreamRateLimitError)
        # No retry-after header provided → default 1000 ms from base mapper.
        assert result.retry_after_ms == 1000
        assert result.extra is not None
        assert result.extra["gql_error_codes"] == ["RATELIMITED"]

    # --- userPresentableMessage preference ---

    def test_user_presentable_message_becomes_agent_message(self) -> None:
        """Curated user-safe text lands in the agent-facing ``message``."""
        result = _invoke([
            {
                "message": "raw internal detail — may include PII",
                "extensions": {
                    "type": "user error",
                    "userPresentableMessage": "You can't do that.",
                },
            }
        ])
        assert isinstance(result, UpstreamError)
        assert result.message == "You can't do that."
        # Raw upstream message should NOT appear in agent-facing message.
        assert "raw internal detail" not in result.message

    def test_absent_user_presentable_message_uses_safe_template(self) -> None:
        result = _invoke([
            {
                "message": "raw internal detail — may include PII",
                "extensions": {"type": "feature not accessible"},
            }
        ])
        assert isinstance(result, UpstreamError)
        assert "Upstream Linear GraphQL error" in result.message
        assert "403" in result.message
        assert "raw internal detail" not in result.message

    # --- path preservation ---

    def test_path_preserved_in_extra(self) -> None:
        result = _invoke([
            {
                "message": "fail",
                "path": ["issue", "creator", "email"],
                "extensions": {"type": "feature not accessible"},
            }
        ])
        assert result.extra is not None
        assert result.extra["gql_error_paths"] == [["issue", "creator", "email"]]

    # --- Unknown type falls through to base default ---

    def test_unknown_type_falls_back_to_default_status(self) -> None:
        """An unrecognized ``extensions.type`` should fall back to the base default (422)."""
        result = _invoke([
            {"message": "mystery", "extensions": {"type": "some unknown phrase"}}
        ])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 422

    # --- Developer message JSON ---

    def test_developer_message_contains_json_of_first_error(self) -> None:
        errors = [
            {
                "message": "boom",
                "path": ["issue", "creator", "email"],
                "locations": [{"line": 1, "column": 5}],
                "extensions": {"type": "feature not accessible", "code": "FEATURE_NOT_ACCESSIBLE"},
            }
        ]
        result = _invoke(errors)
        assert result.developer_message is not None
        parsed = json.loads(result.developer_message)
        assert parsed["message"] == "boom"
        assert parsed["path"] == ["issue", "creator", "email"]
        assert parsed["extensions"]["type"] == "feature not accessible"

    # --- Highest status wins across multiple errors ---

    def test_highest_status_wins_across_multiple_errors(self) -> None:
        result = _invoke([
            {"message": "a", "extensions": {"type": "invalid input"}},  # 400
            {"message": "b", "extensions": {"type": "lock timeout"}},  # 503
        ])
        assert isinstance(result, UpstreamError)
        assert result.status_code == 503


class TestAuthRouting:
    def test_linear_auth_maps_to_linear_graphql_adapter(self) -> None:
        adapter = get_adapter_for_auth_provider(Linear(scopes=["read"]))
        assert isinstance(adapter, LinearGraphQLAdapter)
