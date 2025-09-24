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


class SlackErrorAdapter:
    """Error adapter for Slack SDK (slack-sdk)."""

    slug = "_slack_sdk"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """
        Translate a Slack SDK exception into a ToolRuntimeError.
        """
        # Lazy import the Slack SDK errors module to avoid import errors for toolkits that don't use slack-sdk
        try:
            from slack_sdk import errors
        except ImportError:
            logger.info(
                f"'slack-sdk' is not installed in the toolkit's environment, "
                f"so the '{self.slug}' adapter was not used to handle the upstream error"
            )
            return None

        result = self._handle_api_errors(exc, errors)
        if result:
            return result

        result = self._handle_other_errors(exc, errors)
        if result:
            return result

        # Failsafe for any unhandled Slack SDK errors that are not mapped above
        if hasattr(exc, "__module__") and exc.__module__ and "slack_sdk" in exc.__module__:
            logger.warning(
                "Unknown Slack SDK error encountered: %r. Falling back to generic UpstreamError.",
                exc,
                exc_info=True,
            )
            return UpstreamError(
                message=f"Upstream Slack SDK error: {exc}",
                status_code=500,
                extra={
                    "service": self.slug,
                    "error_type": exc.__class__.__name__,
                },
            )

        # Not a Slack SDK error
        return None

    def _sanitize_uri(self, uri: str) -> str:
        """Strip query params and fragments from URI for privacy."""

        try:
            parsed = urlparse(uri)
            return f"{parsed.scheme}://{parsed.netloc.strip('/')}/{parsed.path.strip('/')}"
        except Exception:
            return uri

    def _parse_retry_after(self, error: Any) -> int:
        """
        Extract retry-after from Slack API errors.
        Returns milliseconds to wait before retry.
        Defaults to 1000ms if not found.

        Args:
            error: The Slack API error to parse

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

    def _map_api_error(self, error: Any) -> ToolRuntimeError | None:
        """Map Slack SlackApiError to appropriate ToolRuntimeError."""
        # Extract error code from Slack API response
        error_code = "unknown_error"
        if hasattr(error, "response") and error.response:
            error_code = error.response.get("error", "unknown_error")

        status_code = 500  # Default to server error
        if (
            hasattr(error, "response")
            and hasattr(error.response, "status_code")
            and isinstance(error.response.status_code, int)
        ):
            status_code = error.response.status_code

        reason = error_code if error_code != "unknown_error" else "Unknown Slack SDK error"

        message = f"Upstream Slack API error: {reason}"

        # Build developer message with additional details
        developer_message = self._build_developer_message(error, error_code)

        # Build extra metadata
        extra = {
            "service": self.slug,
        }

        # Try to extract request details if available
        if hasattr(error, "api_url") and error.api_url:
            extra["endpoint"] = self._sanitize_uri(str(error.api_url))

        extra["error_code"] = error_code

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

    def _build_developer_message(self, error: Any, error_code: str) -> str:
        """Build developer message with additional details from Slack API error."""
        developer_details = [f"Slack error code: {error_code}"]

        if not (hasattr(error, "response") and error.response):
            return developer_details[0]

        warning = self._extract_response_field(error.response, "warning")
        if warning:
            developer_details.append(f"warning: {warning}")

        response_metadata = self._extract_response_field(error.response, "response_metadata")
        if response_metadata and isinstance(response_metadata, dict):
            warnings = response_metadata.get("warnings", [])
            if warnings:
                developer_details.append(f"warnings: {', '.join(warnings)}")

        return " - ".join(developer_details)

    def _extract_response_field(self, response: Any, field: str) -> Any:
        """Safely extract a field from Slack API response."""
        try:
            if hasattr(response, "get"):
                return response.get(field)
            elif hasattr(response, "__getitem__") and field in response:
                return response[field]
        except (TypeError, KeyError):
            pass
        return None

    def _handle_api_errors(self, exc: Exception, errors_module: Any) -> ToolRuntimeError | None:
        """Handle SlackApiError and its subclasses."""
        if isinstance(exc, errors_module.SlackApiError):
            return self._map_api_error(exc)

        return None

    def _handle_other_errors(self, exc: Exception, errors_module: Any) -> ToolRuntimeError | None:
        """Handle non-API Slack SDK errors."""
        if isinstance(exc, errors_module.SlackRequestError):
            return UpstreamError(
                message="Upstream Slack SDK error: Problem with the request being submitted",
                status_code=502,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.SlackRequestError.__name__,
                },
            )

        if isinstance(exc, errors_module.SlackTokenRotationError):
            return UpstreamError(
                message="Upstream Slack SDK error: Token rotation failed",
                status_code=401,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.SlackTokenRotationError.__name__,
                },
            )

        if isinstance(exc, errors_module.BotUserAccessError):
            return UpstreamError(
                message="Upstream Slack SDK error: Bot token used for user-only API method",
                status_code=403,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.BotUserAccessError.__name__,
                },
            )

        if isinstance(exc, errors_module.SlackClientConfigurationError):
            return UpstreamError(
                message="Upstream Slack SDK error: Invalid client configuration",
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.SlackClientConfigurationError.__name__,
                },
            )

        if isinstance(exc, errors_module.SlackClientNotConnectedError):
            return UpstreamError(
                message="Upstream Slack SDK error: WebSocket connection is closed",
                status_code=503,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.SlackClientNotConnectedError.__name__,
                },
            )

        if isinstance(exc, errors_module.SlackObjectFormationError):
            return UpstreamError(
                message="Upstream Slack SDK error: Invalid or malformed object",
                status_code=400,
                developer_message=str(exc),
                extra={
                    "service": self.slug,
                    "error_type": errors_module.SlackObjectFormationError.__name__,
                },
            )

        return None
