import logging
import re
from datetime import datetime, timezone
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
        self,
        request_url: str | None = None,
        request_method: str | None = None,
        error_type: str | None = None,
    ) -> dict[str, str]:
        """Build extra metadata for error reporting."""
        extra = {
            "service": HTTPErrorAdapter.slug,
        }

        if request_url:
            extra["endpoint"] = self._sanitize_uri(request_url)

        if request_method:
            extra["http_method"] = request_method.upper()

        if error_type:
            extra["error_type"] = error_type

        return extra

    def _map_status_to_error(
        self,
        status: int,
        headers: dict[str, str],
        msg: str,
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
                extra=extra,
            )

        if status == 403 and self._is_rate_limit_403(headers, msg):
            return UpstreamRateLimitError(
                retry_after_ms=self._parse_retry_ms(headers),
                message=msg,
                extra=extra,
            )

        return UpstreamError(message=msg, status_code=status, extra=extra)

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


def _request_info_from_attr(obj: Any) -> tuple[str | None, str | None]:
    """Pull ``(url, method)`` from an object that exposes ``.url`` / ``.method``."""
    if obj is None:
        return None, None
    url = getattr(obj, "url", None)
    method = getattr(obj, "method", None)
    return (str(url) if url else None, method)


def _safe_request_attr(exc: Any) -> Any:
    """Safely read ``exc.request`` without triggering httpx's ``.request`` lazy-raise.

    ``httpx.RequestError.request`` is a property that raises ``RuntimeError``
    when the request has not been attached — which happens for many transport
    errors we want to map. Fall back to ``None`` in that case.
    """
    try:
        return getattr(exc, "request", None)
    except RuntimeError:
        return None


