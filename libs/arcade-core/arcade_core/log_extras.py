"""Shared helpers for tool-call-error logs and span attributes.

Field names (``error_*``, ``tool_name``, ``toolkit_version``) are load-bearing
for Datadog dashboards — renaming is a breaking change for downstream alerts.

Data policy: a tool's error ``message`` and ``developer_message`` routinely echo
end-user content (inputs, upstream responses, emails, tokens). Workers must not
keep execution inputs or results, so these helpers only ever emit error
*metadata* (kind, status, retry advice, which declared parameter failed
validation, and the type and size of each declared input). The full text belongs at DEBUG level
only; callers still return it to the caller of the tool.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from arcade_core.errors import ErrorKind
from arcade_core.schema import ToolCallError


def _kind_value(error: ToolCallError) -> str:
    return error.kind.value if hasattr(error.kind, "value") else str(error.kind)


def build_tool_error_log_extra(
    error: ToolCallError,
    *,
    tool_name: str,
    toolkit_name: str | None = None,
    toolkit_version: str | None = None,
    inputs: Mapping[str, Any] | None = None,
    parameter_names: Sequence[str] = (),
    **additional: Any,
) -> dict[str, Any]:
    """Build the structured ``extra`` dict for a failed-tool-call WARNING log.

    Contains no error text (``message`` / ``developer_message``); log those at
    DEBUG level only.

    Args:
        error: The ``ToolCallError``. ``kind`` is normalized via ``.value``
            so Datadog facets on a stable string, not ``"ErrorKind.X"``.
        tool_name: Resolved tool identifier — callers should pass the same
            value OTel spans / metrics use (e.g. ``tool_fqname.name``) so
            logs correlate across signals.
        toolkit_name: Optional toolkit identifier.
        toolkit_version: Optional resolved toolkit version.
        inputs: Optional tool inputs. Only their shape (``tool_inputs_shape``)
            is logged, never the values.
        parameter_names: The tool's declared parameter names, in order.
        **additional: Caller-specific extras (e.g. ``execution_id``). Cannot
            override canonical fields.

    Returns:
        Dict suitable for ``logger.warning(..., extra=<dict>)``. Optional
        *kwargs* are omitted when not supplied so Datadog can distinguish
        "unset" from "set-to-None"; canonical ``error_*`` fields are always
        present (``None`` when unset on the error; ``error_status_code`` is
        also ``None`` when it is not an HTTP status).
    """
    extra: dict[str, Any] = {
        "error_kind": _kind_value(error),
        "error_status_code": _http_status(error),
        "error_can_retry": error.can_retry,
        "error_retry_after_ms": error.retry_after_ms,
        "tool_name": tool_name,
    }
    if toolkit_name is not None:
        extra["toolkit_name"] = toolkit_name
    if toolkit_version is not None:
        extra["toolkit_version"] = toolkit_version
    inputs_shape = describe_inputs_shape(inputs, parameter_names)
    if inputs_shape:
        extra["tool_inputs_shape"] = inputs_shape

    for k, v in additional.items():
        if k in extra:
            continue
        extra[k] = v
    return extra


_MISSING = object()


def _http_status(error: ToolCallError) -> int | None:
    """Return ``status_code`` only when it is an HTTP status (100-599).

    ``status_code`` is set by tool code and can be any int; outside the HTTP
    range it is the tool's own number and we can't know what it carries.
    """
    status = error.status_code
    if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599:
        return status
    return None


def _value_shape(value: Any) -> str:
    """Describe a value by type and size, never by content."""
    if value is _MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return f"string({len(value)})"
    if isinstance(value, Mapping):
        return f"object({len(value)})"
    if isinstance(value, (list, tuple)):
        return f"array({len(value)})"
    return "object"


def describe_inputs_shape(
    inputs: Mapping[str, Any] | None, parameter_names: Sequence[str] = ()
) -> str:
    """Describe each declared input by type and size, never its value.

    Example: ``channel=string(9) limit=number``.

    Only declared parameter names are written: input keys come from the
    caller, so an undeclared key (``jane_doe_ssn``) is only counted.
    """
    if not inputs:
        return ""
    declared = set(parameter_names)
    parts = [f"{name}={_value_shape(inputs[name])}" for name in parameter_names if name in inputs]
    undeclared = sum(1 for key in inputs if key not in declared)
    if undeclared:
        parts.append(f"+{undeclared} undeclared")
    return " ".join(parts)


_VALIDATION_PREFIX = "Pydantic validation failed: "
_VALIDATION_ENTRY = re.compile(r"^(?P<loc>.+)\[[A-Za-z0-9_]+\]$")


def _validation_details(
    error: ToolCallError,
    inputs: Mapping[str, Any] | None,
    parameter_names: Sequence[str],
) -> list[str]:
    """Name the declared parameters that failed input validation.

    The executor writes ``Pydantic validation failed: limit[int_parsing]``
    into ``developer_message``. That text is untrusted (a tool can raise its
    own ``ToolInputError``), so only names matching a declared parameter are
    written. Only the top-level parameter is named; deeper ``loc`` parts can
    be keys the caller sent, so a nested failure is only flagged.
    """
    if error.kind != ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE or not parameter_names:
        return []
    # ``with_context`` prefixes the text: ``[TOOL_RUNTIME_BAD_INPUT_VALUE]
    # ToolInputError during execution of tool 'x': Pydantic validation failed: ...``
    _, found, entries = (error.developer_message or "").partition(_VALIDATION_PREFIX)
    if not found:
        return []
    declared = set(parameter_names)
    details: dict[str, str] = {}
    for entry in entries.split("; "):
        match = _VALIDATION_ENTRY.match(entry)
        if not match:
            continue
        top, _, rest = match.group("loc").partition(".")
        if top not in declared or (top in details and not rest):
            continue
        if rest:
            details[top] = f"{top} has a nested value that failed validation"
        else:
            value = inputs.get(top, _MISSING) if inputs is not None else _MISSING
            details[top] = f"{top} failed validation, got {_value_shape(value)}"
    return list(details.values())


def format_tool_error_summary(
    error: ToolCallError,
    *,
    inputs: Mapping[str, Any] | None = None,
    parameter_names: Sequence[str] = (),
) -> str:
    """Render a one-line, text-free summary of a tool error.

    Uses the Engine's wording so the same failure reads the same everywhere:
    ``UPSTREAM_RUNTIME_RATE_LIMIT (HTTP 429, retry after 2000ms)`` or
    ``TOOL_RUNTIME_BAD_INPUT_VALUE (HTTP 400): limit failed validation, got string(3)``.
    """
    qualifiers = []
    status = _http_status(error)
    if status is not None:
        qualifiers.append(f"HTTP {status}")
    if error.retry_after_ms is not None:
        qualifiers.append(f"retry after {error.retry_after_ms}ms")
    summary = _kind_value(error)
    if qualifiers:
        summary += f" ({', '.join(qualifiers)})"
    details = _validation_details(error, inputs, parameter_names)
    if details:
        summary += ": " + "; ".join(details)
    return summary


def build_tool_error_span_attributes(
    error: ToolCallError,
    *,
    inputs: Mapping[str, Any] | None = None,
    parameter_names: Sequence[str] = (),
    execution_id: str | None = None,
) -> dict[str, str | int | bool]:
    """Build stable span attributes for failed tool-call diagnostics.

    Contains no error text (``message`` / ``developer_message``) and no input
    values. ``execution_id`` links the span to the logs that hold the detail.
    """
    attrs: dict[str, str | int | bool] = {
        "tool_error_kind": _kind_value(error),
        "tool_error_can_retry": error.can_retry,
        "tool_error_summary": format_tool_error_summary(
            error, inputs=inputs, parameter_names=parameter_names
        ),
    }
    status = _http_status(error)
    if status is not None:
        attrs["tool_error_status_code"] = status
    if error.retry_after_ms is not None:
        attrs["tool_error_retry_after_ms"] = error.retry_after_ms
    inputs_shape = describe_inputs_shape(inputs, parameter_names)
    if inputs_shape:
        attrs["tool_inputs_shape"] = inputs_shape
    if execution_id:
        attrs["execution_id"] = execution_id
    return attrs
