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
        # Lazy import the Microsoft Graph SDK to avoid import errors for toolkits that don't use msgraph-sdk
        try:
            import msgraph
        except ImportError:
            logger.info(
                f"'msgraph-sdk' is not installed in the toolkit's environment, "
                f"so the '{self.slug}' adapter was not used to handle the upstream error"
            )
            return None

        # Try API errors first
        result = self._handle_api_errors(exc, msgraph)
        if result:
            return result

        # Failsafe for any unhandled Microsoft Graph SDK errors that are not mapped above
        if hasattr(exc, "__module__") and exc.__module__ and exc.__module__.startswith("msgraph"):
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

    def _parse_retry_after(self, error: Any) -> int:
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
        user_message = f"Upstream Microsoft Graph API error: {error.error.message}"

        developer_message = f"Microsoft Graph error code: {error.error.code}"

        if error.error.inner_error:
            inner_error = error.error.inner_error
            inner_details = []

            if inner_error.code:
                inner_details.append(f"code: {inner_error.code}")
            if getattr(inner_error, "request-id", None):
                inner_details.append(f"request-id: {getattr(inner_error, 'request-id')}")
            if inner_error.date:
                inner_details.append(f"date: {inner_error.date}")

            if inner_details:
                inner_error_str = ", ".join(inner_details)
                developer_message += f" - Inner error: {inner_error_str}"

        return user_message, developer_message

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

        extra["error_code"] = error.error.code

        # Special case for rate limiting (429) and quota exceeded (503 with specific error codes)
        if status_code == 429 or (
            status_code == 503 and error.error.code in ["TooManyRequests", "ServiceUnavailable"]
        ):
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

    def _handle_api_errors(self, exc: Exception, msgraph_module: Any) -> ToolRuntimeError | None:
        """Handle APIError and its subclasses."""
        # Since msgraph-sdk uses Kiota's APIError, we need to check by class name
        # as we can't directly import the APIError class
        if exc.__class__.__name__ == "APIError":
            return self._map_api_error(exc)
        return None