class _HTTPXExceptionHandler:
    """Handler for httpx-specific exceptions.

    Ordering of ``isinstance`` checks matters — httpx's hierarchy is:

    - ``HTTPStatusError`` (has a real response)
    - ``RequestError``
      - ``InvalidURL`` (construction bug)
      - ``TransportError``
        - ``UnsupportedProtocol`` (construction bug)
        - ``ProtocolError``
          - ``LocalProtocolError`` (construction bug)
          - ``RemoteProtocolError`` (upstream sent malformed HTTP — unreachable)
        - ``TimeoutException`` (``ConnectTimeout`` / ``ReadTimeout`` /
          ``WriteTimeout`` / ``PoolTimeout``)
        - ``NetworkError`` (``ConnectError``, ``ReadError``, ``WriteError``,
          ``CloseError``)
        - ``ProxyError``
      - ``DecodingError``
      - ``TooManyRedirects``

    Check construction bugs before their transport-level ancestors so client
    bugs don't get swallowed by the generic transport bucket.
    """

    def handle_exception(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError | None:
        """Convert an httpx exception into the appropriate Arcade error."""
        try:
            import httpx
        except ImportError:
            return None

        # 1. Real HTTP response with a status code → UpstreamError.
        if isinstance(exc, httpx.HTTPStatusError):
            return self._handle_status_error(exc, mapper)

        # 2. Client construction bugs → FatalToolError.
        #    ``httpx.InvalidURL`` is a bare ``Exception`` (not a ``RequestError``
        #    subclass in current httpx), so it must be checked before the
        #    ``RequestError`` guard below.
        if isinstance(
            exc,
            (httpx.InvalidURL, httpx.UnsupportedProtocol, httpx.LocalProtocolError),
        ):
            request_url, request_method = _request_info_from_attr(_safe_request_attr(exc))
            return _build_construction_error(
                exc, mapper, request_url=request_url, request_method=request_method
            )

        # Everything remaining is a RequestError subclass; short-circuit if not httpx.
        if not isinstance(exc, httpx.RequestError):
            return None

        request_url, request_method = _request_info_from_attr(_safe_request_attr(exc))

        # 3. Timeouts → NetworkTransportError (TIMEOUT, retryable).
        if isinstance(exc, httpx.TimeoutException):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
                can_retry=True,
                message="HTTP request timed out before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        # 4. Transport-level reachability failures (connection, DNS, TLS handshake,
        #    proxy, RemoteProtocolError) → NetworkTransportError (UNREACHABLE).
        if isinstance(exc, httpx.TransportError):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE,
                can_retry=True,
                message="HTTP request failed before reaching the upstream service.",
                request_url=request_url,
                request_method=request_method,
            )

        # 5. Decoding failure after a (partial) response started arriving.
        if isinstance(exc, httpx.DecodingError):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP response from upstream could not be decoded.",
                request_url=request_url,
                request_method=request_method,
            )

        # 6. Redirect-loop exhaustion — not retryable (same redirect chain will loop again).
        if isinstance(exc, httpx.TooManyRedirects):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=False,
                message="HTTP redirect limit exceeded before a final response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        # 7. RequestError fallback — unknown subclass, assume transient.
        return _build_network_transport_error(
            exc,
            mapper,
            kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
            can_retry=True,
            message="HTTP request failed before a complete response was received.",
            request_url=request_url,
            request_method=request_method,
        )

    def _handle_status_error(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError:
        response = exc.response
        request = _safe_request_attr(exc)
        request_url, request_method = _request_info_from_attr(request)

        return mapper._map_status_to_error(
            response.status_code,
            dict(response.headers),
            str(exc),
            request_url=request_url,
            request_method=request_method,
        )


class _RequestsExceptionHandler:
    """Handler for requests-specific exceptions.

    Relevant parts of the ``requests`` hierarchy:

    - ``RequestException``
      - ``HTTPError`` (has a response)
      - ``ConnectionError``
        - ``ConnectTimeout`` (also ``Timeout``)
        - ``SSLError`` (cert / trust config — construction bug)
        - ``ProxyError``
      - ``Timeout``
        - ``ConnectTimeout``
        - ``ReadTimeout``
      - ``URLRequired`` / ``MissingSchema`` / ``InvalidSchema`` / ``InvalidURL``
        / ``InvalidProxyURL`` / ``InvalidHeader`` (construction bugs)
      - ``TooManyRedirects``
      - ``ContentDecodingError``

    Check SSLError before ConnectionError (it's a subclass), and check
    Timeout before ConnectionError so that ConnectTimeout — which inherits
    from both — is classified as a timeout.
    """

    def handle_exception(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError | None:
        """Convert a requests exception into the appropriate Arcade error."""
        try:
            from requests import exceptions as rexc  # type: ignore[import-untyped]
        except ImportError:
            return None

        # 1. HTTPError (with response) → UpstreamError.
        if isinstance(exc, rexc.HTTPError):
            return self._handle_http_error(exc, mapper)

        if not isinstance(exc, rexc.RequestException):
            return None

        request_url, request_method = _requests_request_info(exc)

        # 2. Construction bugs → FatalToolError.
        if isinstance(
            exc,
            (
                rexc.MissingSchema,
                rexc.InvalidSchema,
                rexc.InvalidURL,
                rexc.InvalidProxyURL,
                rexc.InvalidHeader,
                rexc.URLRequired,
            ),
        ):
            return _build_construction_error(
                exc, mapper, request_url=request_url, request_method=request_method
            )

        # 3. TLS / cert / trust failures → FatalToolError.
        #    (SSLError is a ConnectionError subclass — check before ConnectionError.)
        if isinstance(exc, rexc.SSLError):
            return _build_construction_error(
                exc,
                mapper,
                request_url=request_url,
                request_method=request_method,
                message_override=(
                    "TLS handshake failed — likely a local certificate or trust "
                    "configuration issue."
                ),
            )

        # 4. Timeouts → NetworkTransportError (TIMEOUT).
        #    (Timeout must be checked before ConnectionError: ConnectTimeout inherits
        #    from both.)
        if isinstance(exc, rexc.Timeout):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
                can_retry=True,
                message="HTTP request timed out before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        # 5. ConnectionError (non-SSL, non-Timeout) → UNREACHABLE.
        if isinstance(exc, rexc.ConnectionError):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE,
                can_retry=True,
                message="HTTP request failed before reaching the upstream service.",
                request_url=request_url,
                request_method=request_method,
            )

        # 6. Content decoding failure.
        if isinstance(exc, rexc.ContentDecodingError):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP response from upstream could not be decoded.",
                request_url=request_url,
                request_method=request_method,
            )

        # 7. Redirect-loop exhaustion — not retryable.
        if isinstance(exc, rexc.TooManyRedirects):
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=False,
                message="HTTP redirect limit exceeded before a final response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        # 8. RequestException fallback.
        return _build_network_transport_error(
            exc,
            mapper,
            kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
            can_retry=True,
            message="HTTP request failed before a complete response was received.",
            request_url=request_url,
            request_method=request_method,
        )

    def _handle_http_error(self, exc: Any, mapper: BaseHTTPErrorMapper) -> ToolRuntimeError | None:
        response = getattr(exc, "response", None)
        if response is None:
            # No response means requests gave up before getting a status code;
            # treat as a transport-level failure.
            request_url, request_method = _requests_request_info(exc)
            return _build_network_transport_error(
                exc,
                mapper,
                kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED,
                can_retry=True,
                message="HTTP request failed before a complete response was received.",
                request_url=request_url,
                request_method=request_method,
            )

        request_url = None
        request_method = None
        request = getattr(response, "request", None)
        if request is not None:
            request_url, request_method = _request_info_from_attr(request)
        if request_url is None:
            request_url = getattr(response, "url", None)

        return mapper._map_status_to_error(
            response.status_code,
            dict(response.headers),
            str(exc),
            request_url=request_url,
            request_method=request_method,
        )


