import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from arcade_core.errors import (
    ErrorKind,
    FatalToolError,
    NetworkTransportError,
    UpstreamError,
    UpstreamRateLimitError,
)
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

    def test_requests_http_error_no_response_is_network_transport(self):
        """HTTPError with no response means we never received a complete response."""

        import requests

        class MockHTTPError(requests.exceptions.HTTPError):
            pass

        mock_exc = MockHTTPError("No response")
        mock_exc.response = None

        result = self.adapter.from_exception(mock_exc)

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
        assert result.can_retry is True
        assert result.status_code is None
        assert result.extra["error_type"] == "MockHTTPError"

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


class TestHTTPXExceptionRouting:
    """Verify httpx exception routing — network-transport failures that never
    received a response must not be classified as UpstreamError, and
    client-construction bugs must become FatalToolError."""

    def setup_method(self):
        self.adapter = HTTPErrorAdapter()

    def test_pool_timeout_routes_to_network_transport_timeout(self):
        import httpx

        result = self.adapter.from_exception(httpx.PoolTimeout("pool exhausted"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
        assert result.can_retry is True
        assert result.status_code is None
        assert result.extra["error_type"] == "PoolTimeout"
        assert result.extra["service"] == "_http"

    def test_connect_timeout_routes_to_network_transport_timeout(self):
        import httpx

        result = self.adapter.from_exception(httpx.ConnectTimeout("deadline"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
        assert result.can_retry is True

    def test_connect_error_routes_to_network_transport_unreachable(self):
        import httpx

        result = self.adapter.from_exception(httpx.ConnectError("refused"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE
        assert result.can_retry is True

    def test_remote_protocol_error_is_network_transport(self):
        """Upstream sent malformed HTTP — not reachable in a usable way."""
        import httpx

        result = self.adapter.from_exception(httpx.RemoteProtocolError("garbage"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE

    def test_unsupported_protocol_routes_to_fatal_tool_error(self):
        """Construction bug — tool used a scheme httpx doesn't support."""
        import httpx

        result = self.adapter.from_exception(httpx.UnsupportedProtocol("ftp://"))

        assert isinstance(result, FatalToolError)
        assert result.kind == ErrorKind.TOOL_RUNTIME_FATAL
        assert result.status_code == 500
        assert result.extra["error_type"] == "UnsupportedProtocol"

    def test_invalid_url_routes_to_fatal_tool_error(self):
        """Construction bug — tool built a URL httpx can't parse.

        Note: httpx.InvalidURL is NOT a RequestError subclass, so this also
        verifies the adapter checks construction bugs before the RequestError
        short-circuit."""
        import httpx

        result = self.adapter.from_exception(httpx.InvalidURL("bad"))

        assert isinstance(result, FatalToolError)
        assert result.extra["error_type"] == "InvalidURL"

    def test_local_protocol_error_routes_to_fatal_tool_error(self):
        """LocalProtocolError = our HTTP framing was invalid (construction bug)."""
        import httpx

        result = self.adapter.from_exception(httpx.LocalProtocolError("bad"))

        assert isinstance(result, FatalToolError)

    def test_decoding_error_routes_to_network_transport_unmapped(self):
        """Response body couldn't be decoded — transport-level, retryable."""
        import httpx

        result = self.adapter.from_exception(httpx.DecodingError("bad gzip"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
        assert result.can_retry is True

    def test_too_many_redirects_is_non_retryable(self):
        """Redirect loop — retrying the same chain will loop again."""
        import httpx

        result = self.adapter.from_exception(httpx.TooManyRedirects("loop"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
        assert result.can_retry is False


class TestRequestsExceptionRouting:
    """Verify requests exception routing — mirrors TestHTTPXExceptionRouting."""

    def setup_method(self):
        self.adapter = HTTPErrorAdapter()

    def test_connect_timeout_routes_to_network_transport_timeout(self):
        """ConnectTimeout inherits from both Timeout and ConnectionError —
        must be classified as a timeout, not unreachable."""
        import requests

        result = self.adapter.from_exception(requests.exceptions.ConnectTimeout("x"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
        assert result.can_retry is True

    def test_read_timeout_routes_to_network_transport_timeout(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.ReadTimeout("x"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT

    def test_connection_error_routes_to_network_transport_unreachable(self):
        """Plain ConnectionError (non-SSL, non-timeout) — upstream unreachable."""
        import requests

        result = self.adapter.from_exception(requests.exceptions.ConnectionError("refused"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNREACHABLE
        assert result.can_retry is True

    def test_ssl_error_routes_to_fatal_tool_error(self):
        """TLS/SSL failures are typically cert/trust config issues, not transient."""
        import requests

        result = self.adapter.from_exception(requests.exceptions.SSLError("bad cert"))

        assert isinstance(result, FatalToolError)
        assert "TLS" in result.message
        assert result.extra["error_type"] == "SSLError"

    def test_missing_schema_routes_to_fatal_tool_error(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.MissingSchema("x"))

        assert isinstance(result, FatalToolError)

    def test_invalid_schema_routes_to_fatal_tool_error(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.InvalidSchema("x"))

        assert isinstance(result, FatalToolError)

    def test_invalid_url_routes_to_fatal_tool_error(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.InvalidURL("x"))

        assert isinstance(result, FatalToolError)

    def test_invalid_header_routes_to_fatal_tool_error(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.InvalidHeader("bad"))

        assert isinstance(result, FatalToolError)

    def test_content_decoding_error_routes_to_network_transport_unmapped(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.ContentDecodingError("x"))

        assert isinstance(result, NetworkTransportError)
        assert result.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
        assert result.can_retry is True

    def test_too_many_redirects_is_non_retryable(self):
        import requests

        result = self.adapter.from_exception(requests.exceptions.TooManyRedirects("loop"))

        assert isinstance(result, NetworkTransportError)
        assert result.can_retry is False


class TestNetworkTransportErrorClass:
    """Unit tests for the NetworkTransportError class itself."""

    def test_defaults(self):
        err = NetworkTransportError("boom")
        assert err.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_UNMAPPED
        assert err.can_retry is True
        assert err.status_code is None
        assert err.is_network_transport_error is True
        assert err.is_upstream_error is False
        assert err.is_tool_error is False

    def test_explicit_kind_and_retry(self):
        err = NetworkTransportError(
            "timeout",
            kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
            can_retry=True,
        )
        assert err.kind == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
        assert err.can_retry is True

    def test_rejects_non_network_kind(self):
        import pytest

        with pytest.raises(ValueError, match="NETWORK_TRANSPORT_"):
            NetworkTransportError("x", kind=ErrorKind.TOOL_RUNTIME_FATAL)

    def test_payload_omits_status_code(self):
        err = NetworkTransportError(
            "timeout",
            kind=ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT,
            can_retry=True,
            extra={"error_type": "PoolTimeout"},
        )
        payload = err.to_payload()
        assert payload["status_code"] is None
        assert payload["kind"] == ErrorKind.NETWORK_TRANSPORT_RUNTIME_TIMEOUT
        assert payload["can_retry"] is True
        assert payload["error_type"] == "PoolTimeout"
