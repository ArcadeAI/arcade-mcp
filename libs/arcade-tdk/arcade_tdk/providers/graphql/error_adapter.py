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
def _load_gql_transport_errors() -> tuple[type[Any], type[Any]] | None:
    """
    Import gql transport exceptions lazily and cache the result to avoid
    repeatedly attempting the import in environments where gql is missing.
    """
    try:
        module = importlib.import_module("gql.transport.exceptions")
        TransportQueryError = module.TransportQueryError
        TransportServerError = module.TransportServerError
    except ImportError:
        logger.debug(
            "'gql' transport exceptions could not be imported; GraphQL adapter disabled",
            exc_info=True,
        )
        return None

    return (TransportQueryError, TransportServerError)


def _extract_error_message(message: Any) -> str:
    """Return the raw GraphQL error message or a fallback when missing."""
    if not message:
        return "Unknown GraphQL error"
    try:
        coerced = str(message)
    except Exception:
        return "Unknown GraphQL error"
    return coerced or "Unknown GraphQL error"


class GraphQLErrorAdapter(BaseHTTPErrorMapper):
    """Error adapter for GraphQL clients (specifically 'gql' library)."""

    slug = "_graphql"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """
        Translate a GraphQL client exception into a ToolRuntimeError.
        """
        gql_exceptions = _load_gql_transport_errors()
        if not gql_exceptions:
            return None

        TransportQueryError, TransportServerError = gql_exceptions

        # Handle GraphQL Query Errors (HTTP 200 OK but contains 'errors' list)
        if isinstance(exc, TransportQueryError):
            return self._handle_query_error(exc)

        # Handle Transport Server Errors (HTTP 500s, 400s from the transport layer)
        if isinstance(exc, TransportServerError):
            return self._handle_server_error(exc)

        return None

    def _handle_query_error(self, exc: Any) -> UpstreamError:
        """Handle TransportQueryError by inspecting error codes."""
        # exc.errors is typically a list of dicts: [{'message': '...', 'extensions': {...}}]
        errors_list = exc.errors if exc.errors else []
        logger.debug("GraphQL TransportQueryError payload: %s", errors_list)
        messages = [_extract_error_message(e.get("message")) for e in errors_list] or [
            "Unknown GraphQL error"
        ]
        joined_message = "; ".join(messages)

        # Extract potential error codes and determine appropriate status code
        error_codes: list[str] = []
        status_code = HTTPStatus.UNPROCESSABLE_ENTITY.value  # Default to Unprocessable Entity

        for e in errors_list:
            extensions = e.get("extensions")
            if not isinstance(extensions, dict):
                continue

            code = extensions.get("code")
            if not isinstance(code, str):
                continue

            error_codes.append(code)
            mapped_status = _GQL_CODE_TO_STATUS.get(code)

            if mapped_status and (
                status_code == HTTPStatus.UNPROCESSABLE_ENTITY.value or mapped_status > status_code
            ):
                status_code = mapped_status

        developer_message = "GraphQL error"
        if error_codes:
            developer_message = f"GraphQL error codes: {', '.join(sorted(set(error_codes)))}"

        return UpstreamError(
            message=f"Upstream GraphQL error: {joined_message}",
            status_code=status_code,
            developer_message=developer_message,
            extra={
                "service": self.slug,
                "error_type": "TransportQueryError",
                "gql_error_count": len(errors_list),
                "gql_error_codes": error_codes,
            },
        )

    def _handle_server_error(self, exc: Any) -> UpstreamError:
        """Handle TransportServerError."""
        # Try to inspect the underlying exception for headers (aiohttp, requests, httpx)
        status = (
            exc.code
            if hasattr(exc, "code") and isinstance(exc.code, int)
            else HTTPStatus.INTERNAL_SERVER_ERROR.value
        )

        # Try to find headers if available on the exception or its cause
        headers = {}
        if hasattr(exc, "response") and hasattr(exc.response, "headers"):
            # Ensure headers are lowercase for case-insensitive lookup in base class
            headers = {k.lower(): v for k, v in exc.response.headers.items()}

        logger.debug(
            "GraphQL TransportServerError details: exc=%r code=%s header_keys=%s",
            exc,
            getattr(exc, "code", None),
            list(headers.keys()),
        )

        return self._map_status_to_error(
            status=status,
            headers=headers,
            msg=f"Upstream GraphQL transport error: {_extract_error_message(str(exc))}",
        )

    def _build_extra_metadata(
        self, request_url: str | None = None, request_method: str | None = None
    ) -> dict[str, str]:
        """Override to ensure correct service slug is used."""
        extra = super()._build_extra_metadata(request_url, request_method)
        extra["service"] = self.slug
        return extra