def _requests_request_info(exc: Any) -> tuple[str | None, str | None]:
    """Best-effort ``(url, method)`` extraction from a requests exception."""
    request = getattr(exc, "request", None)
    if request is not None:
        return _request_info_from_attr(request)
    response = getattr(exc, "response", None)
    if response is not None:
        inner_request = getattr(response, "request", None)
        if inner_request is not None:
            return _request_info_from_attr(inner_request)
        url = getattr(response, "url", None)
        if url:
            return str(url), None
    return None, None


def _build_network_transport_error(
    exc: Exception,
    mapper: BaseHTTPErrorMapper,
    *,
    kind: ErrorKind,
    can_retry: bool,
    message: str,
    request_url: str | None,
    request_method: str | None,
) -> NetworkTransportError:
    """Construct a NetworkTransportError with consistent extras/developer_message."""
    extra = mapper._build_extra_metadata(
        request_url=request_url,
        request_method=request_method,
        error_type=type(exc).__name__,
    )
    developer_message = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    return NetworkTransportError(
        message=message,
        developer_message=developer_message,
        kind=kind,
        can_retry=can_retry,
        extra=extra,
    )


def _build_construction_error(
    exc: Exception,
    mapper: BaseHTTPErrorMapper,
    *,
    request_url: str | None,
    request_method: str | None,
    message_override: str | None = None,
) -> FatalToolError:
    """Construct a FatalToolError for client-side HTTP construction bugs.

    Returned for cases where the tool built an invalid request (bad URL,
    missing scheme, unsupported protocol, bad headers) or where local trust
    configuration prevents the request from being sent (SSL/TLS). Retrying
    won't help — the tool's code or the environment needs to change.
    """
    extra = mapper._build_extra_metadata(
        request_url=request_url,
        request_method=request_method,
        error_type=type(exc).__name__,
    )
    message = message_override or (
        "Tool constructed an invalid HTTP request — likely a tool-authoring bug."
    )
    developer_message = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    return FatalToolError(
        message=message,
        developer_message=developer_message,
        extra=extra,
    )


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
