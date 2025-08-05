import datetime
from typing import Any

import httpx
from arcade_core.errors import (
    UpstreamAuthError,
    UpstreamBadRequestError,
    UpstreamNotFoundError,
    UpstreamRateLimitError,
    UpstreamServerError,
    UpstreamValidationError,
)

RATE_HEADERS = ("retry-after", "x-ratelimit-reset", "x-ratelimit-reset-ms")


class HTTPErrorAdapter:
    slug = "_http"

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
            return int(val) * 1_000
        # Rate limit header is an absolute date
        try:
            dt = datetime.datetime.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")
            return int((dt - datetime.datetime.now(datetime.UTC)).total_seconds() * 1_000)
        except Exception:
            return 1_000

    def _map(self, status: int, headers, msg: str):
        if status == 400:
            return UpstreamBadRequestError(message=msg, status_code=status)
        if status in (401, 403):
            return UpstreamAuthError(message=msg, status_code=status)
        if status == 404:
            return UpstreamNotFoundError(message=msg, status_code=status)
        if status == 422:
            return UpstreamValidationError(message=msg, status_code=status)
        if status == 429:
            return UpstreamRateLimitError(
                retry_after_ms=self._parse_retry_ms(headers),
                message=msg,
            )
        return UpstreamServerError(message=msg, status_code=status)

    def from_exception(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
            # TODO: Should we get the method & url from the request for the error message?
            return self._map(response.status_code, response.headers, str(exc))
        # TODO: Add support for requests library
        return None

    def from_response(self, r: Any):
        # TODO: Either update or just return None. Don't think we need this for raw HTTP?
        status = getattr(r, "status_code", None)
        headers = getattr(r, "headers", {})
        if status and status >= 400:
            return self._map(status, headers, f"HTTP {status}")
        return None
