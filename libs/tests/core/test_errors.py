"""Tests for arcade_core.errors.

Covers the empty-message guard in ``ToolkitError.with_context()`` — without it,
``raise FatalToolError("")`` produces prefixed text like ``"...tool 'foo': "``
that carries no diagnostic payload in logs/agent output.
"""

import pytest
from arcade_core.errors import FatalToolError, RetryableToolError, ToolkitLoadError


@pytest.mark.parametrize("empty_message", ["", " ", "\t", "\n  \n"])
def test_with_context_empty_message_substitutes_placeholder(empty_message):
    err = FatalToolError(empty_message).with_context("my_tool")
    # Prefix is preserved — kind, error type and tool name are still in the message.
    assert "[TOOL_RUNTIME_FATAL]" in err.message
    assert "my_tool" in err.message
    # And the empty body is replaced with a recognizable placeholder so the
    # message ends with diagnostic content rather than ``": "``.
    assert "(no details provided)" in err.message
    assert not err.message.endswith(": ")


def test_with_context_nonempty_message_unchanged():
    err = FatalToolError("Spreadsheet not found").with_context("get_sheet")
    assert err.message.endswith(": Spreadsheet not found")
    assert "(no details provided)" not in err.message


def test_with_context_developer_message_with_empty_message_still_works():
    # A non-empty developer_message is preserved alongside the placeholder body.
    err = FatalToolError("", developer_message="trace: foo.py:42").with_context("my_tool")
    assert "(no details provided)" in err.message
    assert err.developer_message is not None
    assert err.developer_message.endswith(": trace: foo.py:42")


def test_with_context_retryable_error_empty_message():
    err = RetryableToolError("   ").with_context("flaky_tool")
    assert "[TOOL_RUNTIME_RETRY]" in err.message
    assert "(no details provided)" in err.message


def test_with_context_toolkit_load_error_empty_message():
    err = ToolkitLoadError("").with_context("broken_toolkit")
    assert "broken_toolkit" in err.message
    assert "(no details provided)" in err.message
