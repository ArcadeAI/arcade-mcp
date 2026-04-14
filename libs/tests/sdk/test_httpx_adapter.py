import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import httpx
import requests

from arcade_core.errors import ErrorKind, UpstreamError, UpstreamRateLimitError
from arcade_tdk.providers.http.error_adapter import BaseHTTPErrorMapper, HTTPErrorAdapter


class TestBaseHTTPErrorMapper:
    """Test the base HTTP error mapper functionality."""

    def setup_method(self):
        self.mapper = BaseHTTPErrorMapper()

    def test_parse_retry_ms_with_retry_after_seconds(self):
        """Test parsing retry-after header with seconds value."""
        headers = {"retry-after": "60"}
        result = self.mapper._parse_retry_ms(headers)
        assert result == 60_000

    def test_parse_retry_ms_with_x_ratelimit_reset(self):
        """Test parsing x-ratelimit-reset header with seconds value."""
        headers = {"x-ratelimit-reset": "120"}
        result = self.mapper._parse_retry_ms(headers)
        assert result == 120_000

    def test_parse_retry_ms_with_x_ratelimit_reset_ms(self):
        """Test parsing x-ratelimit-reset-ms header with milliseconds value."""
        headers = {"x-ratelimit-reset-ms": "5000"}
        result = self.mapper._parse_retry_ms(headers)
        assert result == 5_000

    def test_parse_retry_ms_with_date_format(self):
        """Test parsing retry header with absolute date format."""
        future_date = "Mon, 01 Jan 2029 12:00:00 GMT"
        headers = {"retry-after": future_date}

        with patch("arcade_tdk.providers.http.error_adapter.datetime") as mock_datetime:
            parsed_date = datetime(2029, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.strptime.return_value = parsed_date

            # Mock datetime.now() to return a time before the parsed date
            current_time = datetime(2029, 1, 1, 11, 59, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time

            mock_datetime.timezone = timezone

            result = self.mapper._parse_retry_ms(headers)
            assert result == 60_000  # 1 minute diff

    def test_parse_retry_ms_no_headers(self):
        """Test parsing retry when no rate limit headers are present."""
        headers = {"content-type": "application/json"}
        result = self.mapper._parse_retry_ms(headers)
        assert result == 1_000

    def test_parse_retry_ms_invalid_date(self):
        """Test parsing retry with invalid date format falls back to default."""
        headers = {"retry-after": "invalid-date"}
        result = self.mapper._parse_retry_ms(headers)
        assert result == 1_000

    def test_sanitize_uri_removes_query_params(self):
        """Test URI sanitization removes query parameters."""
        uri = "https://api.example.com/users/123?token=secret&filter=active"
        result = self.mapper._sanitize_uri(uri)
        assert result == "https://api.example.com/users/123"

    def test_sanitize_uri_removes_fragments(self):
        """Test URI sanitization removes fragments."""
        uri = "https://api.example.com/users#section"
        result = self.mapper._sanitize_uri(uri)
        assert result == "https://api.example.com/users"

    def test_sanitize_uri_handles_trailing_slashes(self):
        """Test URI sanitization handles trailing slashes."""
        uri = "https://api.example.com///path///"
        result = self.mapper._sanitize_uri(uri)
        assert result == "https://api.example.com/path"

    def test_build_extra_metadata_basic(self):
        """Test building extra metadata without request info."""
        result = self.mapper._build_extra_metadata()
        assert result == {"service": "_http"}

    def test_build_extra_metadata_with_url_and_method(self):
        """Test building extra metadata with URL and method."""
        result = self.mapper._build_extra_metadata(
            request_url="https://api.example.com/test?secret=123", request_method="post"
        )
        expected = {
            "service": "_http",
            "endpoint": "https://api.example.com/test",
            "http_method": "POST",
        }
        assert result == expected

    def test_map_status_to_error_rate_limit(self):
        """Test mapping 429 status to rate limit error."""
        headers = {"retry-after": "30"}
        result = self.mapper._map_status_to_error(
            status=429,
            headers=headers,
            msg="Rate limit exceeded",
            request_url="https://api.example.com/test",
            request_method="GET",
        )

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "Rate limit exceeded"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/test"
        assert result.extra["http_method"] == "GET"

    def test_map_status_to_error_generic(self):
        """Test mapping generic HTTP status to upstream error."""
        headers = {}
        result = self.mapper._map_status_to_error(
            status=500,
            headers=headers,
            msg="Internal server error",
            request_url="https://api.example.com/test",
            request_method="POST",
        )

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 500
        assert result.message == "Internal server error"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/test"
        assert result.extra["http_method"] == "POST"


class TestHTTPErrorAdapter:
    """Test the main HTTP error adapter."""

    def setup_method(self):
        self.adapter = HTTPErrorAdapter()

    def test_httpx_not_installed(self):
        """Test handling when httpx is not installed."""
        with patch.object(self.adapter._httpx_handler, "handle_exception") as mock_handle:
            # Simulate what happens when httpx is not installed (returns None)
            mock_handle.return_value = None

            mock_exc = Exception("test exception")

            result = self.adapter.from_exception(mock_exc)
            assert result is None

    def test_requests_not_installed(self):
        """Test handling when requests is not installed."""
        with patch.object(self.adapter._requests_handler, "handle_exception") as mock_handle:
            # Simulate what happens when requests is not installed (returns None)
            mock_handle.return_value = None

            mock_exc = Exception("test exception")

            result = self.adapter.from_exception(mock_exc)
            assert result is None

    def test_httpx_http_status_error_handling(self):
        """Test handling httpx HTTPStatusError."""

        # Create a mock HTTPStatusError class and make our exception inherit from it
        class MockHTTPStatusError(Exception):
            pass

        # Create the exception instance that inherits from our mock class
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}

        mock_request = Mock()
        mock_request.url = "https://api.example.com/users/123"
        mock_request.method = "GET"

        mock_exc = MockHTTPStatusError("404 Client Error: Not Found")
        mock_exc.response = mock_response
        mock_exc.request = mock_request

        with patch("httpx.HTTPStatusError", MockHTTPStatusError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 404
        assert result.message == "404 Client Error: Not Found"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/users/123"
        assert result.extra["http_method"] == "GET"

    def test_httpx_rate_limit_handling(self):
        """Test handling httpx 429 rate limit."""

        # Create a mock HTTPStatusError class
        class MockHTTPStatusError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "60", "content-type": "application/json"}

        mock_request = Mock()
        mock_request.url = "https://api.example.com/upload"
        mock_request.method = "POST"

        mock_exc = MockHTTPStatusError("429 Too Many Requests")
        mock_exc.response = mock_response
        mock_exc.request = mock_request

        with patch("httpx.HTTPStatusError", MockHTTPStatusError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 60_000
        assert result.message == "429 Too Many Requests"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/upload"
        assert result.extra["http_method"] == "POST"

    def test_requests_http_error_handling(self):
        """Test handling requests HTTPError."""

        # Create a mock HTTPError class
        class MockHTTPError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {"www-authenticate": "Bearer"}

        mock_request = Mock()
        mock_request.url = "https://api.example.com/protected"
        mock_request.method = "GET"

        mock_response.request = mock_request

        mock_exc = MockHTTPError("403 Forbidden")
        mock_exc.response = mock_response

        with patch("requests.exceptions.HTTPError", MockHTTPError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 403
        assert result.message == "403 Forbidden"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/protected"
        assert result.extra["http_method"] == "GET"

    def test_requests_http_error_with_url_fallback(self):
        """Test handling requests HTTPError when request is not available but response.url is."""

        # Create a mock HTTPError class
        class MockHTTPError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.request = None  # No request object
        mock_response.url = "https://api.example.com/server-error"

        mock_exc = MockHTTPError("500 Internal Server Error")
        mock_exc.response = mock_response

        with patch("requests.exceptions.HTTPError", MockHTTPError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 500
        assert result.message == "500 Internal Server Error"
        assert result.extra["service"] == "_http"
        assert result.extra["endpoint"] == "https://api.example.com/server-error"
        assert "http_method" not in result.extra  # No method available

    def test_requests_http_error_no_response(self):
        """Test handling requests HTTPError with no response."""

        # Create a mock HTTPError class
        class MockHTTPError(Exception):
            pass

        mock_exc = MockHTTPError("No response")
        mock_exc.response = None

        with patch("requests.exceptions.HTTPError", MockHTTPError):
            result = self.adapter.from_exception(mock_exc)

        assert result is None

    def test_requests_timeout_exception_handling(self):
        """Timeout exceptions should map to retryable upstream timeouts."""
        request = requests.Request("GET", "https://api.example.com/slow?token=secret").prepare()
        exc = requests.exceptions.ReadTimeout("Request timed out", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 504
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP timeout: ReadTimeout"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "ReadTimeout"
        assert result.extra["endpoint"] == "https://api.example.com/slow"
        assert result.extra["http_method"] == "GET"

    def test_requests_transport_exception_handling(self):
        """Connection errors should map to retryable transport failures."""
        request = requests.Request("POST", "https://api.example.com/ping").prepare()
        exc = requests.exceptions.ConnectionError("Connection failed", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP transport error: ConnectionError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "ConnectionError"
        assert result.extra["endpoint"] == "https://api.example.com/ping"
        assert result.extra["http_method"] == "POST"

    def test_requests_invalid_url_is_non_retryable_bad_request(self):
        """Invalid URL errors should map to non-retryable bad request."""
        request = requests.Request("GET", "https://api.example.com/bad").prepare()
        exc = requests.exceptions.InvalidURL("Invalid URL", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.can_retry is False
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.message == "Upstream HTTP request is invalid: InvalidURL"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "InvalidURL"
        assert result.extra["endpoint"] == "https://api.example.com/bad"
        assert result.extra["http_method"] == "GET"

    def test_requests_content_decoding_error_handling(self):
        """Decode failures should map to retryable upstream decode errors."""
        request = requests.Request("GET", "https://api.example.com/json").prepare()
        exc = requests.exceptions.ContentDecodingError("Bad payload", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP response decoding failed: ContentDecodingError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "ContentDecodingError"
        assert result.extra["endpoint"] == "https://api.example.com/json"
        assert result.extra["http_method"] == "GET"

    def test_requests_too_many_redirects_is_non_retryable_bad_request(self):
        """Redirect loops should map to non-retryable bad request errors."""
        request = requests.Request("GET", "https://api.example.com/redirect-loop").prepare()
        exc = requests.exceptions.TooManyRedirects("Exceeded redirect limit", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.can_retry is False
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.message == "Upstream HTTP request redirect limit exceeded: TooManyRedirects"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "TooManyRedirects"
        assert result.extra["endpoint"] == "https://api.example.com/redirect-loop"
        assert result.extra["http_method"] == "GET"

    def test_requests_request_exception_fallback(self):
        """Unhandled requests base exceptions should map as upstream errors."""
        request = requests.Request("DELETE", "https://api.example.com/resource/123").prepare()
        exc = requests.exceptions.RequestException("Request failed", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP request failed: RequestException"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "RequestException"
        assert result.extra["endpoint"] == "https://api.example.com/resource/123"
        assert result.extra["http_method"] == "DELETE"

    def test_unhandled_exception_logs_warning(self, caplog):
        """Test that unhandled exceptions log a warning."""
        with caplog.at_level(logging.INFO):
            unknown_exc = ValueError("Some unrelated error")
            result = self.adapter.from_exception(unknown_exc)

            assert result is None
            assert len(caplog.records) == 1
            assert "ValueError" in caplog.records[0].message
            assert "_http" in caplog.records[0].message
            assert "not handled" in caplog.records[0].message

    def test_httpx_without_request_info(self):
        """Test handling httpx exception without request information."""

        # Create a mock HTTPStatusError class
        class MockHTTPStatusError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {}

        mock_exc = MockHTTPStatusError("400 Bad Request")
        mock_exc.response = mock_response
        mock_exc.request = None

        with patch("httpx.HTTPStatusError", MockHTTPStatusError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.message == "400 Bad Request"
        assert result.extra["service"] == "_http"
        assert "endpoint" not in result.extra
        assert "http_method" not in result.extra

    def test_httpx_timeout_exception_handling(self):
        """Timeout exceptions should map to retryable upstream timeouts."""
        request = httpx.Request("GET", "https://api.example.com/slow?token=secret")
        exc = httpx.ReadTimeout("Read timed out", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 504
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP timeout: ReadTimeout"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "ReadTimeout"
        assert result.extra["endpoint"] == "https://api.example.com/slow"
        assert result.extra["http_method"] == "GET"

    def test_httpx_transport_exception_handling(self):
        """Transport exceptions should map to retryable upstream transport errors."""
        request = httpx.Request("POST", "https://api.example.com/ping")
        exc = httpx.ConnectError("Connection failed", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP transport error: ConnectError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "ConnectError"
        assert result.extra["endpoint"] == "https://api.example.com/ping"
        assert result.extra["http_method"] == "POST"

    def test_httpx_unsupported_protocol_is_non_retryable_bad_request(self):
        """Unsupported protocol should map to a non-retryable bad request."""
        request = httpx.Request("GET", "ftp://api.example.com/resource")
        exc = httpx.UnsupportedProtocol("Unsupported protocol", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.can_retry is False
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.message == "Upstream HTTP request is invalid: UnsupportedProtocol"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "UnsupportedProtocol"
        assert result.extra["endpoint"] == "ftp://api.example.com/resource"
        assert result.extra["http_method"] == "GET"

    def test_httpx_request_error_fallback(self):
        """Unhandled httpx RequestError subclasses should still map as upstream errors."""
        request = httpx.Request("DELETE", "https://api.example.com/resource/123")
        exc = httpx.RequestError("Request failed", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP request failed: RequestError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "RequestError"
        assert result.extra["endpoint"] == "https://api.example.com/resource/123"
        assert result.extra["http_method"] == "DELETE"

    def test_httpx_decoding_error_handling(self):
        """Decoding errors should map to retryable server-side upstream errors."""
        request = httpx.Request("GET", "https://api.example.com/json")
        exc = httpx.DecodingError("Unable to decode response body", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 502
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP response decoding failed: DecodingError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "DecodingError"
        assert result.extra["endpoint"] == "https://api.example.com/json"
        assert result.extra["http_method"] == "GET"

    def test_httpx_local_protocol_error_is_non_retryable_bad_request(self):
        """Local protocol errors should map to non-retryable bad request errors."""
        request = httpx.Request("GET", "https://api.example.com/broken")
        exc = httpx.LocalProtocolError("Malformed local protocol state", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.can_retry is False
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.message == "Upstream HTTP request is invalid: LocalProtocolError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "LocalProtocolError"
        assert result.extra["endpoint"] == "https://api.example.com/broken"
        assert result.extra["http_method"] == "GET"

    def test_httpx_remote_protocol_error_is_retryable_transport_error(self):
        """Remote protocol errors should map to retryable transport errors."""
        request = httpx.Request("GET", "https://api.example.com/protocol")
        exc = httpx.RemoteProtocolError("Malformed upstream protocol response", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 503
        assert result.can_retry is True
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        assert result.message == "Upstream HTTP transport error: RemoteProtocolError"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "RemoteProtocolError"
        assert result.extra["endpoint"] == "https://api.example.com/protocol"
        assert result.extra["http_method"] == "GET"

    def test_httpx_too_many_redirects_is_non_retryable_bad_request(self):
        """Redirect loops should map to non-retryable bad request errors."""
        request = httpx.Request("GET", "https://api.example.com/redirect-loop")
        exc = httpx.TooManyRedirects("Exceeded redirect limit", request=request)

        result = self.adapter.from_exception(exc)

        assert isinstance(result, UpstreamError)
        assert result.status_code == 400
        assert result.can_retry is False
        assert result.kind == ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        assert result.message == "Upstream HTTP request redirect limit exceeded: TooManyRedirects"
        assert result.extra["service"] == "_http"
        assert result.extra["error_type"] == "TooManyRedirects"
        assert result.extra["endpoint"] == "https://api.example.com/redirect-loop"
        assert result.extra["http_method"] == "GET"

    def test_adapter_slug(self):
        """Test that the adapter has the correct slug."""
        assert HTTPErrorAdapter.slug == "_http"

    def test_map_status_to_error_403_with_exhausted_quota(self):
        """Test mapping 403 with exhausted quota to rate limit error."""
        headers = {
            "retry-after": "30",
            "x-ratelimit-remaining": "0",
        }
        result = self.adapter._map_status_to_error(
            status=403,
            headers=headers,
            msg="Forbidden",
            request_url="https://api.example.com/user/repos",
            request_method="GET",
        )

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "Forbidden"

    def test_map_status_to_error_403_with_remaining_quota(self):
        """Test mapping 403 with remaining quota to regular upstream error."""
        headers = {
            "x-ratelimit-remaining": "4941",
            "x-ratelimit-reset": "1762795446",
        }
        result = self.adapter._map_status_to_error(
            status=403,
            headers=headers,
            msg="Forbidden",
            request_url="https://api.example.com/user/repos",
            request_method="GET",
        )

        assert isinstance(result, UpstreamError)
        assert not isinstance(result, UpstreamRateLimitError)
        assert result.status_code == 403
        assert result.message == "Forbidden"

    def test_is_rate_limit_403_with_exhausted_quota(self):
        """Test detecting rate limit 403 when quota is exhausted."""
        headers = {"x-ratelimit-remaining": "0"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_remaining_quota(self):
        """Test that 403 with remaining quota is NOT detected as rate limiting."""
        headers = {"x-ratelimit-remaining": "4941"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_is_rate_limit_403_without_header(self):
        """Test that 403 without rate limit headers is not detected as rate limiting."""
        headers = {}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_is_rate_limit_403_with_x_rate_limit_remaining_variant(self):
        """Test detecting rate limit 403 with x-rate-limit-remaining header variant."""
        headers = {"x-rate-limit-remaining": "0"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_ratelimit_remaining_variant(self):
        """Test detecting rate limit 403 with ratelimit-remaining header variant."""
        headers = {"ratelimit-remaining": "0"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_app_rate_limit_remaining_variant(self):
        """Test detecting rate limit 403 with x-app-rate-limit-remaining header variant."""
        headers = {"x-app-rate-limit-remaining": "0"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_non_digit_value(self):
        """Test that non-digit remaining value is handled gracefully."""
        headers = {"x-ratelimit-remaining": "invalid"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_is_rate_limit_403_with_float_value(self):
        """Test that float remaining value is handled (converted to int)."""
        headers = {"x-ratelimit-remaining": "0.0"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_retry_after_and_rate_limit_headers(self):
        """Test detecting rate limit when retry-after is present with rate limit headers."""
        headers = {
            "retry-after": "60",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "100",  # Still has quota but retry-after suggests rate limit
        }
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is True

    def test_is_rate_limit_403_with_retry_after_only(self):
        """Test that retry-after alone without rate limit headers is not treated as rate limit."""
        headers = {"retry-after": "60"}
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_is_rate_limit_403_with_rate_limit_headers_no_retry_after(self):
        """Test that rate limit headers without retry-after and with remaining quota is not rate limit."""
        headers = {
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "100",
        }
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_is_rate_limit_403_with_retry_after_zero(self):
        """Test that retry-after with value 0 is not treated as rate limiting."""
        headers = {
            "retry-after": "0",
            "x-ratelimit-limit": "5000",
        }
        msg = "Forbidden"

        result = self.adapter._is_rate_limit_403(headers, msg)
        assert result is False

    def test_httpx_403_rate_limit_handling(self):
        """Test handling httpx 403 rate limit with exhausted quota."""

        # Create a mock HTTPStatusError class
        class MockHTTPStatusError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            "x-ratelimit-reset": "1640995200",
            "retry-after": "120",
            "x-ratelimit-remaining": "0",  # Quota is exhausted
        }

        mock_request = Mock()
        mock_request.url = "https://api.example.com/search"
        mock_request.method = "GET"

        mock_exc = MockHTTPStatusError("403 Forbidden")
        mock_exc.response = mock_response
        mock_exc.request = mock_request

        with patch("httpx.HTTPStatusError", MockHTTPStatusError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 120_000
        assert result.message == "403 Forbidden"

    def test_requests_403_rate_limit_handling(self):
        """Test handling requests 403 rate limit with exhausted quota."""

        # Create a mock HTTPError class
        class MockHTTPError(Exception):
            pass

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            "x-ratelimit-reset-ms": "30000",
            "x-ratelimit-remaining": "0",  # Quota is exhausted
        }

        mock_request = Mock()
        mock_request.url = "https://api.example.com/user/repos"
        mock_request.method = "POST"

        mock_response.request = mock_request

        mock_exc = MockHTTPError("403 Forbidden")
        mock_exc.response = mock_response

        with patch("requests.exceptions.HTTPError", MockHTTPError):
            result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, UpstreamRateLimitError)
        assert result.retry_after_ms == 30_000
        assert result.message == "403 Forbidden"
