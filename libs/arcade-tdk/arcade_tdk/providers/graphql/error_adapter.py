import importlib
import logging
from functools import lru_cache
from http import HTTPStatus
from typing import Any

from arcade_core.errors import (
    ErrorKind,
    NetworkTransportError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

from arcade_tdk.providers.http.error_adapter import RATE_HEADERS, BaseHTTPErrorMapper

logger = logging.getLogger(__name__)

# Broadly-observed GraphQL error codes mapped to HTTP status codes. The Apollo
# defaults plus two widely-used rate-limit spellings (GitHub uses
# ``RATE_LIMITED``, Shopify uses ``THROTTLED``). Vendor-specific taxonomies
# (e.g. Linear's lowercase ``extensions.type`` phrases) are not added here —
# vendors that populate a numeric ``extensions.http.status`` / ``statusCode``
# are handled authoritatively by that path below, without needing a map entry.
_GQL_CODE_TO_STATUS = {
    "UNAUTHENTICATED": 401,
    "NOT_AUTHENTICATED": 401,
    "FORBIDDEN": 403,
    "ACCESS_DENIED": 403,
    "NOT_FOUND": 404,
    "BAD_USER_INPUT": 400,
    "GRAPHQL_VALIDATION_FAILED": 400,
    "GRAPHQL_PARSE_FAILED": 400,
    "INTERNAL_SERVER_ERROR": 500,
    "RATE_LIMITED": 429,
    "THROTTLED": 429,
}


@lru_cache(maxsize=1)
def _load_gql_transport_errors() -> (
    tuple[type[Any], type[Any], type[Any], type[Any], type[Any]] | None
):
    """Import gql transport exceptions lazily and cache the result."""
    try:
        module = importlib.import_module("gql.transport.exceptions")
    except ImportError:
        logger.debug("gql not installed; GraphQL adapter disabled")
        return None
    else:
        return (
            module.TransportError,
            module.TransportQueryError,
            module.TransportServerError,
            module.TransportConnectionFailed,
            module.TransportProtocolError,
        )


def _extract_error_message(message: Any) -> str:
    """Return the error message or a fallback."""
    if not message:
        return "Unknown GraphQL error"
    try:
        return str(message) or "Unknown GraphQL error"
    except Exception:
        return "Unknown GraphQL error"


def _resolve_retry_after_ms(headers: dict[str, str], mapper: BaseHTTPErrorMapper) -> int:
    """Return parsed ``retry_after_ms`` only when a rate-limit header is present.

    :meth:`BaseHTTPErrorMapper._parse_retry_ms` returns a hard-coded 1000 ms
    default when no recognized header exists — passing that through would
    fabricate a 1-second wait hint for every 429 with no real header. Zero
    here means "no hint from upstream"; callers back off per their own
    policy.
    """
    if any(h in headers for h in RATE_HEADERS):
        return mapper._parse_retry_ms(headers)
    return 0


def _build_safe_graphql_message(status: int, retry_after_ms: int) -> str:
    """Build a fixed agent-facing message for a GraphQL error.

    Mirrors :meth:`BaseHTTPErrorMapper._build_safe_status_message` but uses
    GraphQL-flavored wording. Never embeds raw upstream error text.
    """
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = "Unknown Status"

    base = f"Upstream GraphQL request failed ({phrase})."
    if status == HTTPStatus.TOO_MANY_REQUESTS.value:
        if retry_after_ms > 0:
            # Ceiling-round so sub-1000 ms hints (e.g. from
            # ``x-ratelimit-reset-ms``) still render a ``Retry after 1
            # second(s).`` message rather than being truncated to 0.
            retry_seconds = max(1, (retry_after_ms + 999) // 1000)
            return f"{base} Retry after {retry_seconds} second(s)."
        return f"{base} Rate limit encountered."
    return base


def _collect_upstream_headers(exc: Any, mapper: "GraphQLErrorAdapter") -> dict[str, str]:
    """Extract headers from ``exc`` (preferred) or its ``__cause__`` (fallback).

    Treats ``None`` (no response) and ``{}`` (response but no headers) as
    distinct: ``{}`` on ``exc`` itself means the response is authoritative
    and we must not fall through to ``__cause__``.
    """
    headers = mapper._get_headers(exc)
    if headers is not None:
        return headers
    cause_headers = mapper._get_headers(exc.__cause__)
    return cause_headers if cause_headers is not None else {}


def _build_developer_message(
    errors_list: list[Any], unique_codes: list[str], paths: list[list[Any]]
) -> str:
    """Build the developer-facing detail string (server-side logs only).

    Raw ``errors[].message`` content is allowed here — this field never
    reaches the agent.
    """
    raw_messages = [
        _extract_error_message(e.get("message")) for e in errors_list if isinstance(e, dict)
    ]
    joined = "; ".join(raw_messages) if raw_messages else "(no details)"
    parts = [f"GraphQL errors: {joined}"]
    if unique_codes:
        parts.append(f"codes: {', '.join(unique_codes)}")
    if paths:
        parts.append(f"paths: {paths}")
    return " | ".join(parts)


def _extract_vendor_status(ext: dict[str, Any]) -> int | None:
    """Return the server's own numeric HTTP-status hint if present.

    Many GraphQL servers embed a per-error HTTP status directly in
    ``extensions`` — Apollo's ``apollo-server-plugin-http`` uses
    ``extensions.http.status``; Linear uses ``extensions.statusCode`` (and
    sometimes also ``extensions.http.status``). When either is present it is
    authoritative: no lookup table can keep up with every vendor's evolving
    taxonomy, but the numeric signal is always meaningful.

    ``bool`` is a subclass of ``int`` in Python; exclude it explicitly so a
    payload accidentally carrying ``statusCode: True`` isn't read as ``1``.
    """
    status = ext.get("statusCode")
    if isinstance(status, bool):
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


class GraphQLErrorAdapter(BaseHTTPErrorMapper):
    """Error adapter for GraphQL clients (specifically 'gql' library)."""

    slug = "_graphql"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """Translate a gql exception into a ToolRuntimeError."""
        gql_types = _load_gql_transport_errors()
        if not gql_types:
            return None

        (
            TransportError,
            TransportQueryError,
            TransportServerError,
            TransportConnectionFailed,
            TransportProtocolError,
        ) = gql_types

        # GraphQL errors in response (HTTP 200 with errors array)
        if isinstance(exc, TransportQueryError):
            return self._handle_query_error(exc)

        # HTTP-level errors (4xx, 5xx) - these can have rate limit headers
        if isinstance(exc, TransportServerError):
            return self._handle_transport_error(exc)

        # Network/protocol errors — the upstream was never reached or never
        # produced a complete response. No HTTP status is available.
        if isinstance(exc, (TransportConnectionFailed, TransportProtocolError)):
            return NetworkTransportError(
                message=("GraphQL request failed before a complete response was received."),
                developer_message=f"{type(exc).__name__}: {exc}",
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE,
                can_retry=True,
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        # Catch-all for unknown TransportError subclasses
        if isinstance(exc, TransportError):
            return self._handle_transport_error(exc)

        return None

    def _handle_query_error(self, exc: Any) -> UpstreamError:
        """Map a ``TransportQueryError`` (GraphQL errors in the response body).

        Status resolution per error (highest across all errors wins):

          1. Numeric ``extensions.http.status`` / ``extensions.statusCode`` —
             authoritative when present (Apollo's ``apollo-server-plugin-http``
             convention; Linear populates both keys).
          2. ``extensions.code`` lookup in :data:`_GQL_CODE_TO_STATUS`.
          3. ``422 Unprocessable Entity`` if neither resolved.

        Agent-facing ``message`` is a fixed template (never interpolates raw
        ``errors[].message``) unless the vendor provides curated
        ``extensions.userPresentableMessage``. Raw upstream content lands in
        ``developer_message`` for server-side logs. This mirrors the data-leak
        discipline of the HTTP adapter's ``_build_safe_status_message``.
        """
        errors_list = exc.errors or []
        logger.debug("GraphQL query errors: %s", errors_list)

        codes: list[str] = []
        paths: list[list[Any]] = []
        user_presentable: str | None = None
        mapped_status: int | None = None

        for e in errors_list:
            if not isinstance(e, dict):
                continue
            raw_ext = e.get("extensions")
            ext: dict[str, Any] = raw_ext if isinstance(raw_ext, dict) else {}

            error_status = _extract_vendor_status(ext)

            code = ext.get("code")
            if isinstance(code, str):
                codes.append(code)
                if error_status is None:
                    error_status = _GQL_CODE_TO_STATUS.get(code)

            if error_status is not None and (mapped_status is None or error_status > mapped_status):
                mapped_status = error_status

            path = e.get("path")
            if isinstance(path, list):
                paths.append(path)

            if user_presentable is None:
                upm = ext.get("userPresentableMessage")
                if isinstance(upm, str) and upm:
                    user_presentable = upm

        status = (
            mapped_status if mapped_status is not None else HTTPStatus.UNPROCESSABLE_ENTITY.value
        )
        unique_codes = sorted(set(codes))
        headers = _collect_upstream_headers(exc, self)
        retry_after_ms = _resolve_retry_after_ms(headers, self)

        # Agent-facing: curated vendor text or a fixed HTTP-status template.
        # Never embed raw ``errors[].message`` content here. On 429 with a
        # real retry hint, append it to the vendor text too so the retry
        # guidance isn't dropped when ``userPresentableMessage`` wins.
        if user_presentable:
            message = user_presentable
            if status == HTTPStatus.TOO_MANY_REQUESTS.value and retry_after_ms > 0:
                retry_seconds = max(1, (retry_after_ms + 999) // 1000)
                message = f"{message} Retry after {retry_seconds} second(s)."
        else:
            message = _build_safe_graphql_message(status, retry_after_ms)

        # Developer-facing: raw upstream detail (server-side logs only).
        developer_message = _build_developer_message(errors_list, unique_codes, paths)

        extra: dict[str, Any] = {
            "service": self.slug,
            "error_type": "TransportQueryError",
            "gql_error_codes": unique_codes,
            "gql_error_paths": paths,
        }

        if status == HTTPStatus.TOO_MANY_REQUESTS.value:
            return UpstreamRateLimitError(
                message=message,
                retry_after_ms=retry_after_ms,
                developer_message=developer_message,
                extra=extra,
            )
        return UpstreamError(
            message=message,
            status_code=status,
            developer_message=developer_message,
            extra=extra,
        )

    def _handle_transport_error(self, exc: Any) -> UpstreamError:
        """Handle TransportServerError and other transport errors."""
        status = getattr(exc, "code", None)
        if not isinstance(status, int):
            status = HTTPStatus.INTERNAL_SERVER_ERROR.value

        # Extract headers for rate limit detection. Use the same helper as
        # ``_handle_query_error`` so empty-dict headers on ``exc`` itself
        # aren't silently overridden by ``__cause__`` headers.
        headers = _collect_upstream_headers(exc, self)

        # Extract URL from __cause__ (aiohttp/httpx/requests store it there)
        url, method = self._get_request_info(exc.__cause__)

        return self._map_status_to_error(
            status=status,
            headers=headers,
            msg=f"Upstream GraphQL request failed with status code {status}.",
            developer_message=str(exc),
            request_url=url,
            request_method=method,
        )

    def _get_headers(self, obj: Any) -> dict[str, str] | None:
        """Extract headers from an object if available."""
        if obj and hasattr(obj, "response") and hasattr(obj.response, "headers"):
            return {k.lower(): v for k, v in obj.response.headers.items()}
        return None

    def _get_request_info(self, cause: Any) -> tuple[str | None, str | None]:
        """Extract URL and method from the __cause__ exception."""
        if not cause:
            return None, None

        # aiohttp: request_info.url
        if hasattr(cause, "request_info"):
            ri = cause.request_info
            url = getattr(ri, "url", None) or getattr(ri, "real_url", None)
            return (str(url), getattr(ri, "method", None)) if url else (None, None)

        # httpx/requests: response.request.url
        if hasattr(cause, "response") and hasattr(cause.response, "request"):
            req = cause.response.request
            url = getattr(req, "url", None)
            return (str(url), getattr(req, "method", None)) if url else (None, None)

        return None, None

    def _build_extra_metadata(
        self, request_url: str | None = None, request_method: str | None = None
    ) -> dict[str, str]:
        """Override to use GraphQL service slug."""
        extra = super()._build_extra_metadata(request_url, request_method)
        extra["service"] = self.slug
        return extra
