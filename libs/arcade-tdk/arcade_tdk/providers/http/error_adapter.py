import datetime
import re
from typing import Any

import httpx

from arcade_tdk.errors import (
    NonRetryableToolError,
    UpstreamRateLimitError,
)

RATE_HEADERS = ("retry-after", "x-ratelimit-reset", "x-ratelimit-reset-ms")


def _parse_retry_ms(headers: dict[str, str]) -> int:
    val = next((headers.get(h) for h in RATE_HEADERS if headers.get(h)), None)
    if val is None:
        return 1_000
    if re.fullmatch(r"\d+", val):  # seconds (int)
        return int(val) * 1_000
    try:  # HTTP-date
        dt = datetime.datetime.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")
        return int((dt - datetime.datetime.utcnow()).total_seconds() * 1_000)
    except Exception:
        return 1_000


class HTTPErrorAdapter:
    slug = "_generic_http"

    def _map(self, status: int, headers, msg: str):
        if status == 429:
            return UpstreamRateLimitError(
                retry_after_ms=_parse_retry_ms(headers),
                message=msg,
            )
            # return UpstreamRateLimitError(_parse_retry_ms(headers), msg)
        if status in (401, 403):
            return NonRetryableToolError(message=msg, status_code=status)
            # return AuthError(msg)
        if 500 <= status < 600:
            return NonRetryableToolError(message=msg, status_code=status)
            # return TransientUpstreamError(msg)
        if 400 <= status < 500:
            return NonRetryableToolError(status_code=status, message=msg)
            # return NonRetryableError(origin="UPSTREAM", code=f"HTTP_{status}", message=msg)
        return None

    # httpx exceptions
    def from_exception(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            r = exc.response
            return self._map(r.status_code, r.headers, str(exc))
        # TODO: Add support for requests
        return None

    # raw Response objects
    def from_response(self, r: Any):
        status = getattr(r, "status_code", None)
        headers = getattr(r, "headers", {})
        if status and status >= 400:
            return self._map(status, headers, f"HTTP {status}")
        return None
