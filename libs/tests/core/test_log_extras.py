"""Tests for the tool-error log and span helpers in ``arcade_core.log_extras``.

Locks the Datadog-facet contract shared by the MCP and worker transports.
Field names are load-bearing for dashboards.
"""

import pytest
from arcade_core.errors import ErrorKind
from arcade_core.log_extras import (
    build_tool_error_log_extra,
    build_tool_error_span_attributes,
    describe_inputs_shape,
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
        "tool_error_summary": "TOOL_RUNTIME_FATAL (HTTP 404)",
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
        "tool_error_summary": "UPSTREAM_RUNTIME_RATE_LIMIT (retry after 1500ms)",
    }


def test_span_attributes_include_inputs_shape_and_execution_id():
    attrs = build_tool_error_span_attributes(
        _err(),
        inputs={"channel": "C01234567", "limit": 5},
        parameter_names=["channel", "limit"],
        execution_id="exec_1",
    )
    assert attrs["tool_inputs_shape"] == "channel=string(9) limit=number"
    assert attrs["execution_id"] == "exec_1"
    assert "C01234567" not in str(attrs)


def test_summary_uses_engine_wording():
    assert format_tool_error_summary(_err()) == "TOOL_RUNTIME_FATAL (HTTP 404)"
    assert (
        format_tool_error_summary(
            _err(
                kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT,
                status_code=429,
                can_retry=True,
                retry_after_ms=2000,
            )
        )
        == "UPSTREAM_RUNTIME_RATE_LIMIT (HTTP 429, retry after 2000ms)"
    )
    assert format_tool_error_summary(_err(status_code=None)) == "TOOL_RUNTIME_FATAL"
    assert (
        format_tool_error_summary(
            _err(kind=ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR, status_code=503, can_retry=True)
        )
        == "UPSTREAM_RUNTIME_SERVER_ERROR (HTTP 503, retryable)"
    )


@pytest.mark.parametrize("status_code", [0, 99, 600, 123456789, -1])
def test_non_http_status_is_not_named(status_code):
    """``status_code`` is set by tool code; outside 100-599 it is the tool's own
    number and could carry anything, so it is left out everywhere."""
    err = _err(status_code=status_code)
    assert format_tool_error_summary(err) == "TOOL_RUNTIME_FATAL"
    assert "tool_error_status_code" not in build_tool_error_span_attributes(err)
    assert build_tool_error_log_extra(err, tool_name="t")["error_status_code"] is None


def test_inputs_shape_uses_engine_words_and_never_values():
    shape = describe_inputs_shape(
        {
            "name": "Jane Doe",
            "count": 3,
            "ratio": 0.5,
            "flag": True,
            "tags": ["a", 1],
            "filters": {"email": "jane@example.com"},
            "cursor": None,
            "jane_doe_ssn": "123-45-6789",
            "other_extra": 1,
        },
        ["name", "count", "ratio", "flag", "tags", "filters", "cursor", "absent"],
    )
    # Alphabetical, like the Engine, so whole-line queries match.
    assert shape == (
        "count=number cursor=null filters=object(1 keys) flag=bool name=string(8) "
        "ratio=number tags=list(2) +2 other"
    )
    for value in ("Jane", "jane@example.com", "jane_doe_ssn", "123-45-6789"):
        assert value not in shape


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("jane@example.com", "string(email)"),
        ("123e4567-e89b-12d3-a456-426614174000", "string(uuid)"),
        ("https://example.com/p?token=abc", "string(url)"),
        ("2026-11-24T10:00:00Z", "string(datetime)"),
        ("2026-11-24", "string(date)"),
        ("not an email", "string(12)"),
        ("a" * 300 + "@example.com", "string(312)"),
        (["jane@example.com"], "list(1, email)"),
        (["a", "b"], "list(2, string)"),
        ([1, 2.5], "list(2, number)"),
        ([[1], [2]], "list(2, list)"),
        ([], "list(0)"),
        ({}, "object(0 keys)"),
    ],
)
def test_inputs_shape_formats(value, expected):
    assert describe_inputs_shape({"v": value}, ["v"]) == f"v={expected}"


