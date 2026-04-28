import logging
import re
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from arcade_core.errors import (
    ErrorKind,
    FatalToolError,
    NetworkTransportError,
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
        base_message = f"Upstream HTTP request failed ({phrase}, {status_class})."

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

    def _build_network_transport_error(
        self,
        *,
        exc: Exception,
        kind: ErrorKind,
        can_retry: bool,
        message: str,
        request_url: str | None,
        request_method: str | None,
    ) -> NetworkTransportError:
        """Build a NetworkTransportError for no-response HTTP failures.

        Used for transport-level failures (timeouts, connection errors, decoding
        failures, redirect-loop exhaustion) where no complete HTTP response was
        received from the upstream service.
        """
        return NetworkTransportError(
            message=message,
            developer_message=str(exc),
            kind=kind,
            can_retry=can_retry,
            extra={
                **self._build_extra_metadata(request_url, request_method),
                "error_type": type(exc).__name__,
            },
        )

    def _build_construction_error(
        self,
        *,
        exc: Exception,
        message: str,
        request_url: str | None,
        request_method: str | None,
    ) -> FatalToolError:
        """Build a FatalToolError for client-side HTTP construction bugs.

        Used for exceptions that indicate the tool built an invalid request
        (bad URL, unsupported scheme, malformed headers) or local trust
        configuration prevents the request from being sent (TLS/SSL).
        Retrying will not help — the tool's code or environment must change.
        """
        return FatalToolError(
            message=message,
            developer_message=str(exc),
            extra={
                **self._build_extra_metadata(request_url, request_method),
                "error_type": type(exc).__name__,
            },
        )

    @staticmethod
    def _extract_request_info(exc: Any) -> tuple[str | None, str | None]:
        """Pull ``(url, method)`` from an exception, trying in order:

        1. ``exc.request.{url,method}`` — present on requests and httpx
           exceptions when a Request was built and attached.
        2. ``exc.response.request.{url,method}`` — set on response-bearing
           exceptions like ``requests.HTTPError``.
        3. ``exc.response.url`` — final fallback for URL only (no method).

        Guards each access because ``httpx.RequestError.request`` raises
        ``RuntimeError`` when no request is attached, and arbitrary mocks
        may omit attributes entirely.
        """

        def _safe_get(obj: Any, name: str) -> Any:
            try:
                return getattr(obj, name, None)
            except RuntimeError:
                return None

        def _as_str(value: Any) -> str | None:
            return str(value) if value is not None else None

        url: str | None = None
        method: str | None = None
        for source in (_safe_get(exc, "request"), _safe_get(_safe_get(exc, "response"), "request")):
            if source is None:
                continue
            url = url or _as_str(_safe_get(source, "url"))
            method = method or _as_str(_safe_get(source, "method"))
            if url and method:
                break
        if url is None:
            url = _as_str(_safe_get(_safe_get(exc, "response"), "url"))
        return url, method

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

        request_url, request_method = mapper._extract_request_info(exc)

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

        # Construction bugs — per-exception messages so the agent can tell
        # the failures apart without reading developer_message. Checked before
        # transport base classes, and before the RequestError guard because
        # ``httpx.InvalidURL`` is a bare ``Exception`` (not a RequestError
        # subclass in current httpx).
        if isinstance(exc, httpx.InvalidURL):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request URL is invalid or malformed.",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, httpx.UnsupportedProtocol):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request URL uses an unsupported scheme (expected http or https).",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, httpx.LocalProtocolError):
            return mapper._build_construction_error(
                exc=exc,
                message=(
                    "HTTP request violated the HTTP protocol before it was sent "
                    "(malformed headers or body)."
                ),
                request_url=request_url,
                request_method=request_method,
            )

        # Order is intentional: specific subclasses before broad base classes.
        if isinstance(exc, httpx.TimeoutException):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
                can_retry=True,
                message="HTTP request timed out before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.TooManyRedirects):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=False,
                message="HTTP redirect limit exceeded before a final response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.DecodingError):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP response from upstream could not be decoded.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.TransportError):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE,
                can_retry=True,
                message="HTTP request failed before reaching the upstream service.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, httpx.RequestError):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP request failed before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        return None


class _RequestsExceptionHandler:
    """Handler for requests-specific exceptions."""

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
                InvalidSchema,
                InvalidURL,
                MissingSchema,
                RequestException,
                SSLError,
                Timeout,
                TooManyRedirects,
                URLRequired,
            )
        except ImportError:
            return None

        # Resolve version-gated exception classes separately so an older
        # ``requests`` install that is missing one of them doesn't silently
        # disable the entire requests adapter chain. Missing classes are
        # replaced with a sentinel that no real exception is an instance of,
        # turning the downstream ``isinstance()`` check into a no-op.
        #   - ``InvalidProxyURL``: added in requests 2.21.0 (Dec 2018).
        #   - ``InvalidHeader``:   added in requests 2.12.0 (Nov 2016).
        class _UnavailableRequestsException(Exception):
            """Placeholder for a requests.exceptions class missing on this install."""

        try:
            from requests.exceptions import InvalidProxyURL
        except ImportError:
            InvalidProxyURL = _UnavailableRequestsException

        try:
            from requests.exceptions import InvalidHeader
        except ImportError:
            InvalidHeader = _UnavailableRequestsException

        request_url, request_method = mapper._extract_request_info(exc)

        if isinstance(exc, HTTPError):
            response = getattr(exc, "response", None)
            if response is None:
                return None

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

        # Construction bugs — per-exception messages so each failure mode is
        # distinguishable in the agent-facing message without reading
        # developer_message.
        if isinstance(exc, MissingSchema):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request URL is missing a scheme (expected http:// or https://).",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, InvalidSchema):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request URL uses an unsupported scheme (expected http or https).",
                request_url=request_url,
                request_method=request_method,
            )
        # InvalidProxyURL is a subclass of InvalidURL — check proxy first.
        if isinstance(exc, InvalidProxyURL):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP proxy URL is invalid or malformed.",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, InvalidURL):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request URL is invalid or malformed.",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, InvalidHeader):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request contains an invalid header name or value.",
                request_url=request_url,
                request_method=request_method,
            )
        if isinstance(exc, URLRequired):
            return mapper._build_construction_error(
                exc=exc,
                message="HTTP request requires a URL but none was provided.",
                request_url=request_url,
                request_method=request_method,
            )

        # TLS / cert / trust failures — typically a local configuration issue.
        # (SSLError is a ConnectionError subclass, so it must be checked first.)
        if isinstance(exc, SSLError):
            return mapper._build_construction_error(
                exc=exc,
                message=(
                    "TLS handshake failed — likely a local certificate or trust "
                    "configuration issue."
                ),
                request_url=request_url,
                request_method=request_method,
            )

        # Order is intentional: specific subclasses before broad base classes.
        # ``ConnectTimeout`` inherits from BOTH ``Timeout`` and ``ConnectionError`` —
        # check ``Timeout`` first so it's classified as a timeout.
        if isinstance(exc, Timeout):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
                can_retry=True,
                message="HTTP request timed out before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, ConnectionError):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE,
                can_retry=True,
                message="HTTP request failed before reaching the upstream service.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, ContentDecodingError):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP response from upstream could not be decoded.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, TooManyRedirects):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=False,
                message="HTTP redirect limit exceeded before a final response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        if isinstance(exc, RequestException):
            return mapper._build_network_transport_error(
                exc=exc,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP request failed before a complete response was received.",
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
