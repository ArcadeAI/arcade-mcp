"""Shared helper for tool-call-error structured-log extras.

Field names (``error_*``, ``tool_name``, ``toolkit_version``) are load-bearing
for Datadog dashboards — renaming is a breaking change for downstream alerts.
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

    for k, v in additional.items():
        if k in extra:
            continue
        extra[k] = v
    return extra
