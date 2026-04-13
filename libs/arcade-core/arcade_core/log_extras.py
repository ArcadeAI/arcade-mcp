"""Helpers for building structured-log ``extra={...}`` dicts used by Datadog
faceting on tool-call failures.

Lives in arcade-core because both ``arcade-mcp-server`` (MCP transport) and
``arcade-serve`` (Arcade Worker transport) emit the same shape of structured
warning when a tool call fails. Centralizing the dict construction here
prevents the two call sites from drifting silently — the field names
(``error_kind``, ``error_message``, …) are load-bearing for ops dashboards
and renaming any of them is a breaking change for downstream alerts.

Field-name conventions (kept aligned with the OTel span attributes set in
``arcade_serve.core.base.BaseWorker.call_tool`` and the ``tool_counter``
metric labels): ``tool_name``, ``toolkit_name``, ``toolkit_version``.
Error-specific fields are prefixed ``error_*`` so they can be filtered as a
group and don't collide with the generic identifiers above.
"""

from __future__ import annotations

from typing import Any

from arcade_core.schema import ToolCallError


def build_tool_error_log_extra(
    error: ToolCallError,
    *,
    tool_name: str,
    toolkit_name: str | None = None,
    toolkit_version: str | None = None,
    **additional: Any,
) -> dict[str, Any]:
    """Build the structured ``extra`` dict for a failed-tool-call WARNING log.

    Args:
        error: The ``ToolCallError`` carried by ``ToolCallOutput.error``. Its
            ``kind`` is normalized to a string (``.value`` when it's an Enum)
            so Datadog facets on a stable string value rather than a Python
            ``repr`` like ``"ErrorKind.TOOL_RUNTIME_FATAL"``.
        tool_name: The tool identifier to put in the ``tool_name`` facet.
            Callers should pass the *resolved* identifier (e.g.
            ``tool_fqname.name`` on the worker side, or the request's tool
            name on the MCP side) so log lines correlate with metrics/spans
            that label by the same value.
        toolkit_name: Optional toolkit identifier; included when the caller
            knows it (worker has it from ``tool_fqname``; MCP server does
            not always have it cheaply at log time).
        toolkit_version: Optional resolved toolkit version. Same source as
            the OTel span attribute of the same name.
        **additional: Caller-specific extras to merge in (e.g. the worker
            adds ``execution_id``). These are merged AFTER the canonical
            fields so a caller cannot accidentally override the contract.

    Returns:
        A flat dict suitable for ``logger.warning(..., extra=<dict>)``.
        Optional fields are only present when the corresponding argument
        was supplied (None values are omitted) so Datadog can distinguish
        "unset" from "set-to-falsy".
    """
    kind_value = error.kind.value if hasattr(error.kind, "value") else str(error.kind)

    extra: dict[str, Any] = {
        "error_kind": kind_value,
        "error_message": error.message,
        "error_developer_message": error.developer_message,
        "error_status_code": error.status_code,
        "error_can_retry": error.can_retry,
        "tool_name": tool_name,
    }
    if toolkit_name is not None:
        extra["toolkit_name"] = toolkit_name
    if toolkit_version is not None:
        extra["toolkit_version"] = toolkit_version

    # Caller-supplied additions (e.g. execution_id) are merged after the
    # canonical fields so they cannot override the contract by mistake.
    for k, v in additional.items():
        if k in extra:
            continue
        extra[k] = v
    return extra
