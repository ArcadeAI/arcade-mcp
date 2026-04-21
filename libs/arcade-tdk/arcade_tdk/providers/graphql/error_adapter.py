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

from arcade_tdk.providers.http.error_adapter import BaseHTTPErrorMapper

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
        """Handle TransportQueryError (GraphQL errors in response body).

        Status-code resolution per error (highest across all errors wins):

          1. Numeric ``extensions.http.status`` or ``extensions.statusCode``.
             Many servers (Apollo via ``apollo-server-plugin-http``, Linear,
             etc.) embed an authoritative HTTP status hint directly in the
             error payload. Trust it over any lookup table.
          2. ``extensions.code`` lookup in :data:`_GQL_CODE_TO_STATUS`.
          3. Fall through to ``422 Unprocessable Entity`` if neither resolved.

        Rate-limit classification: any error that resolves to status 429 (by
        numeric hint or code map) routes to ``UpstreamRateLimitError`` with
        ``retry_after_ms`` parsed from the upstream response's rate-limit
        headers (if the underlying transport exposed them on ``__cause__``).

        Agent-facing message: if any error carries a curated
        ``extensions.userPresentableMessage`` (Linear convention, harmless for
        other vendors), that string wins. Otherwise the message keeps the
        long-standing ``"Upstream GraphQL error: <joined raw messages>"``
        format for Apollo compatibility.
        """
        errors_list = exc.errors or []
        logger.debug("GraphQL query errors: %s", errors_list)

        messages = [_extract_error_message(e.get("message")) for e in errors_list]
        joined = "; ".join(messages) if messages else "Unknown GraphQL error"

        codes: list[str] = []
        paths: list[list[Any]] = []
        vendor_statuses: list[int] = []
        user_presentable_messages: list[str] = []

        mapped_status: int | None = None

        for e in errors_list:
            if not isinstance(e, dict):
                continue
            raw_ext = e.get("extensions")
            ext: dict[str, Any] = raw_ext if isinstance(raw_ext, dict) else {}

            # 1. Numeric status hint — authoritative when present.
            vendor_status = _extract_vendor_status(ext)
            error_status: int | None = vendor_status
            if vendor_status is not None:
                vendor_statuses.append(vendor_status)

            # 2. Code lookup — fallback for servers that don't populate a
            #    numeric hint.
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

            user_presentable = ext.get("userPresentableMessage")
            if isinstance(user_presentable, str) and user_presentable:
                user_presentable_messages.append(user_presentable)

        is_rate_limited = mapped_status == HTTPStatus.TOO_MANY_REQUESTS.value
        status = (
            HTTPStatus.TOO_MANY_REQUESTS.value
            if is_rate_limited
            else (
                mapped_status
                if mapped_status is not None
                else HTTPStatus.UNPROCESSABLE_ENTITY.value
            )
        )

        unique_codes = sorted(set(codes))
        unique_vendor_statuses = sorted(set(vendor_statuses))

        message = (
            user_presentable_messages[0]
            if user_presentable_messages
            else f"Upstream GraphQL error: {joined}"
        )
        developer_message = (
            f"GraphQL error codes: {', '.join(unique_codes)}" if unique_codes else "GraphQL error"
        )
        extra: dict[str, Any] = {
            "service": self.slug,
            "error_type": "TransportQueryError",
            "gql_error_codes": unique_codes,
            "gql_error_paths": paths,
        }
        if unique_vendor_statuses:
            extra["gql_vendor_statuses"] = unique_vendor_statuses

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

    def _handle_transport_error(self, exc: Any) -> UpstreamError:
        """Handle TransportServerError and other transport errors."""
        status = getattr(exc, "code", None)
        if not isinstance(status, int):
            status = HTTPStatus.INTERNAL_SERVER_ERROR.value

        # Extract headers for rate limit detection (check exc and __cause__)
        headers = self._get_headers(exc) or self._get_headers(exc.__cause__)

        # Extract URL from __cause__ (aiohttp/httpx/requests store it there)
        url, method = self._get_request_info(exc.__cause__)

        return self._map_status_to_error(
            status=status,
            headers=headers or {},
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
