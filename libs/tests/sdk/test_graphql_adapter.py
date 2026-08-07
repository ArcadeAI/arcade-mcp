from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
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


class DummyTransportQueryError(DummyTransportError):
    """Mirrors real gql, where `TransportQueryError` subclasses `TransportError`.

    Deriving this from `Exception` would let a broken branch order in
    `from_exception` pass every test in this file — see `TestGqlVersionTolerance
    .test_query_error_is_matched_before_the_transport_catch_all`.
    """

    def __init__(self, errors: list[dict[str, Any]] | None = None) -> None:
        # `.code` stays None: real query errors carry no HTTP status.
        super().__init__("query error")
        self.errors = errors


class DummyResponse:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}


class DummyTransportServerError(DummyTransportError):
    """Mirrors real gql, where `TransportServerError` subclasses `TransportError`."""

    def __init__(
        self, message: str, code: int | None = None, headers: dict[str, str] | None = None
    ):
        super().__init__(message, code)
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

    class TransportQueryError(TransportError):
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


@contextmanager
def _real_stdio_debug_logging() -> Iterator[None]:
    """Install the real `arcade mcp stdio --debug` logging stack, then fully undo it.

    `setup_logging` is doubly destructive to global state, and both halves are
    snapshotted here or logging breaks for every test that runs afterwards:

    * `logging.basicConfig(..., force=True)` wipes the stdlib root handlers,
      including pytest's.
    * `logger.remove()` drops every pre-existing Loguru sink. Loguru offers no
      public snapshot/restore, so the handler registry is saved and put back
      directly, together with `core.min_level` — it caches the minimum level
      across sinks and gates `emit`, so restoring handlers without it leaves the
      restored sinks present but silently dropping records.

    Crucially, the pre-existing handlers are **detached without being stopped**:
    `logger.remove` is swapped for `_detach` while `setup_logging` runs. Letting
    `remove()` stop them and reviving the objects afterwards is not sound, because
    `stop()` has side effects per sink type — `FileSink.stop()` closes the file
    and, when no rotation is configured, runs the **compression and retention**
    functions against the existing log. Never stopping them sidesteps every one of
    those side effects and works for all sink types, rather than only the callable
    and stream sinks that happen to have a no-op `stop()`.
    """
    pytest.importorskip(
        "arcade_mcp_server", reason="stdio logging stack lives in arcade-mcp-server"
    )
    from arcade_mcp_server.logging_utils import setup_logging
    from loguru import logger as loguru_logger

    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level

    core = loguru_logger._core  # type: ignore[attr-defined]
    saved_sinks = dict(core.handlers)
    saved_min_level = core.min_level

    def _detach(handler_id: int | None = None) -> None:
        """Unregister without calling `Handler.stop()` — see the docstring."""
        if handler_id is None:
            core.handlers.clear()
        else:
            core.handlers.pop(handler_id, None)
        core.min_level = float("inf")

    try:
        with patch.object(loguru_logger, "remove", _detach):
            setup_logging(level="DEBUG", stdio_mode=True)
        yield
    finally:
        # Only the sink setup_logging added is truly removed (and stopped).
        for handler_id in [i for i in core.handlers if i not in saved_sinks]:
            loguru_logger.remove(handler_id)
        core.handlers.update(saved_sinks)
        core.min_level = saved_min_level
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def _map_query_errors(errors: Any) -> UpstreamError:
    """Run a `TransportQueryError` payload through the adapter and return the mapping."""
    exc = DummyTransportQueryError(errors=errors)
    with _patch_loader():
        result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)
    assert isinstance(result, UpstreamError)
    return result


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

    @pytest.mark.parametrize("profile", GQL_VERSION_PROFILES)
    def test_query_error_is_matched_before_the_transport_catch_all(self, profile: str) -> None:
        """A query error is also a TransportError — the specific branch must win.

        In real gql every transport exception subclasses `TransportError`, so
        `from_exception`'s ordering is load-bearing: if the catch-all ran first, a
        query error would route to `_handle_transport_error`, which finds no
        `.code` and fabricates "status code 500" while dropping the GraphQL
        message — TOO-1338's symptom, reintroduced.
        """
        with _fake_gql_installed(profile) as module:
            exc = module.TransportQueryError(errors=[{"message": "Entity not found"}])
            # Guards the guard: if the fake stopped mirroring gql's hierarchy,
            # this test would silently stop testing anything.
            assert isinstance(exc, module.TransportError)
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.message == "Upstream GraphQL error: Entity not found"
        assert "status code 500" not in result.message

    @pytest.mark.parametrize("profile", GQL_VERSION_PROFILES)
    def test_server_error_keeps_its_status_and_stays_off_the_network_branch(
        self, profile: str
    ) -> None:
        """A server error carries a real HTTP status; the network branch would discard it.

        Completes the hierarchy fix for the server class. Note the server branch
        and the `TransportError` catch-all both delegate to
        `_handle_transport_error`, so their relative order is not observable —
        what IS observable, and what this pins, is that a server error never
        reaches the network branch, which returns `NetworkTransportError` with no
        status at all.
        """
        with _fake_gql_installed(profile) as module:
            exc = module.TransportServerError("Service Unavailable", code=503)
            assert isinstance(exc, module.TransportError)
            result = gql_adapter.GraphQLErrorAdapter().from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR


