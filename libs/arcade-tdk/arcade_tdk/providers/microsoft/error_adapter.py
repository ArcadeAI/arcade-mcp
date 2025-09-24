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


class MicrosoftGraphErrorAdapter:
    """Error adapter for Microsoft Graph SDK (msgraph-sdk)."""

    slug = "_microsoft_graph"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """
        Translate a Microsoft Graph SDK exception into a ToolRuntimeError.
        """
        # Lazy import kiota abstractions to avoid import errors for toolkits that don't use msgraph-sdk
        try:
            from kiota_abstractions import api_error
        except ImportError:
            logger.info(
                f"'kiota-abstractions' is not installed in the toolkit's environment, "
                f"so the '{self.slug}' adapter was not used to handle the upstream error"
            )
            return None

        # Try API errors first
        result = self._handle_api_errors(exc, api_error)
        if result:
            return result

        # Failsafe for any unhandled Microsoft Graph SDK errors that are not mapped above
        if (
            hasattr(exc, "__module__")
            and exc.__module__
            and ("msgraph" in exc.__module__ or "kiota" in exc.__module__)
        ):
            logger.warning(
                "Unknown Microsoft Graph SDK error encountered: %r. "
                "Falling back to generic UpstreamError.",
                exc,
                exc_info=True,
            )
            return UpstreamError(
                message=f"Upstream Microsoft Graph error: {exc}",
                status_code=500,
                extra={
                    "service": self.slug,
                    "error_type": exc.__class__.__name__,
                },
            )

        # Not a Microsoft Graph SDK error
        return None

    def _sanitize_uri(self, uri: str) -> str:
        """Strip query params and fragments from URI for privacy."""
        parsed = urlparse(uri)
        return f"{parsed.scheme}://{parsed.netloc.strip('/')}/{parsed.path.strip('/')}"

    def _get_retry_after_milliseconds(self, error: Any) -> int:
        """
        Extract retry-after from Microsoft Graph API errors.
        Returns milliseconds to wait before retry.
        Defaults to 1000ms if not found.

        Args:
            error: The APIError to parse

        Returns:
            The number of milliseconds to wait before retry
        """
        if hasattr(error, "response") and hasattr(error.response, "headers"):
            headers = error.response.headers

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
                    logger.warning(
                        f"Failed to parse retry-after header: {retry_after}. Defaulting to 1000ms."
                    )
                    return 1000

        return 1000

    def _extract_error_details(self, error: Any) -> tuple[str, str | None]:
        """
        Extract error message and developer details from Microsoft Graph APIError.

        Microsoft Graph errors always have this structure:
        {
          "error": {
            "code": "string",
            "message": "string",
            "innerError": {
              "code": "string",
              "request-id": "string",
              "date": "string"
            }
          }
        }

        Args:
            error: The APIError to extract details from

        Returns:
            Tuple of (user_message, developer_message)
        """
        message = "Unknown Microsoft Graph error"
        code = "UnknownError"
        inner_error = None

        # Extract error details
        if hasattr(error, "error") and error.error:
            if hasattr(error.error, "message"):
                message = error.error.message or message
            if hasattr(error.error, "code"):
                code = error.error.code or code
            if hasattr(error.error, "inner_error"):
                inner_error = error.error.inner_error

        user_message = f"Upstream Microsoft Graph API error: {message}"
        developer_message = f"Microsoft Graph error code: {code}"

        # Add inner error details if present
        if inner_error:
            inner_error_details = self._format_inner_error_details(inner_error)
            if inner_error_details:
                developer_message += f" - Inner error: {inner_error_details}"

        return user_message, developer_message

    def _format_inner_error_details(self, inner_error: Any) -> str:
        """Format inner error details into a readable string."""
        inner_details = []

        if hasattr(inner_error, "code") and inner_error.code:
            inner_details.append(f"code: {inner_error.code}")
        if getattr(inner_error, "request-id", None):
            inner_details.append(f"request-id: {getattr(inner_error, 'request-id')}")
        elif hasattr(inner_error, "request_id") and inner_error.request_id:
            inner_details.append(f"request-id: {inner_error.request_id}")
        if hasattr(inner_error, "client_request_id") and inner_error.client_request_id:
            inner_details.append(f"client-request-id: {inner_error.client_request_id}")
        if hasattr(inner_error, "date") and inner_error.date:
            inner_details.append(f"date: {inner_error.date}")

        return ", ".join(inner_details)

    def _map_api_error(self, error: Any) -> ToolRuntimeError | None:
        """Map Microsoft Graph APIError to appropriate ToolRuntimeError."""

        status_code = 500  # Default to server error
        if hasattr(error, "response") and error.response and hasattr(error.response, "status_code"):
            status_code = error.response.status_code
        elif hasattr(error, "response_status_code") and isinstance(
            getattr(error, "response_status_code", None), int
        ):
            status_code = error.response_status_code

        message, developer_message = self._extract_error_details(error)

        extra = {
            "service": self.slug,
        }

        # Try to extract request details if available
        if (
            hasattr(error, "response")
            and error.response
            and hasattr(error.response, "url")
            and error.response.url
        ):
            extra["endpoint"] = self._sanitize_uri(str(error.response.url))

        error_code = "UnknownError"
        if hasattr(error, "error") and error.error and hasattr(error.error, "code"):
            error_code = error.error.code
        extra["error_code"] = error_code

        # Special case for rate limiting (429) and quota exceeded (503 with specific error codes)
        if status_code == 429 or (
            status_code == 503 and error_code in ["TooManyRequests", "ServiceUnavailable"]
        ):
            return UpstreamRateLimitError(
                retry_after_ms=self._get_retry_after_milliseconds(error),
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

    def _handle_api_errors(self, exc: Exception, api_error_module: Any) -> ToolRuntimeError | None:
        """Handle APIError and its subclasses."""
        if isinstance(exc, api_error_module.APIError):
            return self._map_api_error(exc)
        return None
