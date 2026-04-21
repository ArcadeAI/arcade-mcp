"""Tests for ``build_tool_error_log_extra``.

Locks the Datadog-facet contract shared by the MCP and worker transports.
Field names are load-bearing for dashboards.
"""

import pytest
from arcade_core.errors import ErrorKind
from arcade_core.log_extras import build_tool_error_log_extra
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
        "error_message": "Spreadsheet not found",
        "error_developer_message": "dev: x",
        "error_status_code": 404,
        "error_can_retry": False,
        "tool_name": "MyTool",
    }


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
        error_message="OVERRIDE_ATTEMPT",
        tool_name_override="ignored too",
    )
    assert extra["error_message"] == "canonical"
    # Non-canonical-name additions still pass through.
    assert extra["tool_name_override"] == "ignored too"


def test_developer_message_none_propagates():
    """``error_developer_message`` is present and explicitly None when the
    error has no developer_message — Datadog needs to distinguish 'unset'
    from 'set to None' on this field specifically."""
    extra = build_tool_error_log_extra(_err(developer_message=None), tool_name="t")
    assert "error_developer_message" in extra
    assert extra["error_developer_message"] is None


def test_status_code_none_propagates():
    extra = build_tool_error_log_extra(_err(status_code=None), tool_name="t")
    assert "error_status_code" in extra
    assert extra["error_status_code"] is None


@pytest.mark.parametrize("can_retry", [True, False])
def test_can_retry_propagates_as_bool(can_retry):
    extra = build_tool_error_log_extra(_err(can_retry=can_retry), tool_name="t")
    assert extra["error_can_retry"] is can_retry
