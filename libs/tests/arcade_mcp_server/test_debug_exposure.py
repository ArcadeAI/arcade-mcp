"""Tests for the MCP-only debug-exposure escape hatch.

The augmentation lives at the MCP boundary (``arcade_mcp_server/_debug_exposure.py``)
rather than in ``arcade-core`` because only MCP clients suffer from the
"message-only error rendering" problem that motivates these flags.
"""

import logging

import pytest
from arcade_mcp_server import _debug_exposure as debug_exposure
from arcade_mcp_server._debug_exposure import augment_error_message_for_debug

_LEAK_MAGIC = "yes-i-accept-leaking-internals-to-the-agent"
_ENV_DEV_MSG = "ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES"
_ENV_STACKTRACE = "ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES"


@pytest.fixture(autouse=True)
def _reset_leak_warn_state(monkeypatch):
    """Clear the per-process one-shot warning state so each test starts clean.

    Both flags emit loud warnings (rejection and activation) one-shot per flag.
    Without a reset, later tests would silently lose coverage of those branches
    because the module-level tracking sets are already populated from earlier
    tests.
    """
    monkeypatch.delenv(_ENV_DEV_MSG, raising=False)
    monkeypatch.delenv(_ENV_STACKTRACE, raising=False)
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()
    yield
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()


def test_no_leak_by_default():
    """With both flags unset, message must not be augmented."""
    out = augment_error_message_for_debug(
        "public error",
        developer_message="secret internals",
        stacktrace="Traceback...\n  line",
    )
    assert out == "public error"


@pytest.mark.parametrize("bad_value", ["true", "1", "yes", "on", "TRUE", "True"])
def test_rejects_boolean_activation(monkeypatch, caplog, bad_value):
    """Any truthy-looking value that isn't the magic string must be rejected."""
    monkeypatch.setenv(_ENV_DEV_MSG, bad_value)
    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        out = augment_error_message_for_debug(
            "public error", developer_message="secret internals", stacktrace=None
        )
    assert out == "public error"
    assert any(
        "set to a truthy value but not to the required" in rec.message for rec in caplog.records
    )


def test_rejects_random_non_magic_value(monkeypatch, caplog):
    """A non-boolean-looking value that isn't the magic string is silently off."""
    monkeypatch.setenv(_ENV_DEV_MSG, "debug-please")
    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        out = augment_error_message_for_debug(
            "public error", developer_message="secret internals", stacktrace=None
        )
    assert out == "public error"
    assert not any(
        "set to a truthy value but not to the required" in rec.message for rec in caplog.records
    )


def test_developer_message_flag_enabled(monkeypatch, caplog):
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        out = augment_error_message_for_debug(
            "public error", developer_message="secret internals", stacktrace="trace"
        )
    assert "public error" in out
    assert "[DEBUG] developer_message: secret internals" in out
    # Stacktrace flag is off → stacktrace must NOT be in the augmented text.
    assert "trace" not in out.replace("public error", "")
    assert any("is ENABLED" in rec.message for rec in caplog.records)


def test_stacktrace_flag_enabled(monkeypatch):
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    out = augment_error_message_for_debug(
        "public error",
        developer_message="secret internals",
        stacktrace="Traceback (most recent call last):\n  File ...",
    )
    assert "public error" in out
    assert "[DEBUG] stacktrace:" in out
    assert "File ..." in out
    # Developer-message flag off → dev message must NOT leak.
    assert "secret internals" not in out


def test_both_flags_enabled(monkeypatch):
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    out = augment_error_message_for_debug(
        "public error", developer_message="dev info", stacktrace="trace info"
    )
    assert "[DEBUG] developer_message: dev info" in out
    assert "[DEBUG] stacktrace:\ntrace info" in out


def test_flag_enabled_but_no_content_to_leak(monkeypatch):
    """Flag on but developer_message/stacktrace are None → message unchanged."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    out = augment_error_message_for_debug("public error", None, None)
    assert out == "public error"


def test_activation_warning_emitted_once_per_process(monkeypatch, caplog):
    """Second call with the flag on must NOT emit another activation warning."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        augment_error_message_for_debug("a", developer_message="dev", stacktrace=None)
        first_count = sum("is ENABLED" in r.message for r in caplog.records)
        augment_error_message_for_debug("b", developer_message="dev", stacktrace=None)
        second_count = sum("is ENABLED" in r.message for r in caplog.records)
    assert first_count == 1
    assert second_count == 1  # one-shot per process


def test_rejection_does_not_suppress_later_activation_warning(monkeypatch, caplog):
    """Regression: once a truthy-but-non-magic value has been rejected for a
    flag, correcting the value to the magic string within the same process
    must still emit the critical "ENABLED ... DO NOT USE IN PRODUCTION"
    warning. Previously both paths shared one state set, so the activation
    warning was silently swallowed in this scenario.
    """
    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        monkeypatch.setenv(_ENV_DEV_MSG, "true")
        out_rejected = augment_error_message_for_debug(
            "public error", developer_message="secret internals", stacktrace=None
        )
        assert "[DEBUG]" not in out_rejected
        rejection_count = sum(
            "set to a truthy value but not to the required" in r.message for r in caplog.records
        )
        assert rejection_count == 1

        monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
        out_activated = augment_error_message_for_debug(
            "public error", developer_message="secret internals", stacktrace=None
        )
        assert "[DEBUG] developer_message: secret internals" in out_activated
        activation_count = sum("is ENABLED" in r.message for r in caplog.records)
        assert activation_count == 1, (
            "activation warning must fire even after the rejection warning "
            "has already been emitted for the same flag in this process"
        )


def test_magic_value_ignores_surrounding_whitespace(monkeypatch):
    """Leading/trailing whitespace around the magic string still activates the flag."""
    monkeypatch.setenv(_ENV_DEV_MSG, f"  {_LEAK_MAGIC}  ")
    out = augment_error_message_for_debug(
        "public error", developer_message="secret internals", stacktrace=None
    )
    assert "[DEBUG] developer_message: secret internals" in out
