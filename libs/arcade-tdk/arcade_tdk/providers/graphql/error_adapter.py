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
)

from arcade_tdk.providers.http.error_adapter import BaseHTTPErrorMapper

logger = logging.getLogger(__name__)

# Standard Apollo/GraphQL error codes mapped to HTTP status codes
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
}


# Resolved from `gql.transport.exceptions`, in the order `from_exception` unpacks them.
_GQL_ERROR_NAMES = (
    "TransportError",
    "TransportQueryError",
    "TransportServerError",
    "TransportConnectionFailed",
    "TransportProtocolError",
)


class _MissingGqlError(Exception):
    """Placeholder for a transport exception the installed gql does not define.

    Never raised, so the ``isinstance()`` checks that receive it stay valid but
    can never match.
    """


@lru_cache(maxsize=1)
def _load_gql_transport_errors() -> (
    tuple[type[Any], type[Any], type[Any], type[Any], type[Any]] | None
):
    """Import gql transport exceptions lazily and cache the result.

    gql's exception inventory varies by version — ``TransportConnectionFailed``
    exists on 4.0.x but not on the 3.5.x line. Reading the names eagerly raised
    ``AttributeError`` on 3.5.x, which disabled the whole adapter and dropped the
    real GraphQL message from every error (TOO-1338). Resolve each class
    defensively instead: classes the installed gql defines still map, and any it
    omits fall back to a sentinel that never matches.

    Tolerating a missing class must not mean hiding it: an inventory gap silently
    disables error branches, so name any unresolved class in the log. That
    diagnostic is the difference between debugging the next rename in minutes and
    rediscovering TOO-1338. Log only — never print. This module is reachable from
    the MCP stdio transport, where stray stdout corrupts the protocol.
    """
    try:
        module = importlib.import_module("gql.transport.exceptions")
    except ImportError:
        logger.debug("gql not installed; GraphQL adapter disabled")
        return None

    resolved = {name: getattr(module, name, _MissingGqlError) for name in _GQL_ERROR_NAMES}

    unresolved = [name for name, cls in resolved.items() if cls is _MissingGqlError]
    if unresolved:
        logger.debug(
            "Installed gql does not define %s; the GraphQL error branches matching "
            "%s are disabled. Expected for TransportConnectionFailed on gql < 4.0; "
            "anything else suggests the adapter's class inventory is out of date.",
            ", ".join(unresolved),
            "them" if len(unresolved) > 1 else "it",
        )

    return (
        resolved["TransportError"],
        resolved["TransportQueryError"],
        resolved["TransportServerError"],
        resolved["TransportConnectionFailed"],
        resolved["TransportProtocolError"],
    )


def _extract_error_message(message: Any) -> str:
    """Return the error message or a fallback."""
    if not message:
        return "Unknown GraphQL error"
    try:
        return str(message) or "Unknown GraphQL error"
    except Exception:
        return "Unknown GraphQL error"


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
        """Handle TransportQueryError (GraphQL errors in response body)."""
        errors_list = exc.errors or []
        # A non-conforming server can put anything in `errors`. Normalize rather
        # than trust the shape: an exception raised here escapes into tool.py's
        # broad except, which disables the adapter and drops the real message —
        # the TOO-1338 failure all over again.
        if not isinstance(errors_list, list):
            errors_list = [errors_list]
        logger.debug("GraphQL query errors: %s", errors_list)

        messages = [
            _extract_error_message(e.get("message") if isinstance(e, dict) else e)
            for e in errors_list
        ]
        joined = "; ".join(messages) if messages else "Unknown GraphQL error"

        # Extract error codes and map to HTTP status
        codes: list[str] = []
        mapped_statuses: list[int] = []

        for e in errors_list:
            ext = e.get("extensions") if isinstance(e, dict) else None
            code = ext.get("code") if isinstance(ext, dict) else None
            if isinstance(code, str):
                codes.append(code)
                mapped = _GQL_CODE_TO_STATUS.get(code)
                if mapped:
                    mapped_statuses.append(mapped)

        # Highest recognized code wins (5xx over 4xx); 422 is only the fallback
        # for a response whose codes we don't recognize — using it as a floor
        # masked the more specific 401/403/404/400 codes.
        #
        # One numeric rule for every pair, including within 4xx: an auth code
        # alongside another 4xx does not out-rank it (401 + 404 reports 404).
        # Special-casing auth would raise whether it also beats 5xx, which would
        # change retryability. The single scalar loses nothing that matters —
        # every message and code is still carried in message/extra below.
        status = max(mapped_statuses) if mapped_statuses else HTTPStatus.UNPROCESSABLE_ENTITY.value

        unique_codes = sorted(set(codes))

        return UpstreamError(
            message=f"Upstream GraphQL error: {joined}",
            status_code=status,
            developer_message=f"GraphQL error codes: {', '.join(unique_codes)}"
            if unique_codes
            else "GraphQL error",
            extra={
                "service": self.slug,
                "error_type": "TransportQueryError",
                "gql_error_codes": unique_codes,
            },
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
