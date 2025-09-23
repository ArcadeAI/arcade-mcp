from datetime import datetime, timezone
from unittest.mock import Mock, patch

from arcade_core.errors import UpstreamError, UpstreamRateLimitError
from arcade_tdk.providers.microsoft.error_adapter import MicrosoftGraphErrorAdapter


class TestMicrosoftGraphErrorAdapter:
    """Test the Microsoft Graph error adapter functionality."""

    def setup_method(self):
        self.adapter = MicrosoftGraphErrorAdapter()

    def _create_mock_api_error(
        self, status_code=500, message=None, code=None, inner_error=None, url=None, headers=None
    ):
        """
        Create a mock APIError following Microsoft Graph error structure:
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
        """
        mock_error = Mock()
        mock_error.__class__.__name__ = "APIError"

        # Mock response
        mock_response = Mock()
        mock_response.status_code = status_code
        if url:
            mock_response.url = url
        if headers:
            mock_response.headers = headers
        else:
            mock_response.headers = {}
        mock_error.response = mock_response

        # Mock error details (always present in Microsoft Graph errors)
        mock_error_details = Mock()
        mock_error_details.message = message or "Unknown error"
        mock_error_details.code = code or "UnknownError"
        mock_error_details.inner_error = inner_error  # Can be None
        mock_error.error = mock_error_details

        return mock_error

    def test_adapter_slug(self):
        """Test that the adapter has the correct slug."""
        assert MicrosoftGraphErrorAdapter.slug == "_microsoft_graph"

    def test_sanitize_uri_removes_query_params(self):
        """Test URI sanitization removes query parameters."""
        uri = "https://graph.microsoft.com/v1.0/me/messages?$select=id,subject&$top=10"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://graph.microsoft.com/v1.0/me/messages"

    def test_sanitize_uri_removes_fragments(self):
        """Test URI sanitization removes fragments."""
        uri = "https://graph.microsoft.com/v1.0/users/me#profile"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://graph.microsoft.com/v1.0/users/me"

    def test_sanitize_uri_handles_trailing_slashes(self):
        """Test URI sanitization handles trailing slashes."""
        uri = "https://graph.microsoft.com///v1.0/me/calendars///"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://graph.microsoft.com/v1.0/me/calendars"

    def test_parse_retry_after_with_seconds(self):
        """Test parsing retry-after header with seconds value."""
        mock_error = self._create_mock_api_error(headers={"Retry-After": "120"})

        result = self.adapter._get_retry_after_milliseconds(mock_error)
        assert result == 120_000

    def test_parse_retry_after_with_lowercase_header(self):
        """Test parsing retry-after header with lowercase key."""
        mock_error = self._create_mock_api_error(headers={"retry-after": "60"})

        result = self.adapter._get_retry_after_milliseconds(mock_error)
        assert result == 60_000

    def test_parse_retry_after_with_date_format(self):
        """Test parsing retry-after header with absolute date format."""
        future_date = "Mon, 01 Jan 2029 12:00:00 GMT"
        mock_error = self._create_mock_api_error(headers={"Retry-After": future_date})

        with patch("arcade_tdk.providers.microsoft.error_adapter.datetime") as mock_datetime:
            parsed_date = datetime(2029, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.strptime.return_value = parsed_date

            # Mock datetime.now() to return a time before the parsed date
            current_time = datetime(2029, 1, 1, 11, 58, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time
            mock_datetime.timezone = timezone

            result = self.adapter._get_retry_after_milliseconds(mock_error)
            assert result == 120_000  # 2 minute diff

    def test_parse_retry_after_no_headers(self):
        """Test parsing retry-after when no headers are present."""
        mock_error = self._create_mock_api_error(headers={})

        result = self.adapter._get_retry_after_milliseconds(mock_error)
        assert result == 1_000

    def test_parse_retry_after_no_response_attribute(self):
        """Test parsing retry-after when error has no response attribute."""
        mock_error = Mock()
        mock_error.__class__.__name__ = "APIError"
        # No response attribute

        result = self.adapter._get_retry_after_milliseconds(mock_error)
        assert result == 1_000  # defaults to 1 second

    def test_parse_retry_after_invalid_date(self):
        """Test parsing retry-after with invalid date format falls back to default."""
        mock_error = self._create_mock_api_error(headers={"Retry-After": "invalid-date"})

        result = self.adapter._get_retry_after_milliseconds(mock_error)
        assert result == 1_000

    def test_extract_error_details_standard_structure(self):
        """Test extracting error details from standard Microsoft Graph error structure."""
        mock_error = self._create_mock_api_error(
            message="The request is invalid", code="invalidRequest"
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert user_message == "Upstream Microsoft Graph API error: The request is invalid"
        assert developer_message == "Microsoft Graph error code: invalidRequest"

    def test_extract_error_details_with_complete_inner_error(self):
        """Test extracting error details with complete inner error structure."""
        # Create mock inner error with all Microsoft Graph fields
        mock_inner_error = Mock()
        mock_inner_error.code = "invalidSyntax"
        setattr(mock_inner_error, "request-id", "12345-67890")
        mock_inner_error.date = "2025-09-22T16:08:56Z"
        # Explicitly set client_request_id to None to avoid Mock object
        mock_inner_error.client_request_id = None

        mock_error = self._create_mock_api_error(
            message="The request is invalid",
            code="invalidRequest",
            inner_error=mock_inner_error,
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert user_message == "Upstream Microsoft Graph API error: The request is invalid"
        assert "Microsoft Graph error code: invalidRequest" in developer_message
        assert (
            "Inner error: code: invalidSyntax, request-id: 12345-67890, date: 2025-09-22T16:08:56Z"
            in developer_message
        )

    def test_extract_error_details_with_partial_inner_error(self):
        """Test extracting error details with partial inner error (only some fields)."""
        # Create mock inner error with only code and request-id
        mock_inner_error = Mock()
        mock_inner_error.code = "tokenExpired"
        setattr(mock_inner_error, "request-id", "67890-12345")
        mock_inner_error.date = None

        mock_error = self._create_mock_api_error(
            message="Access is denied",
            code="unauthorized",
            inner_error=mock_inner_error,
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert user_message == "Upstream Microsoft Graph API error: Access is denied"
        assert "Microsoft Graph error code: unauthorized" in developer_message
        assert "Inner error: code: tokenExpired, request-id: 67890-12345" in developer_message
        assert "date:" not in developer_message

    def test_extract_error_details_without_inner_error(self):
        """Test extracting error details when innerError field is missing."""
        mock_error = self._create_mock_api_error(
            message="The resource could not be found",
            code="notFound",
            inner_error=None,
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert user_message == "Upstream Microsoft Graph API error: The resource could not be found"
        assert developer_message == "Microsoft Graph error code: notFound"
        assert "Inner error:" not in developer_message

    def test_extract_error_details_with_empty_inner_error_fields(self):
        """Test extracting error details when inner error has empty/None fields."""
        # Create mock inner error with empty fields
        mock_inner_error = Mock()
        mock_inner_error.code = None
        setattr(mock_inner_error, "request-id", None)
        mock_inner_error.date = None
        # Explicitly set all other fields to None
        mock_inner_error.request_id = None
        mock_inner_error.client_request_id = None

        mock_error = self._create_mock_api_error(
            message="Service temporarily unavailable",
            code="serviceUnavailable",
            inner_error=mock_inner_error,
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert user_message == "Upstream Microsoft Graph API error: Service temporarily unavailable"
        assert developer_message == "Microsoft Graph error code: serviceUnavailable"
        assert "Inner error:" not in developer_message

    def test_extract_error_details_exact_microsoft_graph_structure(self):
        """Test with exact Microsoft Graph API error structure from documentation."""
        # Create mock inner error matching exact structure from docs
        mock_inner_error = Mock()
        mock_inner_error.code = "invalidRange"
        setattr(mock_inner_error, "request-id", "request-id")
        mock_inner_error.date = "date-time"
        # Explicitly set client_request_id to None to avoid Mock object
        mock_inner_error.client_request_id = None

        mock_error = self._create_mock_api_error(
            message="Uploaded fragment overlaps with existing data.",
            code="badRequest",
            inner_error=mock_inner_error,
        )

        user_message, developer_message = self.adapter._extract_error_details(mock_error)

        assert (
            user_message
            == "Upstream Microsoft Graph API error: Uploaded fragment overlaps with existing data."
        )
        assert "Microsoft Graph error code: badRequest" in developer_message
        assert (
            "Inner error: code: invalidRange, request-id: request-id, date: date-time"
            in developer_message
        )

    def test_map_api_error_basic(self):
        """Test mapping basic API error with standard Microsoft Graph structure."""
        mock_error = self._create_mock_api_error(
            status_code=404,
            message="The resource could not be found",
            code="itemNotFound",
            url="https://graph.microsoft.com/v1.0/me/messages/missing",
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 404
        assert (
            result.message == "Upstream Microsoft Graph API error: The resource could not be found"
        )
        assert result.developer_message == "Microsoft Graph error code: itemNotFound"
        assert result.extra["service"] == "_microsoft_graph"
        assert result.extra["endpoint"] == "https://graph.microsoft.com/v1.0/me/messages/missing"
        assert result.extra["error_code"] == "itemNotFound"

    def test_map_api_error_rate_limit_429(self):
        """Test mapping 429 rate limit error with Microsoft Graph structure."""
        mock_error = self._create_mock_api_error(
            status_code=429,
            message="Rate limit has been exceeded.",
            code="tooManyRequests",
            url="https://graph.microsoft.com/v1.0/me/messages",
            headers={"Retry-After": "30"},
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "Upstream Microsoft Graph API error: Rate limit has been exceeded."
        assert result.developer_message == "Microsoft Graph error code: tooManyRequests"
        assert result.extra["service"] == "_microsoft_graph"
        assert result.extra["endpoint"] == "https://graph.microsoft.com/v1.0/me/messages"
        assert result.extra["error_code"] == "tooManyRequests"

    def test_map_api_error_rate_limit_503_with_too_many_requests(self):
        """Test mapping 503 error with TooManyRequests code."""
        mock_error = self._create_mock_api_error(
            status_code=503,
            message="Service temporarily unavailable due to high load.",
            code="TooManyRequests",
            headers={"Retry-After": "60"},
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 60_000
        assert (
            result.message
            == "Upstream Microsoft Graph API error: Service temporarily unavailable due to high load."
        )

    def test_map_api_error_rate_limit_503_with_service_unavailable(self):
        """Test mapping 503 error with ServiceUnavailable code."""
        mock_error = self._create_mock_api_error(
            status_code=503,
            message="Service unavailable",
            code="ServiceUnavailable",
            headers={"Retry-After": "120"},
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 120_000

    def test_map_api_error_503_without_rate_limit_code(self):
        """Test mapping 503 error without rate limit specific code."""
        mock_error = self._create_mock_api_error(
            status_code=503, message="Service unavailable", code="InternalServerError"
        )

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 503

    def test_map_api_error_default_status_code(self):
        """Test mapping API error with default status code."""
        mock_error = self._create_mock_api_error(message="Unknown error", code="UnknownError")
        # Set response to None to test default status code
        mock_error.response = None

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500  # Default

    def test_map_api_error_missing_attributes(self):
        """Test mapping API error without url and error code attributes."""
        mock_error = self._create_mock_api_error(
            status_code=400,
            message="Bad request",
            code="BadRequest",  # Code is always present in Microsoft Graph errors
            # No url
        )
        # Remove URL to test missing endpoint
        mock_error.response.url = None

        result = self.adapter._map_api_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.extra["service"] == "_microsoft_graph"
        assert "endpoint" not in result.extra
        assert result.extra["error_code"] == "BadRequest"

    def test_handle_api_errors_with_api_error(self):
        """Test handling APIError exceptions."""

        # Create mock APIError class
        class MockAPIError:
            pass

        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        mock_error = MockAPIError()
        # Add the expected attributes
        mock_error.response = Mock()
        mock_error.response.status_code = 401
        mock_error.response.url = "https://graph.microsoft.com/v1.0/me"
        mock_error.response.headers = {}
        mock_error.error = Mock()
        mock_error.error.message = "Unauthorized"
        mock_error.error.code = "Unauthorized"
        mock_error.error.inner_error = None

        result = self.adapter._handle_api_errors(mock_error, mock_msgraph)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 401
        assert result.message == "Upstream Microsoft Graph API error: Unauthorized"

    def test_handle_api_errors_non_api_error(self):
        """Test handling non-APIError exceptions returns None."""

        # Create mock APIError class
        class MockAPIError:
            pass

        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        mock_error = ValueError("Not an API error")

        result = self.adapter._handle_api_errors(mock_error, mock_msgraph)
        assert result is None

    def test_handle_api_errors_wrong_class_name(self):
        """Test handling exception with wrong class name returns None."""

        # Create mock APIError class
        class MockAPIError:
            pass

        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        mock_error = Mock()
        mock_error.__class__.__name__ = "SomeOtherError"

        result = self.adapter._handle_api_errors(mock_error, mock_msgraph)
        assert result is None

    def test_from_exception_kiota_not_installed(self, caplog):
        """Test handling when kiota-abstractions is not installed."""
        with (
            patch("arcade_tdk.providers.microsoft.error_adapter.logger") as mock_logger,
            patch.dict("sys.modules", {"kiota_abstractions.api_error": None}),
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'kiota_abstractions'"),
            ),
        ):
            mock_exc = Exception("test exception")
            result = self.adapter.from_exception(mock_exc)

        assert result is None
        mock_logger.info.assert_called_once()
        warning_message = mock_logger.info.call_args[0][0]
        assert "'kiota-abstractions' is not installed" in warning_message
        assert "_microsoft_graph" in warning_message

    def test_from_exception_api_error_handling(self):
        """Test full from_exception flow with API error."""

        # Create mock api_error module with APIError class
        class MockAPIError:
            def __init__(self):
                # Initialize with the same structure as _create_mock_api_error
                self.response = Mock()
                self.response.status_code = 403
                self.response.url = "https://graph.microsoft.com/v1.0/me/messages"
                self.response.headers = {}

                self.error = Mock()
                self.error.message = "Forbidden"
                self.error.code = "Forbidden"
                self.error.inner_error = None

        mock_api_error_module = Mock()
        mock_api_error_module.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_api_error_module

        # Create the mock error as an actual instance of MockAPIError
        mock_error = MockAPIError()

        with patch.dict(
            "sys.modules",
            {
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_api_error_module,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 403
        assert result.message == "Upstream Microsoft Graph API error: Forbidden"

    def test_from_exception_fallback_for_unhandled_msgraph_error(self):
        """Test fallback handling for unhandled Microsoft Graph errors."""

        # Create an unhandled Microsoft Graph error
        class MockUnhandledError(Exception):
            pass

        mock_error = MockUnhandledError("Some unhandled Microsoft Graph error")
        mock_error.__module__ = "msgraph.generated.models"

        # Create mock APIError class
        class MockAPIError:
            pass

        # Create mock msgraph module
        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_msgraph

        with patch.dict(
            "sys.modules",
            {
                "msgraph": Mock(),
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_msgraph,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert (
            result.message == "Upstream Microsoft Graph error: Some unhandled Microsoft Graph error"
        )
        assert result.extra["service"] == "_microsoft_graph"
        assert result.extra["error_type"] == "MockUnhandledError"

    def test_from_exception_fallback_with_msgraph_core_module(self):
        """Test fallback handling for errors from msgraph_core module."""

        class MockCoreError(Exception):
            pass

        mock_error = MockCoreError("Core error")
        mock_error.__module__ = "msgraph_core.requests"

        # Create mock APIError class
        class MockAPIError:
            pass

        # Create mock msgraph module
        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_msgraph

        with patch.dict(
            "sys.modules",
            {
                "msgraph": Mock(),
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_msgraph,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert result.message == "Upstream Microsoft Graph error: Core error"

    def test_from_exception_non_msgraph_error(self):
        """Test handling non-Microsoft Graph errors returns None."""
        # Create a non-Microsoft Graph error
        mock_error = ValueError("Not a Microsoft Graph error")
        mock_error.__module__ = "builtins"

        # Create mock APIError class
        class MockAPIError:
            pass

        # Create mock msgraph module
        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_msgraph

        with patch.dict(
            "sys.modules",
            {
                "msgraph": Mock(),
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_msgraph,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert result is None

    def test_from_exception_error_without_module(self):
        """Test handling error without __module__ attribute."""
        mock_error = Exception("Error without module")
        if hasattr(mock_error, "__module__"):
            del mock_error.__module__

        # Create mock APIError class
        class MockAPIError:
            pass

        # Create mock msgraph module
        mock_msgraph = Mock()
        mock_msgraph.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_msgraph

        with patch.dict(
            "sys.modules",
            {
                "msgraph": Mock(),
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_msgraph,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert result is None

    def test_from_exception_rate_limit_integration(self):
        """Test full integration with rate limit error."""

        # Create mock api_error module with APIError class
        class MockAPIError:
            def __init__(self):
                # Initialize with the same structure as _create_mock_api_error
                self.response = Mock()
                self.response.status_code = 429
                self.response.url = "https://graph.microsoft.com/v1.0/me/messages"
                self.response.headers = {"Retry-After": "300"}

                self.error = Mock()
                self.error.message = "Rate limit exceeded"
                self.error.code = "TooManyRequests"
                self.error.inner_error = None

        mock_api_error_module = Mock()
        mock_api_error_module.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_api_error_module

        # Create the mock error as an actual instance of MockAPIError
        mock_error = MockAPIError()

        with patch.dict(
            "sys.modules",
            {
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_api_error_module,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 300_000
        assert result.message == "Upstream Microsoft Graph API error: Rate limit exceeded"
        assert result.extra["service"] == "_microsoft_graph"
        assert result.extra["error_code"] == "TooManyRequests"

    def test_from_exception_complex_error_details(self):
        """Test handling error with complex nested error details."""

        # Create mock api_error module with APIError class
        class MockAPIError:
            def __init__(self):
                # Create mock inner error with proper Mock structure
                mock_inner_error = Mock()
                mock_inner_error.code = "InvalidSyntax"
                setattr(mock_inner_error, "request-id", "12345-67890")
                mock_inner_error.date = "2025-09-22T16:08:56Z"

                # Initialize with the same structure as _create_mock_api_error
                self.response = Mock()
                self.response.status_code = 400
                self.response.url = "https://graph.microsoft.com/v1.0/me/messages"
                self.response.headers = {}

                self.error = Mock()
                self.error.message = "Invalid request syntax"
                self.error.code = "BadRequest"
                self.error.inner_error = mock_inner_error

        mock_api_error_module = Mock()
        mock_api_error_module.APIError = MockAPIError

        # Create parent module mock
        mock_kiota_module = Mock()
        mock_kiota_module.api_error = mock_api_error_module

        # Create the mock error as an actual instance of MockAPIError
        mock_error = MockAPIError()

        with patch.dict(
            "sys.modules",
            {
                "kiota_abstractions": mock_kiota_module,
                "kiota_abstractions.api_error": mock_api_error_module,
            },
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream Microsoft Graph API error: Invalid request syntax"
        assert "Microsoft Graph error code: BadRequest" in result.developer_message
        assert "Inner error:" in result.developer_message
