"""Tests for arcade_core.errors.

Covers the empty-message guard in ``ToolkitError.with_context()`` — without it,
``raise FatalToolError("")`` produces prefixed text like ``"...tool 'foo': "``
that carries no diagnostic payload in logs/agent output.
"""

import pytest
from arcade_core.errors import (
    ErrorKind,
    FatalToolError,
    NetworkTransportError,
    RetryableToolError,
    ToolkitLoadError,
    UpstreamError,
)


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


# ---- NetworkTransportError -------------------------------------------------


def test_network_transport_error_is_sibling_to_upstream_error():
    """NetworkTransportError and UpstreamError serve different semantic roles.

    The classification helpers must not mix them up — any consumer keying on
    ``is_upstream_error`` (telemetry dashboards, retry playbooks) relies on
    that distinction being clean.
    """
    nte = NetworkTransportError("boom")
    ue = UpstreamError("boom", status_code=500)

    assert nte.is_network_transport_error is True
    assert nte.is_upstream_error is False

    assert ue.is_upstream_error is True
    assert ue.is_network_transport_error is False


def test_network_transport_error_defaults():
    err = NetworkTransportError("boom")
    assert err.kind is ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
    assert err.can_retry is True
    # No complete response was received, so there is no status code.
    assert err.status_code is None


def test_network_transport_error_rejects_non_network_kind():
    """The class invariant — kind must be in the NETWORK_TRANSPORT_ namespace —
    protects telemetry and classification helpers from accidental pollution."""
    with pytest.raises(ValueError, match="NETWORK_TRANSPORT_"):
        NetworkTransportError("x", kind=ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR)


def test_network_transport_error_to_payload_omits_status_code():
    err = NetworkTransportError(
        "timed out",
        kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
        can_retry=True,
        extra={"error_type": "PoolTimeout"},
    )
    payload = err.to_payload()
    assert payload["status_code"] is None
    assert payload["kind"] is ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
    assert payload["can_retry"] is True
    assert payload["error_type"] == "PoolTimeout"
