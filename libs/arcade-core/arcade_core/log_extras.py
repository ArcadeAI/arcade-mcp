"""Shared helpers for tool-call-error logs and span attributes.

Field names (``error_*``, ``tool_name``, ``toolkit_version``) are load-bearing
for Datadog dashboards — renaming is a breaking change for downstream alerts.

Data policy: a tool's error ``message`` and ``developer_message`` routinely echo
end-user content (inputs, upstream responses, emails, tokens). Workers must not
keep execution inputs or results, so these helpers only ever emit error
*metadata* (kind, status, retry advice). The full text belongs at DEBUG level
only; callers still return it to the caller of the tool.
"""

from __future__ import annotations

from typing import Any

from arcade_core.schema import ToolCallError


def _kind_value(error: ToolCallError) -> str:
    return error.kind.value if hasattr(error.kind, "value") else str(error.kind)


def build_tool_error_log_extra(
    error: ToolCallError,
    *,
    tool_name: str,
    toolkit_name: str | None = None,
    toolkit_version: str | None = None,
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
        **additional: Caller-specific extras (e.g. ``execution_id``). Cannot
            override canonical fields.

    Returns:
        Dict suitable for ``logger.warning(..., extra=<dict>)``. Optional
        *kwargs* are omitted when not supplied so Datadog can distinguish
        "unset" from "set-to-None"; canonical ``error_*`` fields are always
        present (``None`` when unset on the error).
    """
    extra: dict[str, Any] = {
        "error_kind": _kind_value(error),
        "error_status_code": error.status_code,
        "error_can_retry": error.can_retry,
        "error_retry_after_ms": error.retry_after_ms,
        "tool_name": tool_name,
    }
    if toolkit_name is not None:
        extra["toolkit_name"] = toolkit_name
    if toolkit_version is not None:
        extra["toolkit_version"] = toolkit_version

    for k, v in additional.items():
        if k in extra:
            continue
        extra[k] = v
    return extra


def format_tool_error_summary(error: ToolCallError) -> str:
    """Render a one-line, text-free summary of a tool error for log messages.

    Example: ``kind=UPSTREAM_RUNTIME_NOT_FOUND status=404 can_retry=False``.
    """
    parts = [f"kind={_kind_value(error)}"]
    if error.status_code is not None:
        parts.append(f"status={error.status_code}")
    parts.append(f"can_retry={error.can_retry}")
    if error.retry_after_ms is not None:
        parts.append(f"retry_after_ms={error.retry_after_ms}")
    return " ".join(parts)


def build_tool_error_span_attributes(error: ToolCallError) -> dict[str, str | int | bool]:
    """Build stable span attributes for failed tool-call diagnostics.

    Contains no error text (``message`` / ``developer_message``).
    """
    attrs: dict[str, str | int | bool] = {
        "tool_error_kind": _kind_value(error),
        "tool_error_can_retry": error.can_retry,
    }
    if error.status_code is not None:
        attrs["tool_error_status_code"] = error.status_code
    if error.retry_after_ms is not None:
        attrs["tool_error_retry_after_ms"] = error.retry_after_ms
    return attrs
