import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from arcade_core.errors import (
    FatalToolError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

logger = logging.getLogger(__name__)

# Google's error text can echo request values back (e.g. "File not found: <fileId>."), so it
# never reaches the agent: the agent gets a fixed message per error class, and Google's text
# goes to developer_message.
RATE_LIMITED_MESSAGE = "Google is rate-limiting requests for this account. Retry shortly."
SERVER_ERROR_MESSAGE = (
    "Google could not complete the request because of a problem on its side. Retry shortly."
)
UNAUTHORIZED_MESSAGE = "Google rejected this account's authorization. Re-authorize and retry."
FORBIDDEN_MESSAGE = (
    "Google denied the request. This account may not have permission for the item, "
    "the authorization may be missing a required scope, "
    "or the account may have reached a usage limit. "
    "Check access to the item, or re-authorize with the required scopes."
)
NOT_FOUND_MESSAGE = (
    "Google could not find the requested item. Check the ID; "
    "if it is right, this account may not have access to the item."
)
BAD_REQUEST_MESSAGE = "Google rejected the request as invalid. Check the arguments and retry."
REFUSED_MESSAGE = (
    "Google refused the request. Check the arguments; "
    "if they are right, this account may not have access to the item."
)
UNEXPECTED_RESPONSE_MESSAGE = "Google returned a response the tool could not use."
# googleapiclient raises BatchError without a response before sending anything (too many calls,
# a media request in the batch) or while reading a batch response's part IDs. Retrying the
# same call cannot fix any of these.
BATCH_FAILED_MESSAGE = (
    "The Google batch request could not be built or read, so it was not completed. "
    "Retrying the same call will not help."
)
INVALID_JSON_MESSAGE = "Google returned a response that is not valid JSON. Retry shortly."
UNKNOWN_API_MESSAGE = "The Google API name or version the tool requested does not exist."
UNACCEPTABLE_MIME_TYPE_MESSAGE = "Google does not accept this MIME type for this operation."
MEDIA_UPLOAD_SIZE_MESSAGE = "The file is larger than Google allows for this operation."
INVALID_CHUNK_SIZE_MESSAGE = "The upload chunk size the tool set is not valid for Google."
INVALID_NOTIFICATION_MESSAGE = "The Google notification channel configuration is not valid."


def _safe_message_for_status(status_code: int) -> str:
    """Return the fixed, agent-facing message for an HTTP status from Google."""
    if status_code == 429:
        return RATE_LIMITED_MESSAGE
    if status_code >= 500:
        return SERVER_ERROR_MESSAGE
    if status_code == 401:
        return UNAUTHORIZED_MESSAGE
    if status_code == 403:
        return FORBIDDEN_MESSAGE
    if status_code == 404:
        return NOT_FOUND_MESSAGE
    if status_code == 400:
        return BAD_REQUEST_MESSAGE
    if 400 <= status_code < 500:
        return REFUSED_MESSAGE
    return UNEXPECTED_RESPONSE_MESSAGE


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

    def _build_developer_message(self, status_code: int, error: Any) -> str:
        """Collect Google's own error text for developers. It never goes to the agent."""
        reason = getattr(error, "reason", None)
        reason_text = str(reason).strip() if reason else ""
        developer_message = f"Google API error (HTTP {status_code})"
        if reason_text:
            developer_message += f": {reason_text}"

        details = getattr(error, "error_details", None)
        # A body with only `error.message` makes googleapiclient copy that message into
        # error_details as well, so skip details that only repeat the reason.
        if details and not (isinstance(details, str) and details.strip() == reason_text):
            developer_message += f" - Details: {details}"

        return developer_message

    def _map_http_error(
        self, error: Any, status_code: int | None = None
    ) -> ToolRuntimeError | None:
        """Map Google HttpError to appropriate ToolRuntimeError."""
        if status_code is None:
            status_code = error.status_code

        message = _safe_message_for_status(status_code)
        developer_message = self._build_developer_message(status_code, error)

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
        # BatchError subclasses HttpError but skips its __init__ (no error_details, and resp
        # may be None), so it must be matched first.
        if isinstance(exc, errors_module.BatchError):
            status = getattr(getattr(exc, "resp", None), "status", None)
            if isinstance(status, int):
                return self._map_http_error(exc, status_code=status)

            # No response: the request was never sent, or its batch response could not be
            # read. Not something Google refused, and not fixed by a retry.
            reason = getattr(exc, "reason", None)
            return FatalToolError(
                message=BATCH_FAILED_MESSAGE,
                developer_message=f"Google API batch operation failed: {reason}",
                extra={
                    "service": self.slug,
                    "error_type": "BatchError",
                },
            )

        if isinstance(exc, errors_module.HttpError):
            return self._map_http_error(exc)

        return None

    def _handle_other_errors(self, exc: Exception, errors_module: Any) -> ToolRuntimeError | None:
        """Handle non-HTTP Google API errors."""
        if isinstance(exc, errors_module.InvalidJsonError):
            return UpstreamError(
                message=INVALID_JSON_MESSAGE,
                status_code=502,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "InvalidJsonError",
                },
            )

        if isinstance(exc, errors_module.UnknownApiNameOrVersion):
            return UpstreamError(
                message=UNKNOWN_API_MESSAGE,
                status_code=404,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "UnknownApiNameOrVersion",
                },
            )

        if isinstance(exc, errors_module.UnacceptableMimeTypeError):
            return UpstreamError(
                message=UNACCEPTABLE_MIME_TYPE_MESSAGE,
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "UnacceptableMimeTypeError",
                },
            )

        if isinstance(exc, errors_module.MediaUploadSizeError):
            return UpstreamError(
                message=MEDIA_UPLOAD_SIZE_MESSAGE,
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": "MediaUploadSizeError",
                },
            )

        if isinstance(exc, errors_module.InvalidChunkSizeError):
            return UpstreamError(
                message=INVALID_CHUNK_SIZE_MESSAGE,
                developer_message=str(exc),
                status_code=400,
                extra={
                    "service": self.slug,
                    "error_type": "InvalidChunkSizeError",
                },
            )

        if isinstance(exc, errors_module.InvalidNotificationError):
            return UpstreamError(
                message=INVALID_NOTIFICATION_MESSAGE,
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
                message=f"Google API client error: unhandled {exc.__class__.__name__}.",
                developer_message=str(exc),
                status_code=500,
                extra={
                    "service": self.slug,
                    "error_type": exc.__class__.__name__,
                },
            )

        # Not a Google API client error
        return None