def test_inputs_shape_names_at_most_20_inputs():
    names = [f"p{i:02d}" for i in range(23)]
    shape = describe_inputs_shape(dict.fromkeys(names, 1) | {"extra": 1}, names)
    assert shape.split()[:20] == [f"p{i:02d}=number" for i in range(20)]
    assert shape.endswith(" +4 other")


def test_inputs_shape_empty_without_inputs():
    assert describe_inputs_shape(None, ["a"]) == ""
    assert describe_inputs_shape({}, ["a"]) == ""
    assert "tool_inputs_shape" not in build_tool_error_span_attributes(_err())
    assert "tool_inputs_shape" not in build_tool_error_log_extra(_err(), tool_name="t")


def test_log_extra_includes_inputs_shape():
    extra = build_tool_error_log_extra(
        _err(), tool_name="t", inputs={"limit": "abc"}, parameter_names=["limit"]
    )
    assert extra["tool_inputs_shape"] == "limit=string(3)"


def _input_err(developer_message):
    return _err(
        kind=ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE,
        status_code=400,
        message="[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError during execution of tool "
        "'x': Invalid input: limit: Input should be a valid integer",
        developer_message=developer_message,
    )


def test_summary_names_failed_parameter_with_real_worker_prefix():
    err = _input_err(
        "[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError during execution of tool 'x': "
        "Pydantic validation failed: limit[int_parsing]"
    )
    assert format_tool_error_summary(
        err, inputs={"limit": "abc", "channel": "C1"}, parameter_names=["channel", "limit"]
    ) == ("TOOL_RUNTIME_BAD_INPUT_VALUE (HTTP 400): limit failed validation, got string(3)")


def test_summary_flags_nested_failure_without_naming_nested_keys():
    err = _input_err(
        "Pydantic validation failed: filters.jane_doe_ssn[string_type]; limit[missing]"
    )
    summary = format_tool_error_summary(
        err, inputs={"filters": {"jane_doe_ssn": 1}}, parameter_names=["filters", "limit"]
    )
    assert summary == (
        "TOOL_RUNTIME_BAD_INPUT_VALUE (HTTP 400): "
        "filters has a nested value that failed validation; "
        "limit failed validation and was not sent"
    )
    assert "jane_doe_ssn" not in summary


def test_summary_reports_undeclared_validation_failures_without_names():
    """Only declared parameter names are written; the developer message is
    untrusted (a tool can raise its own ToolInputError) and input keys come
    from the caller. A failure on an undeclared key is reported once, unnamed."""
    err = _input_err(
        "Pydantic validation failed: jane_doe_ssn[extra_forbidden]; "
        "jane@example.com[x]; <root>[model_type]"
    )
    summary = format_tool_error_summary(err, inputs={}, parameter_names=["limit"])
    assert summary == ("TOOL_RUNTIME_BAD_INPUT_VALUE (HTTP 400): an unexpected parameter was sent")


def test_summary_validation_details_only_for_bad_input_kind():
    err = _err(developer_message="Pydantic validation failed: limit[int_parsing]")
    assert format_tool_error_summary(err, parameter_names=["limit"]) == (
        "TOOL_RUNTIME_FATAL (HTTP 404)"
    )


def test_status_code_none_propagates():
    extra = build_tool_error_log_extra(_err(status_code=None), tool_name="t")
    assert "error_status_code" in extra
    assert extra["error_status_code"] is None


@pytest.mark.parametrize("can_retry", [True, False])
def test_can_retry_propagates_as_bool(can_retry):
    extra = build_tool_error_log_extra(_err(can_retry=can_retry), tool_name="t")
    assert extra["error_can_retry"] is can_retry
