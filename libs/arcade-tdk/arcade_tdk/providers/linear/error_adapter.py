"""Vendor-specific GraphQL error adapter for Linear's API.

Linear's GraphQL SDK dispatches errors by the wire-format ``extensions.type``
(a lowercase phrase like ``"feature not accessible"``) rather than the Apollo
convention of ``extensions.code`` (SCREAMING_SNAKE_CASE). This adapter teaches
the base :class:`GraphQLErrorAdapter` about Linear's taxonomy so the toolkit
surfaces accurate ``UpstreamError`` / ``UpstreamRateLimitError`` instead of an
opaque ``FatalToolError``.

The authoritative mapping below is lifted from the ``@linear/sdk`` v82.1.0
source (``errorMap``). Do not invent new entries — verify against the SDK
first.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any

from arcade_core.errors import UpstreamError, UpstreamRateLimitError

from arcade_tdk.providers.graphql.error_adapter import GraphQLErrorAdapter

logger = logging.getLogger(__name__)

# Wire-format ``extensions.type`` (lowercase phrase) → HTTP status.
# Sourced from @linear/sdk errorMap.
_LINEAR_TYPE_TO_STATUS: dict[str, int] = {
    "authentication error": 401,
    "forbidden": 403,
    "feature not accessible": 403,
    "invalid input": 400,
    "user error": 400,
    "graphql error": 400,
    "ratelimited": 429,
    "lock timeout": 503,
    "internal error": 500,
    "bootstrap error": 500,
    "usage limit exceeded": 402,
    "network error": 502,
    "unknown": 500,
    "other": 500,
}

# Secondary fallback lookup when ``extensions.type`` is absent but
# ``extensions.code`` is populated (SCREAMING_SNAKE_CASE on the wire).
_LINEAR_CODE_TO_STATUS: dict[str, int] = {
    "RATELIMITED": 429,
    "AUTHENTICATION_ERROR": 401,
    "FEATURE_NOT_ACCESSIBLE": 403,
    "INVALID_INPUT": 400,
    "USER_ERROR": 400,
}

_RATE_LIMIT_TYPES = {"ratelimited"}
_RATE_LIMIT_CODES = {"RATELIMITED"}

_DEVELOPER_MESSAGE_MAX_LEN = 2000


class LinearGraphQLAdapter(GraphQLErrorAdapter):
    """GraphQL error adapter specialized for Linear's API.

    Inherits the base dispatcher and only overrides ``_handle_query_error``.
    Transport-layer errors (HTTP 5xx, connection failures, protocol errors)
    continue to use the base class implementation — there's nothing vendor
    specific about them.
    """

    slug = "_linear_graphql"

    def _handle_query_error(self, exc: Any) -> UpstreamError:
        """Map a Linear ``TransportQueryError`` into an ``UpstreamError``.

        Status-code precedence per error, highest wins across all errors:
          1. ``extensions.statusCode`` (numeric, Linear's own authoritative hint)
          2. ``extensions.http.status`` (numeric, same signal in a nested shape)
          3. ``extensions.type`` lookup (lowercase phrase)
          4. ``extensions.code`` lookup (SCREAMING_SNAKE_CASE) as last resort.
        """
        errors_list = exc.errors or []
        logger.debug("Linear GraphQL query errors: %s", errors_list)

        types: list[str] = []
        codes: list[str] = []
        paths: list[list[Any]] = []
        vendor_statuses: list[int] = []
        user_presentable_messages: list[str] = []

        # Track the highest *mapped* Linear status. Fall back to the base
        # adapter's default (422) only if no error resolved to a known mapping,
        # so a known-400 isn't masked by the default.
        mapped_status: int | None = None
        is_rate_limited = False

        for e in errors_list:
            if not isinstance(e, dict):
                continue

            ext = e.get("extensions") if isinstance(e.get("extensions"), dict) else {}
            if not isinstance(ext, dict):
                ext = {}

            # Trust Linear's own numeric hint when present. Linear populates
            # either ``extensions.statusCode`` or ``extensions.http.status``
            # (occasionally both). Either is authoritative over our type map.
            vendor_status = _extract_vendor_status(ext)
            error_status: int | None = vendor_status
            if vendor_status is not None:
                vendor_statuses.append(vendor_status)

            # Wire-format type — Linear's taxonomy dispatcher, used as a
            # fallback when no numeric hint is present.
            linear_type = ext.get("type")
            if isinstance(linear_type, str):
                types.append(linear_type)
                if error_status is None:
                    error_status = _LINEAR_TYPE_TO_STATUS.get(linear_type.lower())
                if linear_type.lower() in _RATE_LIMIT_TYPES:
                    is_rate_limited = True

            # Apollo-style SCREAMING_SNAKE_CASE code as last resort.
            code = ext.get("code")
            if isinstance(code, str):
                codes.append(code)
                if error_status is None:
                    error_status = _LINEAR_CODE_TO_STATUS.get(code)
                if code in _RATE_LIMIT_CODES:
                    is_rate_limited = True

            if error_status is not None and (mapped_status is None or error_status > mapped_status):
                mapped_status = error_status

            path = e.get("path")
            if isinstance(path, list):
                paths.append(path)

            user_presentable = ext.get("userPresentableMessage")
            if isinstance(user_presentable, str) and user_presentable:
                user_presentable_messages.append(user_presentable)

        status = (
            mapped_status if mapped_status is not None else HTTPStatus.UNPROCESSABLE_ENTITY.value
        )

        unique_types = sorted({t.lower() for t in types if isinstance(t, str)})
        unique_codes = sorted(set(codes))
        unique_vendor_statuses = sorted(set(vendor_statuses))

        # Agent-facing message: prefer curated user-safe text from Linear if
        # present, otherwise a safe template. NEVER interpolate raw
        # ``errors[].message`` into the agent-facing field (data-leak policy).
        if user_presentable_messages:
            message = user_presentable_messages[0]
        else:
            phrase = _safe_status_phrase(status)
            message = f"Upstream Linear GraphQL error ({status} {phrase})."

        # Developer message: raw first error (JSON) for server-side debugging.
        developer_message = _build_developer_message(errors_list)

        extra: dict[str, Any] = {
            "service": self.slug,
            "error_type": "TransportQueryError",
            "linear_error_types": unique_types,
            "gql_error_paths": paths,
            "gql_error_codes": unique_codes,
        }
        if unique_vendor_statuses:
            extra["linear_vendor_statuses"] = unique_vendor_statuses

        if is_rate_limited:
            headers = self._get_headers(exc) or self._get_headers(exc.__cause__) or {}
            return UpstreamRateLimitError(
                message=message,
                retry_after_ms=self._parse_retry_ms(headers),
                developer_message=developer_message,
                extra=extra,
            )

        return UpstreamError(
            message=message,
            status_code=status,
            developer_message=developer_message,
            extra=extra,
        )


def _safe_status_phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Unknown Status"


def _extract_vendor_status(ext: dict[str, Any]) -> int | None:
    """Return Linear's own numeric HTTP-status hint if present.

    Linear embeds either ``extensions.statusCode`` or ``extensions.http.status``
    (or both) in its error payloads. Either is an authoritative signal over our
    local type / code maps.
    """
    status = ext.get("statusCode")
    if isinstance(status, bool):
        # bool is a subclass of int in Python; explicitly exclude it.
        status = None
    if isinstance(status, int):
        return status

    http = ext.get("http")
    if isinstance(http, dict):
        http_status = http.get("status")
        if isinstance(http_status, bool):
            http_status = None
        if isinstance(http_status, int):
            return http_status

    return None


def _build_developer_message(errors_list: list[Any]) -> str:
    """JSON-encode the first error (message/path/locations/extensions) for logs.

    Raw upstream content is allowed in ``developer_message`` — this field is
    sent to server-side logs only, never back to the agent. Capped to keep the
    log entry bounded.
    """
    if not errors_list:
        return "Linear GraphQL error"

    first = errors_list[0]
    if not isinstance(first, dict):
        try:
            return f"Linear GraphQL error: {str(first)[:_DEVELOPER_MESSAGE_MAX_LEN]}"
        except Exception:
            return "Linear GraphQL error"

    payload = {
        "message": first.get("message"),
        "path": first.get("path"),
        "locations": first.get("locations"),
        "extensions": first.get("extensions"),
    }
    try:
        encoded = json.dumps(payload, default=str)
    except Exception:
        encoded = str(payload)

    if len(encoded) > _DEVELOPER_MESSAGE_MAX_LEN:
        encoded = encoded[:_DEVELOPER_MESSAGE_MAX_LEN] + "...<truncated>"
    return encoded
