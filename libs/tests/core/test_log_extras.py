"""Tests for ``build_tool_error_log_extra``.

Locks the Datadog-facet contract shared by the MCP and worker transports.
Field names are load-bearing for dashboards.
"""

import pytest
from arcade_core.errors import ErrorKind
from arcade_core.log_extras import (
    build_tool_error_log_extra,
    build_tool_error_span_attributes,
    format_tool_error_summary,
)
from arcade_core.schema import ToolCallError


def _err(**kw):
    defaults = {
        "message": "Spreadsheet not found",
        "kind": ErrorKind.TOOL_RUNTIME_FATAL,
        "developer_message": None,
        "status_code": 404,
        "can_retry": False,
    }
    defaults.update(kw)
    return ToolCallError(**defaults)


def test_canonical_field_contract():
    """Locks the canonical field names every Datadog dashboard depends on."""
    extra = build_tool_error_log_extra(_err(developer_message="dev: x"), tool_name="MyTool")
    assert extra == {
        "error_kind": "TOOL_RUNTIME_FATAL",
        "error_status_code": 404,
        "error_can_retry": False,
        "error_retry_after_ms": None,
        "tool_name": "MyTool",
    }


def test_log_extra_never_contains_error_text():
    """Error text echoes end-user content; it must not reach logs above DEBUG."""
    err = _err(
        message="No contact with email jane@example.com",
        developer_message="GET /contacts?email=jane@example.com",
        additional_prompt_content="try jane@example.com again",
        stacktrace="Traceback ... jane@example.com",
    )
    extra = build_tool_error_log_extra(err, tool_name="t")
    assert "jane@example.com" not in str(extra)
    assert "jane@example.com" not in format_tool_error_summary(err)
    assert "jane@example.com" not in str(build_tool_error_span_attributes(err))


def test_kind_enum_value_used_not_repr():
    """``error_kind`` must be the stable string code (Datadog facets on
    ``"TOOL_RUNTIME_FATAL"``, NOT the Python repr ``"ErrorKind.TOOL_RUNTIME_FATAL"``)."""
    extra = build_tool_error_log_extra(
        _err(kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT), tool_name="t"
    )
    assert extra["error_kind"] == "UPSTREAM_RUNTIME_RATE_LIMIT"
    assert "ErrorKind." not in extra["error_kind"]


def test_kind_string_fallback_when_not_enum():
    """If something passes a raw string in ``kind`` (not a ToolCallError that
    would normalize it), the helper still produces a sensible value."""

    class FakeError:
        kind = "CUSTOM_KIND"
        message = "x"
        developer_message = None
        status_code = None
        can_retry = False
        retry_after_ms = None

    extra = build_tool_error_log_extra(FakeError(), tool_name="t")
    assert extra["error_kind"] == "CUSTOM_KIND"


def test_optional_toolkit_fields_omitted_by_default():
    """Optional toolkit fields are only present when supplied — Datadog can
    distinguish 'not set' from 'set to None'."""
    extra = build_tool_error_log_extra(_err(), tool_name="MyTool")
    assert "toolkit_name" not in extra
    assert "toolkit_version" not in extra


def test_optional_toolkit_fields_included_when_supplied():
    extra = build_tool_error_log_extra(
        _err(),
        tool_name="MyTool",
        toolkit_name="MyKit",
        toolkit_version="1.2.3",
    )
    assert extra["toolkit_name"] == "MyKit"
    assert extra["toolkit_version"] == "1.2.3"


def test_additional_extras_merged():
    """Worker passes ``execution_id``; MCP server may add others. The helper
    accepts arbitrary additions via **kwargs."""
    extra = build_tool_error_log_extra(
        _err(),
        tool_name="t",
        execution_id="exec_42",
    )
    assert extra["execution_id"] == "exec_42"


def test_additional_extras_cannot_clobber_canonical_fields():
    """A caller passing a key that collides with the canonical contract must
    NOT be able to override the canonical value — that would let one call site
    silently change the Datadog facet for every dashboard."""
    extra = build_tool_error_log_extra(
        _err(message="canonical"),
        tool_name="t",
        error_kind="OVERRIDE_ATTEMPT",
        tool_name_override="ignored too",
    )
    assert extra["error_kind"] == "TOOL_RUNTIME_FATAL"
    # Non-canonical-name additions still pass through.
    assert extra["tool_name_override"] == "ignored too"


def test_span_attributes_contract():
    attrs = build_tool_error_span_attributes(_err(developer_message="dev: x"))
    assert attrs == {
        "tool_error_kind": "TOOL_RUNTIME_FATAL",
        "tool_error_can_retry": False,
        "tool_error_status_code": 404,
    }


def test_span_attributes_include_retry_after_when_present():
    attrs = build_tool_error_span_attributes(
        _err(
            kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT,
            status_code=None,
            can_retry=True,
            retry_after_ms=1500,
        )
    )
    assert attrs == {
        "tool_error_kind": "UPSTREAM_RUNTIME_RATE_LIMIT",
        "tool_error_can_retry": True,
        "tool_error_retry_after_ms": 1500,
    }


def test_summary_format():
    assert format_tool_error_summary(_err()) == "kind=TOOL_RUNTIME_FATAL status=404 can_retry=False"
    assert (
        format_tool_error_summary(
            _err(
                kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT,
                status_code=429,
                can_retry=True,
                retry_after_ms=2000,
            )
        )
        == "kind=UPSTREAM_RUNTIME_RATE_LIMIT status=429 can_retry=True retry_after_ms=2000"
    )
    assert format_tool_error_summary(_err(status_code=None)) == (
        "kind=TOOL_RUNTIME_FATAL can_retry=False"
    )


def test_status_code_none_propagates():
    extra = build_tool_error_log_extra(_err(status_code=None), tool_name="t")
    assert "error_status_code" in extra
    assert extra["error_status_code"] is None


@pytest.mark.parametrize("can_retry", [True, False])
def test_can_retry_propagates_as_bool(can_retry):
    extra = build_tool_error_log_extra(_err(can_retry=can_retry), tool_name="t")
    assert extra["error_can_retry"] is can_retry