class TestUnresolvedClassDiagnostic:
    """A silently incomplete class inventory is how TOO-1338 stayed invisible."""

    def test_missing_class_is_named_at_debug_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The one diagnostic that says which branches got disabled."""
        with caplog.at_level(logging.DEBUG, logger=gql_adapter.__name__):
            with _fake_gql_installed(GQL_35X):
                gql_adapter._load_gql_transport_errors()

        records = [r for r in caplog.records if "TransportConnectionFailed" in r.getMessage()]
        assert records, "a missing gql class must be named in the logs"
        assert records[0].levelno == logging.DEBUG

    def test_no_diagnostic_when_every_class_resolves(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A complete inventory is the normal case and must stay quiet."""
        with caplog.at_level(logging.DEBUG, logger=gql_adapter.__name__):
            with _fake_gql_installed(GQL_40X):
                gql_adapter._load_gql_transport_errors()

        assert not [r for r in caplog.records if "does not define" in r.getMessage()]

    def test_diagnostic_leaves_the_stdio_jsonrpc_channel_clean(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """stdout carries JSON-RPC in stdio mode and must stay byte-clean.

        Drives the REAL supported configuration rather than the default test
        harness: `setup_logging(level="DEBUG", stdio_mode=True)` is what
        `arcade mcp stdio --debug` installs, and it is the only configuration
        under which this diagnostic is emitted at all.
        """
        with _real_stdio_debug_logging(), _fake_gql_installed(GQL_35X):
            gql_adapter._load_gql_transport_errors()

        assert capsys.readouterr().out == ""

    def test_diagnostic_goes_to_stderr_the_sanctioned_stdio_sink(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Pins WHICH stream the diagnostic uses, so a reroute to stdout fails here.

        `setup_logging` deliberately sinks to stderr in stdio mode — "stdout is
        reserved for JSON-RPC" (`logging_utils.py:104-105`). Asserting stderr is
        non-empty is not asserting pollution: it pins that the sanctioned channel
        is the one being used, and turns any future switch of that sink into a
        test failure instead of a corrupted protocol stream.
        """
        with _real_stdio_debug_logging(), _fake_gql_installed(GQL_35X):
            gql_adapter._load_gql_transport_errors()

        captured = capsys.readouterr()
        assert "TransportConnectionFailed" in captured.err
        assert captured.out == ""

    def test_module_never_writes_directly_to_either_stream(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With no logging configured at all, the loader must be silent — no bare print."""
        with _fake_gql_installed(GQL_35X):
            gql_adapter._load_gql_transport_errors()

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestStdioDebugLoggingHelper:
    """`_real_stdio_debug_logging` rips up global logging state; it must leave no trace.

    Test-infrastructure tests, but this helper reconfigures process-wide logging,
    so a leak here shows up as order-dependent flakiness somewhere unrelated.
    """

    def test_restores_a_preexisting_loguru_sink(self) -> None:
        """A sink configured before the helper must still receive logs afterwards."""
        pytest.importorskip("arcade_mcp_server", reason="stdio logging stack")
        from loguru import logger as loguru_logger

        received: list[str] = []
        sink_id = loguru_logger.add(received.append, level="DEBUG")
        try:
            with _real_stdio_debug_logging():
                pass
            loguru_logger.debug("after the helper exits")
        finally:
            with suppress(ValueError):  # absent if the restore failed
                loguru_logger.remove(sink_id)

        assert any("after the helper exits" in message for message in received)

    def test_restores_a_preexisting_file_sink(self, tmp_path: Path) -> None:
        """A file sink must keep writing, and keep what it had already written."""
        pytest.importorskip("arcade_mcp_server", reason="stdio logging stack")
        from loguru import logger as loguru_logger

        log_file = tmp_path / "preexisting.log"
        sink_id = loguru_logger.add(str(log_file), level="DEBUG", format="{message}")
        try:
            loguru_logger.debug("before the helper")
            with _real_stdio_debug_logging():
                pass
            loguru_logger.debug("after the helper exits")
        finally:
            with suppress(ValueError):
                loguru_logger.remove(sink_id)

        contents = log_file.read_text()
        assert "after the helper exits" in contents  # sink still live
        assert "before the helper" in contents  # and its history intact

    def test_preexisting_file_sink_is_not_compressed_or_rotated(self, tmp_path: Path) -> None:
        """`FileSink.stop()` runs compression/retention — the helper must not trigger it.

        This is the case that rules out reviving stopped handler objects. With
        `compression="gz"` configured, letting `logger.remove()` stop the sink
        gzips the live log out from under the caller; the file sink then reopens
        an empty file on the next write and the earlier records are gone from it.
        """
        pytest.importorskip("arcade_mcp_server", reason="stdio logging stack")
        from loguru import logger as loguru_logger

        log_file = tmp_path / "compressed.log"
        sink_id = loguru_logger.add(
            str(log_file), level="DEBUG", format="{message}", compression="gz"
        )
        try:
            loguru_logger.debug("before the helper")
            with _real_stdio_debug_logging():
                pass
            loguru_logger.debug("after the helper exits")

            # Asserted before cleanup on purpose: removing the sink ourselves
            # compresses it, which is correct loguru behaviour and would mask this.
            assert not list(tmp_path.glob("*.gz")), "the helper compressed a live log sink"
            contents = log_file.read_text()
            assert "before the helper" in contents
            assert "after the helper exits" in contents
        finally:
            with suppress(ValueError):
                loguru_logger.remove(sink_id)

    def test_restores_stdlib_root_handlers(self) -> None:
        """`setup_logging` calls basicConfig(force=True), which wipes pytest's handlers."""
        pytest.importorskip("arcade_mcp_server", reason="stdio logging stack")
        root = logging.getLogger()
        before = root.handlers[:]

        with _real_stdio_debug_logging():
            pass

        assert root.handlers == before


class TestQueryErrorStatusSelection:
    """422 is the no-recognized-code fallback, not a floor that masks specific 4xx codes."""

    @pytest.mark.parametrize(
        ("code", "expected_status", "expected_kind"),
        [
            ("UNAUTHENTICATED", 401, ErrorKind.UPSTREAM_RUNTIME_AUTH_ERROR),
            ("NOT_AUTHENTICATED", 401, ErrorKind.UPSTREAM_RUNTIME_AUTH_ERROR),
            ("FORBIDDEN", 403, ErrorKind.UPSTREAM_RUNTIME_AUTH_ERROR),
            ("ACCESS_DENIED", 403, ErrorKind.UPSTREAM_RUNTIME_AUTH_ERROR),
            ("NOT_FOUND", 404, ErrorKind.UPSTREAM_RUNTIME_NOT_FOUND),
            ("BAD_USER_INPUT", 400, ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST),
            ("GRAPHQL_VALIDATION_FAILED", 400, ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST),
            ("GRAPHQL_PARSE_FAILED", 400, ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST),
            ("INTERNAL_SERVER_ERROR", 500, ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR),
        ],
    )
    def test_lone_code_reports_its_own_status_and_kind(
        self, code: str, expected_status: int, expected_kind: ErrorKind
    ) -> None:
        """A single recognized code is reported as itself, including codes below 422.

        `kind` is pinned alongside `status_code` because it is wire-visible: it is
        serialized in `to_payload()` and prefixed onto the agent-facing message.
        Lifting the 422 floor deliberately upgrades it — an auth failure now reads
        AUTH_ERROR instead of the generic BAD_REQUEST the floor produced. That is
        the point of the change, so it gets asserted rather than left implicit.
        """
        result = _map_query_errors([{"message": "boom", "extensions": {"code": code}}])

        assert result.status_code == expected_status
        assert result.kind == expected_kind

    def test_unknown_code_falls_back_to_422(self) -> None:
        """No recognized code → the unprocessable-entity fallback, code still reported."""
        result = _map_query_errors([{"message": "boom", "extensions": {"code": "WEIRD"}}])

        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.extra["gql_error_codes"] == ["WEIRD"]

    def test_unmapped_code_does_not_drown_a_mapped_one(self) -> None:
        """A mapped 404 wins over an unrecognized sibling code, which is still reported."""
        result = _map_query_errors([
            {"message": "missing", "extensions": {"code": "NOT_FOUND"}},
            {"message": "huh", "extensions": {"code": "WEIRD"}},
        ])

        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.extra["gql_error_codes"] == ["NOT_FOUND", "WEIRD"]

    def test_highest_mapped_status_wins_across_errors(self) -> None:
        """Multi-code responses keep the existing highest-wins contract (5xx over 4xx)."""
        result = _map_query_errors([
            {"message": "denied", "extensions": {"code": "FORBIDDEN"}},
            {"message": "boom", "extensions": {"code": "INTERNAL_SERVER_ERROR"}},
        ])

        assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_two_mapped_4xx_codes_resolve_numerically(self) -> None:
        """Two mapped 4xx codes break the tie numerically — the higher status is reported.

        Highest-wins applies within 4xx too, so an auth + not-found response is
        labelled 404. This is the decided contract, not an accident: one ordering
        rule for every pair, no special case for auth codes. Auth deliberately
        does NOT out-rank other 4xx — that would force the question of whether it
        out-ranks 5xx as well, which would flip `can_retry` for a FORBIDDEN +
        INTERNAL_SERVER_ERROR response.

        The scalar `status_code`/`kind` picks one code, but no signal is
        discarded: both messages and both codes still reach the caller, which is
        what keeps the single-label choice cheap.
        """
        result = _map_query_errors([
            {"message": "Not authenticated", "extensions": {"code": "UNAUTHENTICATED"}},
            {"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}},
        ])

        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_NOT_FOUND
        assert "Not authenticated" in result.message
        assert "Entity not found" in result.message
        assert result.extra["gql_error_codes"] == ["NOT_FOUND", "UNAUTHENTICATED"]


class TestMalformedErrorsPayload:
    """A non-conforming `errors[]` must degrade, never crash the adapter.

    An exception escaping the adapter is swallowed by `tool.py`'s broad except,
    which disables the adapter and drops the real message — the exact TOO-1338
    fault class this change exists to remove.
    """

    def test_non_dict_error_element_surfaces_its_own_message(self) -> None:
        """A bare-string element must not raise AttributeError on `.get`."""
        result = _map_query_errors(["Entity not found"])

        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert result.extra["gql_error_codes"] == []

    def test_non_dict_element_alongside_a_well_formed_one(self) -> None:
        """A malformed element must not cost the well-formed element's code or message."""
        result = _map_query_errors([
            {"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}},
            "something went wrong",
        ])

        assert "Entity not found" in result.message
        assert "something went wrong" in result.message
        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.extra["gql_error_codes"] == ["NOT_FOUND"]

    def test_non_list_errors_payload_is_treated_as_one_error(self) -> None:
        """A non-list `errors` must not be iterated character by character."""
        result = _map_query_errors("Entity not found")

        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_tuple_of_error_dicts_is_not_collapsed(self) -> None:
        """A non-list *sequence* of well-formed errors must map like a list.

        Normalizing on `list` exactly regressed this: the tuple was wrapped and
        stringified, losing the code and the real message.
        """
        result = _map_query_errors((
            {"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}},
        ))

        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.status_code == HTTPStatus.NOT_FOUND
        assert result.extra["gql_error_codes"] == ["NOT_FOUND"]

    def test_single_error_dict_is_treated_as_one_error(self) -> None:
        """A bare dict is one error, not an iterable of its keys."""
        result = _map_query_errors({
            "message": "Entity not found",
            "extensions": {"code": "NOT_FOUND"},
        })

        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.status_code == HTTPStatus.NOT_FOUND

    def test_one_shot_iterable_is_not_exhausted_by_the_first_pass(self) -> None:
        """`errors_list` is walked twice — messages, then codes.

        A generator must be materialized first, or the second pass sees nothing
        and every error code is silently dropped.
        """
        errors = iter([{"message": "Entity not found", "extensions": {"code": "NOT_FOUND"}}])
        result = _map_query_errors(errors)

        assert result.message == "Upstream GraphQL error: Entity not found"
        assert result.extra["gql_error_codes"] == ["NOT_FOUND"]
        assert result.status_code == HTTPStatus.NOT_FOUND
