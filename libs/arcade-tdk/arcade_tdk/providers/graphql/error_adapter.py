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


class _MissingGqlError(Exception):
    """Sentinel for a gql exception class absent on the installed gql version.

    Substituted for a class the installed gql does not define so the adapter's
    ``isinstance()`` checks stay valid but simply never match. Never raised or
    instantiated.
    """


@lru_cache(maxsize=1)
def _load_gql_transport_errors() -> (
    tuple[type[Any], type[Any], type[Any], type[Any], type[Any]] | None
):
    """Import gql transport exceptions lazily and cache the result.

    Each class is resolved with ``getattr`` and a never-raised sentinel so a gql
    version that omits one of these names degrades gracefully instead of raising
    ``AttributeError``. In particular ``TransportConnectionFailed`` was added in
    gql 4.0.0 and does NOT exist on the stable 3.5.x line (the gql stable line
    jumps 3.5.3 -> 4.0.0); consumers pinned to ``gql>=3.5,<4.0`` resolve to 3.5.3.
    Eagerly reading ``module.TransportConnectionFailed`` there raised
    ``AttributeError`` — which is not an ``ImportError``, so it escaped the guard,
    was swallowed by the adapter chain in ``tool.py``, and silently disabled the
    whole GraphQL adapter (TOO-1338). Resolving with ``getattr`` keeps every class
    the installed gql *does* define working.
    """
    try:
        module = importlib.import_module("gql.transport.exceptions")
    except ImportError:
        logger.debug("gql not installed; GraphQL adapter disabled")
        return None
    else:
        return (
            getattr(module, "TransportError", _MissingGqlError),
            getattr(module, "TransportQueryError", _MissingGqlError),
            getattr(module, "TransportServerError", _MissingGqlError),
            getattr(module, "TransportConnectionFailed", _MissingGqlError),
            getattr(module, "TransportProtocolError", _MissingGqlError),
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
        logger.debug("GraphQL query errors: %s", errors_list)

        messages = [_extract_error_message(e.get("message")) for e in errors_list]
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
                if mapped is not None:
                    mapped_statuses.append(mapped)

        # 422 (Unprocessable Entity) is only a fallback for when no recognized
        # GraphQL error code was present. When codes DID map, pick the highest
        # mapped status so a 5xx (retryable) wins over a 4xx in a multi-error
        # response. The previous code seeded `status` at 422 and only replaced it
        # when `mapped > status`, so specific 4xx codes below the 422 floor —
        # NOT_FOUND (404), FORBIDDEN (403), UNAUTHENTICATED (401), BAD_USER_INPUT
        # (400) — never won and were reported as 422 (TOO-1338, secondary bug).
        status = (
            max(mapped_statuses) if mapped_statuses else HTTPStatus.UNPROCESSABLE_ENTITY.value
        )

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
