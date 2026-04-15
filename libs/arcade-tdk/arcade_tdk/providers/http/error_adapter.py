import logging
import re
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from arcade_core.errors import (
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

_NUMERIC_HEADER_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")

logger = logging.getLogger(__name__)

RATE_HEADERS = ("retry-after", "x-ratelimit-reset", "x-ratelimit-reset-ms")


class BaseHTTPErrorMapper:
    """Base class for HTTP error mapping functionality."""

    def _status_class_label(self, status: int) -> str:
        if 400 <= status < 500:
            return "client error"
        if 500 <= status < 600:
            return "server error"
        if 300 <= status < 400:
            return "redirection"
        if 100 <= status < 200:
            return "informational"
        return "response"

    def _status_phrase(self, status: int) -> str:
        try:
            return HTTPStatus(status).phrase
        except ValueError:
            return "Unknown Status"

    def _build_safe_status_message(self, status: int, headers: dict[str, str]) -> str:
        phrase = self._status_phrase(status)
        status_class = self._status_class_label(status)
        base_message = f"Upstream HTTP request failed ({status} {phrase}, {status_class})."

        if status == 429 or (status == 403 and self._is_rate_limit_403(headers, base_message)):
            retry_after_ms = self._parse_retry_ms(headers)
            retry_after_seconds = retry_after_ms // 1000
            if retry_after_seconds > 0:
                return f"{base_message} Retry after {retry_after_seconds} second(s)."
            return f"{base_message} Rate limit encountered."

        return base_message

    def _parse_numeric_header(self, value: str | None) -> float | None:
        """Convert numeric header values to float without relying on exceptions."""

        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            return None

        if _NUMERIC_HEADER_PATTERN.fullmatch(stripped):
            return float(stripped)

        return None

    def _parse_retry_ms(self, headers: dict[str, str]) -> int:
        """
        Parses a rate limit header and returns the number
        of milliseconds until the rate limit resets.

        Args:
            headers: A dictionary of HTTP headers.

        Returns:
            The number of milliseconds until the rate limit resets.
            Defaults to 1000ms if a rate limit header is not found or cannot be parsed.
        """
        val = next((headers.get(h) for h in RATE_HEADERS if headers.get(h)), None)
        # No rate limit header found
        if val is None:
            return 1_000
        # Rate limit header is a number of seconds
        if val.isdigit():
            key = next((h for h in RATE_HEADERS if headers.get(h) == val), "")
            if key.endswith("ms"):
                return int(val)
            return int(val) * 1_000
        # Rate limit header is an absolute date
        try:
            dt = datetime.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")
            return int((dt - datetime.now(timezone.utc)).total_seconds() * 1_000)
        except Exception:
            logger.warning(f"Failed to parse rate limit header: {val}. Defaulting to 1000ms.")
            return 1_000

    def _sanitize_uri(self, uri: str) -> str:
        """Strip query params and fragments from URI for privacy."""

        parsed = urlparse(uri)
        return f"{parsed.scheme}://{parsed.netloc.strip('/')}/{parsed.path.strip('/')}"

    def _build_extra_metadata(
        self, request_url: str | None = None, request_method: str | None = None
    ) -> dict[str, str]:
        """Build extra metadata for error reporting."""
        extra = {
            "service": HTTPErrorAdapter.slug,
        }

        if request_url:
            extra["endpoint"] = self._sanitize_uri(request_url)

        if request_method:
            extra["http_method"] = request_method.upper()

        return extra

    def _map_status_to_error(
        self,
        status: int,
        headers: dict[str, str],
        msg: str,
        developer_message: str | None = None,
        request_url: str | None = None,
        request_method: str | None = None,
    ) -> UpstreamError:
        """Map HTTP status code to appropriate Arcade error."""
        extra = self._build_extra_metadata(request_url, request_method)

        # Special case for rate limiting
        if status == 429:
            return UpstreamRateLimitError(
                retry_after_ms=self._parse_retry_ms(headers),
                message=msg,
                developer_message=developer_message,
                extra=extra,
            )

        if status == 403 and self._is_rate_limit_403(headers, msg):
            return UpstreamRateLimitError(
                retry_after_ms=self._parse_retry_ms(headers),
                message=msg,
                developer_message=developer_message,
                extra=extra,
            )

        return UpstreamError(
            message=msg,
            status_code=status,
            developer_message=developer_message,
            extra=extra,
        )

    def _is_rate_limit_403(self, headers: dict[str, str], msg: str) -> bool:
        """
        Determine if a 403 error is actually a rate limiting error.

        Checks if rate limit quota is exhausted. Simply having rate limit headers
        is not sufficient since some services include them in all responses.

        Args:
            headers: HTTP response headers
            msg: Error message (unused, kept for compatibility)

        Returns:
            True if this 403 should be treated as rate limiting
        """
        # Check if rate limit is actually exhausted (remaining requests is 0)
        # Support common header variations used by different APIs
        headers_lower = {k.lower(): v for k, v in headers.items()}
        remaining_header_names = [
            "x-ratelimit-remaining",
            "x-rate-limit-remaining",
            "ratelimit-remaining",
            "x-app-rate-limit-remaining",
        ]

        # Check if remaining quota is 0
        for header_name in remaining_header_names:
            remaining_value = self._parse_numeric_header(headers_lower.get(header_name))
            if remaining_value is not None and remaining_value == 0:
                return True

        # Check if retry-after is present with a meaningful value along with rate limit headers
        # This combination often indicates rate limiting even if remaining isn't explicitly 0
        retry_after = headers_lower.get("retry-after")
        has_meaningful_retry_after = False
        if retry_after:
            retry_after_value = self._parse_numeric_header(retry_after)
            if retry_after_value is not None:
                has_meaningful_retry_after = retry_after_value > 0
            else:
                # Non-numeric retry-after values (e.g., HTTP dates) indicate rate limiting windows
                has_meaningful_retry_after = True

        has_rate_limit_headers = any(
            header_name in headers_lower
            for header_name in [
                "x-ratelimit-limit",
                "x-rate-limit-limit",
                "ratelimit-limit",
            ]
        )
        return bool(has_meaningful_retry_after and has_rate_limit_headers)


class _HTTPXExceptionHandler:
    """Handler for httpx-specific exceptions."""

    def _build_upstream_error(
        self,
        *,
        mapper: BaseHTTPErrorMapper,
        exc: Exception,
        status_code: int,
        message: str,
        request_url: str | None,
        request_method: str | None,
    ) -> UpstreamError:
        return UpstreamError(
            message=message,
            status_code=status_code,
            developer_message=str(exc),
            extra={
                **mapper._build_extra_metadata(request_url, request_method),
                "error_type": type(exc).__name__,
            },
        )

    def handle_exception(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError | None:
        """Handle typed httpx exceptions.

        Args:
            exc: An httpx exception instance
            mapper: The BaseHTTPErrorMapper instance to use for mapping

        Returns:
            An Arcade error instance or None if not an httpx exception
        """
        # Lazy import httpx types locally to avoid import errors for toolkits that don't use httpx
        try:
            import httpx
        except ImportError:
            return None

        request_url = None
        request_method = None
        request = getattr(exc, "request", None)
        if request is not None:
            request_url_obj = getattr(request, "url", None)
            if request_url_obj is not None:
                request_url = str(request_url_obj)
            request_method_obj = getattr(request, "method", None)
            if request_method_obj is not None:
                request_method = str(request_method_obj)

        if isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
            safe_message = mapper._build_safe_status_message(
                response.status_code, dict(response.headers)
            )
            return mapper._map_status_to_error(
                response.status_code,
                dict(response.headers),
                safe_message,
                developer_message=str(exc),
                request_url=request_url,
                request_method=request_method,
            )

        # Order is intentional: specific subclasses before broad base classes.
        if isinstance(exc, httpx.TimeoutException):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=504,
                message=f"Upstream HTTP timeout: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.TooManyRedirects):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=400,
                message=f"Upstream HTTP request redirect limit exceeded: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, (httpx.UnsupportedProtocol, httpx.LocalProtocolError)):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=400,
                message=f"Upstream HTTP request is invalid: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.DecodingError):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=502,
                message=f"Upstream HTTP response decoding failed: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.TransportError):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=503,
                message=f"Upstream HTTP transport error: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.RequestError):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=502,
                message=f"Upstream HTTP request failed: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        return None


class _RequestsExceptionHandler:
    """Handler for requests-specific exceptions."""

    def _build_upstream_error(
        self,
        *,
        mapper: BaseHTTPErrorMapper,
        exc: Exception,
        status_code: int,
        message: str,
        request_url: str | None,
        request_method: str | None,
    ) -> UpstreamError:
        return UpstreamError(
            message=message,
            status_code=status_code,
            developer_message=str(exc),
            extra={
                **mapper._build_extra_metadata(request_url, request_method),
                "error_type": type(exc).__name__,
            },
        )

    def handle_exception(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError | None:
        """Handle requests exceptions with HTTP responses.

        Args:
            exc: A requests exception candidate
            mapper: The BaseHTTPErrorMapper instance to use for mapping

        Returns:
            An Arcade error instance or None if not a requests exception
        """
        # Lazy import requests types locally to avoid import errors for toolkits that don't use requests
        try:
            from requests.exceptions import (  # type: ignore[import-untyped]
                ConnectionError,
                ContentDecodingError,
                HTTPError,
                InvalidProxyURL,
                InvalidSchema,
                InvalidURL,
                RequestException,
                Timeout,
                TooManyRedirects,
            )
        except ImportError:
            return None

        request_url = None
        request_method = None
        request = getattr(exc, "request", None)
        if request is not None:
            request_url_obj = getattr(request, "url", None)
            if request_url_obj is not None:
                request_url = str(request_url_obj)
            request_method_obj = getattr(request, "method", None)
            if request_method_obj is not None:
                request_method = str(request_method_obj)

        if isinstance(exc, HTTPError):
            response = getattr(exc, "response", None)
            if response is None:
                return None

            # Extract request information from HTTP response if available
            if hasattr(response, "request") and response.request:
                request_url = response.request.url
                request_method = response.request.method
            elif hasattr(response, "url"):
                request_url = response.url

            safe_message = mapper._build_safe_status_message(
                response.status_code, dict(response.headers)
            )
            return mapper._map_status_to_error(
                response.status_code,
                dict(response.headers),
                safe_message,
                developer_message=str(exc),
                request_url=request_url,
                request_method=request_method,
            )

        # Order is intentional: specific subclasses before broad base classes.
        if isinstance(exc, Timeout):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=504,
                message=f"Upstream HTTP timeout: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, TooManyRedirects):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=400,
                message=f"Upstream HTTP request redirect limit exceeded: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, (InvalidURL, InvalidSchema, InvalidProxyURL)):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=400,
                message=f"Upstream HTTP request is invalid: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, ContentDecodingError):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=502,
                message=f"Upstream HTTP response decoding failed: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, ConnectionError):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=503,
                message=f"Upstream HTTP transport error: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, RequestException):
            return self._build_upstream_error(
                mapper=mapper,
                exc=exc,
                status_code=502,
                message=f"Upstream HTTP request failed: {type(exc).__name__}",
                request_url=request_url,
                request_method=request_method,
            )

        return None


class HTTPErrorAdapter(BaseHTTPErrorMapper):
    """Main HTTP error adapter that supports multiple HTTP libraries."""

    slug = "_http"

    def __init__(self) -> None:
        self._httpx_handler = _HTTPXExceptionHandler()
        self._requests_handler = _RequestsExceptionHandler()

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """Convert HTTP library exceptions into Arcade errors."""

        httpx_result = self._httpx_handler.handle_exception(exc, self)
        if httpx_result is not None:
            return httpx_result

        requests_result = self._requests_handler.handle_exception(exc, self)
        if requests_result is not None:
            return requests_result

        logger.info(
            f"Exception type '{type(exc).__name__}' was not handled by the '{self.slug}' adapter. "
            f"Either the exception is not from a supported HTTP library (httpx, requests) or "
            f"the required library is not installed in the toolkit's environment."
        )
        return None
