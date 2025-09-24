import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from arcade_core.errors import (
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

logger = logging.getLogger(__name__)


class GoogleErrorAdapter:
    """Error adapter for Google's API Python Client library."""

    slug = "_google_api_client"

    def _sanitize_uri(self, uri: str) -> str:
        """Strip query params and fragments from URI for privacy."""

        parsed = urlparse(uri)
        return f"{parsed.scheme}://{parsed.netloc.strip('/')}/{parsed.path.strip('/')}"

    def _parse_retry_after(self, error: Any) -> int:
        """
        Extract retry-after from Google API errors.
        Returns milliseconds to wait before retry.
        Defaults to 1000ms if not found.

        Args:
            error: The Google client error to parse

        Returns:
            The number of milliseconds to wait before retry
        """
        if hasattr(error, "resp") and hasattr(error.resp, "headers"):
            headers = error.resp.headers

            retry_after = headers.get("Retry-After", headers.get("retry-after"))
            if retry_after:
                try:
                    # If it's a number, it's seconds
                    if retry_after.isdigit():
                        return int(retry_after) * 1000
                    # Otherwise try to parse as date
                    dt = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S %Z")
                    return int((dt - datetime.now(timezone.utc)).total_seconds() * 1000)
                except Exception:
                    # TODO: Log?
                    return 1000

        return 1000

    def _map_http_error(self, error: Any) -> ToolRuntimeError | None:
        """Map Google HttpError to appropriate ToolRuntimeError."""
        status_code = error.status_code
        reason = str(error.reason) if error.reason else f"HTTP {status_code} error"

        message = f"Upstream Google API error: {reason}"

        developer_message = None
        if error.error_details:
            # str error details are added to the message
            if isinstance(error.error_details, str):
                message = f"{message} - Details: {error.error_details}"
            else:
                # structured error details are added to the developer message
                developer_message = f"Upstream Google API error details: {error.error_details}"

        # Build extra metadata
        extra = {
            "service": self.slug,
        }

        # Try to extract request details if available
        if hasattr(error, "uri") and error.uri:
            extra["endpoint"] = self._sanitize_uri(error.uri)
        if hasattr(error, "method_") and error.method_:
            extra["http_method"] = error.method_.upper()

        # Special case for rate limiting
        if status_code == 429:
            return UpstreamRateLimitError(
                retry_after_ms=self._parse_retry_after(error),
                message=message,
                developer_message=developer_message,
                extra=extra,
            )

        return UpstreamError(
            message=message,
            status_code=status_code,
            developer_message=developer_message,
            extra=extra,
        )

    def _handle_http_errors(self, exc: Exception, errors_module: Any) -> ToolRuntimeError | None:
        """Handle HttpError and its subclasses."""
        if isinstance(exc, errors_module.HttpError):
            return self._map_http_error(exc)

        if isinstance(exc, errors_module.BatchError):
            # BatchError might not have status_code, so handle carefully
            if hasattr(exc, "resp") and hasattr(exc.resp, "status"):
                exc.status_code = exc.resp.status
                return self._map_http_error(exc)
            else:
                # No status code available, treat as server error
                extra = {
                    "service": "google_api",
                    "error_type": "BatchError",
                }
                return UpstreamError(
                    message=f"Upstream Google API batch operation failed: {exc.reason}",
                    status_code=500,
                    extra=extra,
                )
        return None

    def _handle_other_errors(self, exc: Exception, errors_module: Any) -> ToolRuntimeError | None:
        """Handle non-HTTP Google API errors."""
        if isinstance(exc, errors_module.InvalidJsonError):
            return UpstreamError(
                message="Upstream Google API returned invalid JSON response",
                status_code=502,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "InvalidJsonError",
                },
            )

        if isinstance(exc, errors_module.UnknownApiNameOrVersion):
            return UpstreamError(
                message="Upstream Google API error: Unknown API name or version",
                status_code=404,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "UnknownApiNameOrVersion",
                },
            )

        if isinstance(exc, errors_module.UnacceptableMimeTypeError):
            return UpstreamError(
                message="Upstream Google API error: Unacceptable MIME type for this operation",
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "UnacceptableMimeTypeError",
                },
            )

        if isinstance(exc, errors_module.MediaUploadSizeError):
            return UpstreamError(
                message="Upstream Google API error: Media file size exceeds allowed limit",
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "MediaUploadSizeError",
                },
            )

        if isinstance(exc, errors_module.InvalidChunkSizeError):
            return UpstreamError(
                message="Upstream Google API error: Invalid chunk size specified",
                developer_message=str(exc),
                status_code=400,
                extra={
                    "service": self.slug,
                    "error_type": "InvalidChunkSizeError",
                },
            )

        if isinstance(exc, errors_module.InvalidNotificationError):
            return UpstreamError(
                message="Upstream Google API error: Invalid notification configuration",
                developer_message=str(exc),
                status_code=400,
                extra={
                    "service": self.slug,
                    "error_type": "InvalidNotificationError",
                },
            )

        return None

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """
        Translate a Google API client exception into a ToolRuntimeError.
        """
        # Lazy import the Google API client errors module to avoid import errors for toolkits that don't use googleapiclient
        try:
            from googleapiclient import errors
        except ImportError:
            logger.info(
                f"'googleapiclient' is not installed in the toolkit's environment, "
                f"so the '{self.slug}' adapter was not used to handle the upstream error"
            )
            return None

        # Try HTTP errors first
        result = self._handle_http_errors(exc, errors)
        if result:
            return result

        # Then try other error types
        result = self._handle_other_errors(exc, errors)
        if result:
            return result

        # Failsafe for any unhandled Google API client errors that are not mapped above
        if hasattr(exc, "__module__") and exc.__module__ == "googleapiclient.errors":
            logger.warning(
                "Unknown Google API client error encountered: %r. "
                "Falling back to generic UpstreamError.",
                exc,
                exc_info=True,
            )
            return UpstreamError(
                message=f"Upstream Google API error: {exc}",
                status_code=500,
                extra={
                    "service": self.slug,
                    "error_type": exc.__class__.__name__,
                },
            )

        # Not a Google API client error
        return None
