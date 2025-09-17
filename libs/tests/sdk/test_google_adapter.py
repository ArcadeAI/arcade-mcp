from datetime import datetime, timezone
from unittest.mock import Mock, patch

from arcade_core.errors import UpstreamError, UpstreamRateLimitError
from arcade_tdk.providers.google.error_adapter import GoogleErrorAdapter


class TestGoogleErrorAdapter:
    """Test the Google error adapter functionality."""

    def setup_method(self):
        self.adapter = GoogleErrorAdapter()

    def _create_mock_errors_module(self):
        """Create a mock errors module with all necessary error classes."""

        class MockHttpError(Exception):
            pass

        class MockBatchError(Exception):
            pass

        class MockInvalidJsonError(Exception):
            pass

        class MockUnknownApiNameOrVersion(Exception):
            pass

        class MockUnacceptableMimeTypeError(Exception):
            pass

        class MockMediaUploadSizeError(Exception):
            pass

        class MockInvalidChunkSizeError(Exception):
            pass

        class MockInvalidNotificationError(Exception):
            pass

        mock_errors = Mock()
        mock_errors.HttpError = MockHttpError
        mock_errors.BatchError = MockBatchError
        mock_errors.InvalidJsonError = MockInvalidJsonError
        mock_errors.UnknownApiNameOrVersion = MockUnknownApiNameOrVersion
        mock_errors.UnacceptableMimeTypeError = MockUnacceptableMimeTypeError
        mock_errors.MediaUploadSizeError = MockMediaUploadSizeError
        mock_errors.InvalidChunkSizeError = MockInvalidChunkSizeError
        mock_errors.InvalidNotificationError = MockInvalidNotificationError

        return mock_errors

    def test_adapter_slug(self):
        """Test that the adapter has the correct slug."""
        assert GoogleErrorAdapter.slug == "_google_api_client"

    def test_sanitize_uri_removes_query_params(self):
        """Test URI sanitization removes query parameters."""
        uri = "https://www.googleapis.com/drive/v3/files/123?key=secret&fields=id,name"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://www.googleapis.com/drive/v3/files/123"

    def test_sanitize_uri_removes_fragments(self):
        """Test URI sanitization removes fragments."""
        uri = "https://www.googleapis.com/gmail/v1/users/me/messages#inbox"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://www.googleapis.com/gmail/v1/users/me/messages"

    def test_sanitize_uri_handles_trailing_slashes(self):
        """Test URI sanitization handles trailing slashes."""
        uri = "https://www.googleapis.com///sheets/v4/spreadsheets///"
        result = self.adapter._sanitize_uri(uri)
        assert result == "https://www.googleapis.com/sheets/v4/spreadsheets"

    def test_parse_retry_after_with_seconds(self):
        """Test parsing retry-after header with seconds value."""
        mock_error = Mock()
        mock_error.resp = Mock()
        mock_error.resp.headers = {"Retry-After": "120"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 120_000

    def test_parse_retry_after_with_lowercase_header(self):
        """Test parsing retry-after header with lowercase key."""
        mock_error = Mock()
        mock_error.resp = Mock()
        mock_error.resp.headers = {"retry-after": "60"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 60_000

    def test_parse_retry_after_with_date_format(self):
        """Test parsing retry-after header with absolute date format."""
        future_date = "Mon, 01 Jan 2029 12:00:00 GMT"
        mock_error = Mock()
        mock_error.resp = Mock()
        mock_error.resp.headers = {"Retry-After": future_date}

        with patch("arcade_tdk.providers.google.error_adapter.datetime") as mock_datetime:
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
        mock_error.resp = Mock()
        mock_error.resp.headers = {}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1_000

    def test_parse_retry_after_no_resp_attribute(self):
        """Test parsing retry-after when error has no resp attribute."""
        mock_error = Mock()
        del mock_error.resp

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1_000  # defaults to 1 second

    def test_parse_retry_after_invalid_date(self):
        """Test parsing retry-after with invalid date format falls back to default."""
        mock_error = Mock()
        mock_error.resp = Mock()
        mock_error.resp.headers = {"Retry-After": "invalid-date"}

        result = self.adapter._parse_retry_after(mock_error)
        assert result == 1_000

    def test_map_http_error_basic(self):
        """Test mapping basic HTTP error."""
        mock_error = Mock()
        mock_error.status_code = 404
        mock_error.reason = "Not Found"
        mock_error.error_details = None
        mock_error.uri = "https://www.googleapis.com/drive/v3/files/missing"
        mock_error.method_ = "get"

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 404
        assert result.message == "Upstream Google API error: Not Found"
        assert result.extra["service"] == "_google_api_client"
        assert result.extra["endpoint"] == "https://www.googleapis.com/drive/v3/files/missing"
        assert result.extra["http_method"] == "GET"

    def test_map_http_error_with_string_details(self):
        """Test mapping HTTP error with string error details."""
        mock_error = Mock()
        mock_error.status_code = 400
        mock_error.reason = "Bad Request"
        mock_error.error_details = "Invalid field value"
        mock_error.uri = "https://www.googleapis.com/sheets/v4/spreadsheets"
        mock_error.method_ = "post"

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert "Invalid field value" in result.message
        assert result.extra["service"] == "_google_api_client"
        assert result.extra["http_method"] == "POST"

    def test_map_http_error_with_structured_details(self):
        """Test mapping HTTP error with structured error details."""
        mock_error = Mock()
        mock_error.status_code = 403
        mock_error.reason = "Forbidden"
        mock_error.error_details = {"error": {"code": 403, "message": "Insufficient permissions"}}
        mock_error.uri = "https://www.googleapis.com/drive/v3/files"
        mock_error.method_ = "delete"

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 403
        assert result.message == "Upstream Google API error: Forbidden"
        assert "Upstream Google API error details" in result.developer_message
        assert result.extra["http_method"] == "DELETE"

    def test_map_http_error_rate_limit(self):
        """Test mapping 429 rate limit error."""
        mock_error = Mock()
        mock_error.status_code = 429
        mock_error.reason = "Too Many Requests"
        mock_error.error_details = None
        mock_error.uri = "https://www.googleapis.com/gmail/v1/users/me/messages"
        mock_error.method_ = "get"
        mock_error.resp = Mock()
        mock_error.resp.headers = {"Retry-After": "30"}

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "Upstream Google API error: Too Many Requests"
        assert result.extra["service"] == "_google_api_client"
        assert result.extra["endpoint"] == "https://www.googleapis.com/gmail/v1/users/me/messages"
        assert result.extra["http_method"] == "GET"

    def test_map_http_error_no_reason(self):
        """Test mapping HTTP error with no reason."""
        mock_error = Mock()
        mock_error.status_code = 500
        mock_error.reason = None
        mock_error.error_details = None
        mock_error.uri = "https://www.googleapis.com/calendar/v3/calendars"
        mock_error.method_ = "post"

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert result.message == "Upstream Google API error: HTTP 500 error"

    def test_map_http_error_missing_attributes(self):
        """Test mapping HTTP error without uri and method attributes."""
        mock_error = Mock()
        mock_error.status_code = 503
        mock_error.reason = "Service Unavailable"
        mock_error.error_details = None

        # Remove uri and method_ attributes
        if hasattr(mock_error, "uri"):
            del mock_error.uri
        if hasattr(mock_error, "method_"):
            del mock_error.method_

        result = self.adapter._map_http_error(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.extra["service"] == "_google_api_client"
        assert "endpoint" not in result.extra
        assert "http_method" not in result.extra

    def test_handle_http_errors_with_http_error(self):
        """Test handling HttpError exceptions."""
        mock_errors = self._create_mock_errors_module()

        # Create mock error instance
        mock_error = mock_errors.HttpError()
        mock_error.status_code = 401
        mock_error.reason = "Unauthorized"
        mock_error.error_details = None
        mock_error.uri = "https://www.googleapis.com/drive/v3/files"
        mock_error.method_ = "get"

        result = self.adapter._handle_http_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 401
        assert result.message == "Upstream Google API error: Unauthorized"

    def test_handle_http_errors_with_batch_error_with_status(self):
        """Test handling BatchError with response status."""
        mock_errors = self._create_mock_errors_module()

        # Create mock error instance
        mock_error = mock_errors.BatchError()
        mock_error.reason = "Batch operation failed"
        mock_error.error_details = None
        mock_error.resp = Mock()
        mock_error.resp.status = 400

        result = self.adapter._handle_http_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream Google API error: Batch operation failed"

    def test_handle_http_errors_with_batch_error_no_status(self):
        """Test handling BatchError without response status."""
        mock_errors = self._create_mock_errors_module()

        # Create mock error instance
        mock_error = mock_errors.BatchError()
        mock_error.reason = "Batch operation failed"

        result = self.adapter._handle_http_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert (
            result.message == "Upstream Google API batch operation failed: Batch operation failed"
        )
        assert result.extra["service"] == "google_api"
        assert result.extra["error_type"] == "BatchError"

    def test_handle_http_errors_unhandled_exception(self):
        """Test handling non-HTTP exceptions returns None."""
        mock_errors = self._create_mock_errors_module()

        # Create a non-HTTP exception
        mock_error = ValueError("Not an HTTP error")

        result = self.adapter._handle_http_errors(mock_error, mock_errors)
        assert result is None

    def test_handle_other_errors_invalid_json_error(self):
        """Test handling InvalidJsonError."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.InvalidJsonError("Invalid JSON response")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.message == "Upstream Google API returned invalid JSON response"
        assert result.developer_message == "Invalid JSON response"
        assert result.extra["service"] == "_google_api_client"
        assert result.extra["error_type"] == "InvalidJsonError"

    def test_handle_other_errors_unknown_api_name_or_version(self):
        """Test handling UnknownApiNameOrVersion."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.UnknownApiNameOrVersion("Unknown API: nonexistent/v1")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 404
        assert result.message == "Upstream Google API error: Unknown API name or version"
        assert result.developer_message == "Unknown API: nonexistent/v1"
        assert result.extra["error_type"] == "UnknownApiNameOrVersion"

    def test_handle_other_errors_unacceptable_mime_type_error(self):
        """Test handling UnacceptableMimeTypeError."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.UnacceptableMimeTypeError("MIME type not supported")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert (
            result.message == "Upstream Google API error: Unacceptable MIME type for this operation"
        )
        assert result.developer_message == "MIME type not supported"
        assert result.extra["error_type"] == "UnacceptableMimeTypeError"

    def test_handle_other_errors_media_upload_size_error(self):
        """Test handling MediaUploadSizeError."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.MediaUploadSizeError("File size exceeds 5GB limit")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream Google API error: Media file size exceeds allowed limit"
        assert result.developer_message == "File size exceeds 5GB limit"
        assert result.extra["error_type"] == "MediaUploadSizeError"

    def test_handle_other_errors_invalid_chunk_size_error(self):
        """Test handling InvalidChunkSizeError."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.InvalidChunkSizeError("Chunk size must be multiple of 256KB")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream Google API error: Invalid chunk size specified"
        assert result.developer_message == "Chunk size must be multiple of 256KB"
        assert result.extra["error_type"] == "InvalidChunkSizeError"

    def test_handle_other_errors_invalid_notification_error(self):
        """Test handling InvalidNotificationError."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.InvalidNotificationError("Invalid webhook URL")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "Upstream Google API error: Invalid notification configuration"
        assert result.developer_message == "Invalid webhook URL"
        assert result.extra["error_type"] == "InvalidNotificationError"

    def test_handle_other_errors_unhandled_exception(self):
        """Test handling non-Google API exceptions returns None."""
        mock_errors = self._create_mock_errors_module()

        # Create a non-Google API exception
        mock_error = ValueError("Not a Google API error")

        result = self.adapter._handle_other_errors(mock_error, mock_errors)
        assert result is None

    def test_from_exception_googleapiclient_not_installed(self, caplog):
        """Test handling when googleapiclient is not installed."""
        with (
            patch("arcade_tdk.providers.google.error_adapter.logger") as mock_logger,
            patch.dict("sys.modules", {"googleapiclient": None}),
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'googleapiclient'"),
            ),
        ):
            mock_exc = Exception("test exception")
            result = self.adapter.from_exception(mock_exc)

            assert result is None
            mock_logger.info.assert_called_once()
            warning_message = mock_logger.info.call_args[0][0]
            assert "'googleapiclient' is not installed" in warning_message
            assert "_google_api_client" in warning_message

    def test_from_exception_http_error_handling(self):
        """Test full from_exception flow with HTTP error."""
        mock_errors = self._create_mock_errors_module()

        # Create mock error instance
        mock_error = mock_errors.HttpError()
        mock_error.status_code = 403
        mock_error.reason = "Forbidden"
        mock_error.error_details = None
        mock_error.uri = "https://www.googleapis.com/drive/v3/files"
        mock_error.method_ = "get"

        # Create mock googleapiclient module
        mock_googleapiclient = Mock()
        mock_googleapiclient.errors = mock_errors

        with patch.dict(
            "sys.modules",
            {"googleapiclient": mock_googleapiclient, "googleapiclient.errors": mock_errors},
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 403
        assert result.message == "Upstream Google API error: Forbidden"

    def test_from_exception_other_error_handling(self):
        """Test full from_exception flow with other error types."""
        mock_errors = self._create_mock_errors_module()
        mock_error = mock_errors.InvalidJsonError("Invalid JSON")

        # Create mock googleapiclient module
        mock_googleapiclient = Mock()
        mock_googleapiclient.errors = mock_errors

        with patch.dict(
            "sys.modules",
            {"googleapiclient": mock_googleapiclient, "googleapiclient.errors": mock_errors},
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.message == "Upstream Google API returned invalid JSON response"

    def test_from_exception_fallback_for_unhandled_google_error(self):
        """Test fallback handling for unhandled Google API errors."""
        mock_errors = self._create_mock_errors_module()

        # Create an unhandled Google API error
        class MockUnhandledError(Exception):
            pass

        mock_error = MockUnhandledError("Some unhandled Google error")
        mock_error.__module__ = "googleapiclient.errors"

        # Create mock googleapiclient module
        mock_googleapiclient = Mock()
        mock_googleapiclient.errors = mock_errors

        with patch.dict(
            "sys.modules",
            {"googleapiclient": mock_googleapiclient, "googleapiclient.errors": mock_errors},
        ):
            result = self.adapter.from_exception(mock_error)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert result.message == "Upstream Google API error: Some unhandled Google error"
        assert result.extra["service"] == "_google_api_client"
        assert result.extra["error_type"] == "MockUnhandledError"

    def test_from_exception_non_google_error(self):
        """Test handling non-Google API errors returns None."""
        mock_errors = self._create_mock_errors_module()

        # Create a non-Google API error
        mock_error = ValueError("Not a Google error")
        mock_error.__module__ = "builtins"

        # Create mock googleapiclient module
        mock_googleapiclient = Mock()
        mock_googleapiclient.errors = mock_errors

        with patch.dict(
            "sys.modules",
            {"googleapiclient": mock_googleapiclient, "googleapiclient.errors": mock_errors},
        ):
            result = self.adapter.from_exception(mock_error)

        assert result is None
