"""Integration tests for ``LoguruInterceptHandler``.

Exercises the full stdlib-logging → handler → loguru → sink path with a real
loguru sink (no mocks). The contract under test:

* ``extra={"foo": "bar"}`` from a stdlib ``logger.warning`` call must reach
  the loguru sink as ``record["extra"]["foo"] == "bar"`` so downstream
  structured-log shippers (Datadog, ELK, etc.) can facet on it.
* Stdlib-internal LogRecord fields (``levelname``, ``pathname``, ``thread``,
  ``message``, ``asctime``, …) must NOT be forwarded — that would both
  clobber loguru's own keys and bloat the payload.
* Exception info must be preserved and rendered by loguru.
* The renderable message body (``record.getMessage()``) must reach the sink
  intact.
"""

from __future__ import annotations

import logging

import pytest
from arcade_mcp_server.logging_utils import LoguruInterceptHandler
from loguru import logger as loguru_logger


@pytest.fixture
def loguru_sink():
    """Capture every loguru record into a list and tear down at end."""
    captured: list[dict] = []

    def sink(message):  # message is loguru's "Message" wrapping a record dict
        captured.append(dict(message.record))

    sink_id = loguru_logger.add(sink, level="DEBUG", format="{message}")
    yield captured
    loguru_logger.remove(sink_id)


@pytest.fixture
def stdlib_logger_with_intercept():
    """A real stdlib logger wired through LoguruInterceptHandler — no mocks."""
    log = logging.getLogger("arcade_mcp_server.tests.intercept_integration")
    log.handlers.clear()
    log.addHandler(LoguruInterceptHandler())
    log.setLevel(logging.DEBUG)
    log.propagate = False
    yield log
    log.handlers.clear()


def test_extra_fields_reach_loguru_sink(stdlib_logger_with_intercept, loguru_sink):
    """The whole point of the handler: extras must survive the bridge."""
    stdlib_logger_with_intercept.warning(
        "tool failure",
        extra={
            "error_kind": "TOOL_RUNTIME_FATAL",
            "tool_name": "MyToolkit.MyTool",
            "error_status_code": 500,
        },
    )

    assert len(loguru_sink) == 1
    extra = loguru_sink[0]["extra"]
    assert extra["error_kind"] == "TOOL_RUNTIME_FATAL"
    assert extra["tool_name"] == "MyToolkit.MyTool"
    assert extra["error_status_code"] == 500


def test_stdlib_internal_fields_not_forwarded(stdlib_logger_with_intercept, loguru_sink):
    """``record.__dict__`` carries dozens of stdlib-internal attributes
    (``levelname``, ``pathname``, ``thread``, ``module``, …). Forwarding any
    of them via ``logger.bind`` would clobber loguru's own equivalents and
    pollute the structured payload."""
    stdlib_logger_with_intercept.warning("hello", extra={"my_extra": "kept"})

    assert len(loguru_sink) == 1
    extra = loguru_sink[0]["extra"]
    # The legitimate user-supplied extra survives.
    assert extra.get("my_extra") == "kept"
    # None of the stdlib internals leak into the bound extras.
    for forbidden in (
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "lineno",
        "funcName",
        "thread",
        "threadName",
        "processName",
        "process",
        "msg",
        "args",
        "exc_info",
        "exc_text",
        "stack_info",
        "created",
        "msecs",
        "relativeCreated",
        "name",
    ):
        assert forbidden not in extra, f"stdlib field {forbidden!r} leaked into loguru extra"


def test_message_body_preserved(stdlib_logger_with_intercept, loguru_sink):
    """``record.getMessage()`` (which performs ``%`` interpolation of args)
    must reach the sink — losing the renderable body would defeat the bridge."""
    stdlib_logger_with_intercept.warning("user %s did %s", "alice", "logout")

    assert loguru_sink[0]["message"] == "user alice did logout"


def test_exception_info_preserved(stdlib_logger_with_intercept, loguru_sink):
    """``exc_info`` from ``logger.exception(...)`` must propagate so loguru
    can render the traceback."""
    try:
        raise ValueError("a deliberately raised test exception")
    except ValueError:
        stdlib_logger_with_intercept.exception("handled exception in test")

    assert len(loguru_sink) == 1
    exc = loguru_sink[0]["exception"]
    assert exc is not None
    # ValueError is a builtin so loguru's exception record carries the type.
    assert exc.type is ValueError
    assert "deliberately raised" in str(exc.value)


def test_unknown_level_falls_back_to_numeric(stdlib_logger_with_intercept, loguru_sink):
    """A custom numeric level not registered with loguru must still be
    accepted (handler falls back to ``str(record.levelno)`` when
    ``logger.level(name)`` raises ValueError)."""
    custom_level_no = 42
    logging.addLevelName(custom_level_no, "CUSTOM_TEST_LEVEL")
    stdlib_logger_with_intercept.log(custom_level_no, "custom level emit")

    # The fallback path goes through ``logger.log(str(record.levelno), ...)``,
    # which loguru accepts as a numeric level. The record reaches the sink.
    assert any(r["message"] == "custom level emit" for r in loguru_sink)
