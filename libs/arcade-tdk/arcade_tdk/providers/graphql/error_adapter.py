import importlib
import logging
from functools import lru_cache
from http import HTTPStatus
from typing import Any

from arcade_core.errors import ToolRuntimeError, UpstreamError

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

        # Network/protocol errors - simple 502
        if isinstance(exc, (TransportConnectionFailed, TransportProtocolError)):
            return UpstreamError(
                message=f"Upstream GraphQL error: {type(exc).__name__}",
                status_code=HTTPStatus.BAD_GATEWAY.value,
                developer_message=str(exc),
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
        status = HTTPStatus.UNPROCESSABLE_ENTITY.value

        for e in errors_list:
            ext = e.get("extensions") if isinstance(e, dict) else None
            code = ext.get("code") if isinstance(ext, dict) else None
            if isinstance(code, str):
                codes.append(code)
                mapped = _GQL_CODE_TO_STATUS.get(code)
                if mapped and mapped > status:
                    status = mapped

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
            msg=f"Upstream GraphQL error: {_extract_error_message(str(exc))}",
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
