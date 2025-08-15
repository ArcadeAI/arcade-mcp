import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from arcade_core.schema import ToolSecretItem
from arcade_tdk import BaseHttpClient, ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError


class DummyHttpClient(BaseHttpClient):
    """A dummy HTTP client implementation for testing purposes."""

    @property
    def service_name(self) -> str:
        return "dummy"

    @property
    def default_api_version(self) -> str:
        return "v1"

    @property
    def default_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "User-Agent": "DummyClient/1.0",
        }

    @property
    def base_url(self) -> str:
        return "https://api.dummy.com"

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{self.default_api_version}{path}"


@pytest.fixture
def basic_context():
    """Create a basic ToolContext without secrets."""
    return ToolContext()


@pytest.fixture
def context_with_max_requests():
    """Create a ToolContext with max concurrent requests secret."""
    return ToolContext(secrets=[ToolSecretItem(key="dummy_max_concurrent_requests", value="5")])


@pytest.fixture
def context_with_invalid_max_requests():
    """Create a ToolContext with invalid max concurrent requests secret."""
    return ToolContext(
        secrets=[ToolSecretItem(key="dummy_max_concurrent_requests", value="invalid")]
    )


class TestDummyHttpClientInitialization:
    """Test the initialization of DummyHttpClient."""

    def test_basic_initialization(self, basic_context):
        client = DummyHttpClient(basic_context)

        assert client.context == basic_context
        assert client.max_concurrent_requests == 3  # default value
        assert client._semaphore._value == 3

    def test_initialization_with_custom_max_requests(self, basic_context):
        client = DummyHttpClient(basic_context, max_concurrent_requests=10)

        assert client.max_concurrent_requests == 10
        assert client._semaphore._value == 10

    def test_initialization_with_context_max_requests(self, context_with_max_requests):
        client = DummyHttpClient(context_with_max_requests, max_concurrent_requests=3)

        # Context value should take precedence
        assert client.max_concurrent_requests == 5
        assert client._semaphore._value == 5

    def test_initialization_with_invalid_context_max_requests(
        self, context_with_invalid_max_requests
    ):
        with pytest.raises(
            ValueError, match="Invalid value set for the secret 'dummy_max_concurrent_requests'"
        ):
            DummyHttpClient(context_with_invalid_max_requests)

    def test_initialization_with_negative_max_requests(self, basic_context):
        with pytest.raises(ValueError, match="Invalid value set for 'max_concurrent_requests'"):
            DummyHttpClient(basic_context, max_concurrent_requests=-1)

    def test_initialization_with_zero_max_requests(self, basic_context):
        with pytest.raises(ValueError, match="Invalid value set for 'max_concurrent_requests'"):
            DummyHttpClient(basic_context, max_concurrent_requests=0)


class TestDummyHttpClientProperties:
    """Test the properties of DummyHttpClient."""

    def test_service_name(self, basic_context):
        client = DummyHttpClient(basic_context)
        assert client.service_name == "dummy"

    def test_default_api_version(self, basic_context):
        client = DummyHttpClient(basic_context)
        assert client.default_api_version == "v1"

    def test_default_headers(self, basic_context):
        client = DummyHttpClient(basic_context)
        expected_headers = {
            "Content-Type": "application/json",
            "User-Agent": "DummyClient/1.0",
        }
        assert client.default_headers == expected_headers

    def test_base_url(self, basic_context):
        client = DummyHttpClient(basic_context)
        assert client.base_url == "https://api.dummy.com"

    def test_build_url(self, basic_context):
        client = DummyHttpClient(basic_context)
        url = client._build_url("/test")
        assert url == "https://api.dummy.com/v1/test"

    def test_auth_token_empty(self, basic_context):
        client = DummyHttpClient(basic_context)
        assert client.auth_token == ""


class TestHttpClientRequests:
    """Test HTTP request handling."""

    @pytest.mark.asyncio
    async def test_successful_json_response(self, basic_context):
        client = DummyHttpClient(basic_context)
        mock_response_data = {"status": "success", "data": {"id": 123}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response

            result = await client.get("/test")

            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                "GET",
                "https://api.dummy.com/v1/test",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DummyClient/1.0",
                },
            )

    @pytest.mark.asyncio
    async def test_successful_non_json_response(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "plain text response"
            mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
            mock_client.request.return_value = mock_response

            result = await client.get("/test")

            assert result == {"response": "plain text response"}

    @pytest.mark.asyncio
    async def test_404_error(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {}
            mock_client.request.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await client.get("/test")

            assert "Not found error: Not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_400_error(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {}
            mock_client.request.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await client.get("/test")

            assert "Bad request error: Bad request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_429_error_without_retry_after(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limited"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {}
            mock_client.request.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await client.get("/test")

            assert "Too many requests, the service is busy. Please try again later." in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_429_error_with_retry_after_seconds(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limited"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {"Retry-After": "60"}
            mock_client.request.return_value = mock_response

            with pytest.raises(RetryableToolError) as exc_info:
                await client.get("/test")

            assert "Too many requests, the service is busy. Please try again later." in str(
                exc_info.value
            )
            assert exc_info.value.retry_after_ms == 60

    @pytest.mark.asyncio
    async def test_500_error(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {}
            mock_client.request.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await client.get("/test")

            assert "Server error: Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_503_error_with_retry_after_http_date(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = "Service unavailable"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}
            mock_client.request.return_value = mock_response

            with pytest.raises(RetryableToolError) as exc_info:
                await client.get("/test")

            assert "Server error: Service unavailable" in str(exc_info.value)
            # The retry_after should be a timestamp in milliseconds
            assert exc_info.value.retry_after_ms == 1445412480000

    @pytest.mark.asyncio
    async def test_503_error_without_retry_after(self, basic_context):
        client = DummyHttpClient(basic_context)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = "Service unavailable"
            mock_response.request.url = "https://api.dummy.com/v1/test"
            mock_response.headers = {}
            mock_client.request.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await client.get("/test")

            assert "Server error: Service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_post_request(self, basic_context):
        client = DummyHttpClient(basic_context)
        mock_response_data = {"created": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response

            result = await client.post("/create", json={"name": "test"})

            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                "POST",
                "https://api.dummy.com/v1/create",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DummyClient/1.0",
                },
                json={"name": "test"},
            )

    @pytest.mark.asyncio
    async def test_put_request(self, basic_context):
        client = DummyHttpClient(basic_context)
        mock_response_data = {"updated": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response

            result = await client.put("/update/123", json={"name": "updated"})

            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                "PUT",
                "https://api.dummy.com/v1/update/123",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DummyClient/1.0",
                },
                json={"name": "updated"},
            )

    @pytest.mark.asyncio
    async def test_delete_request(self, basic_context):
        client = DummyHttpClient(basic_context)
        mock_response_data = {"deleted": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response

            result = await client.delete("/delete/123")

            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                "DELETE",
                "https://api.dummy.com/v1/delete/123",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DummyClient/1.0",
                },
            )

    @pytest.mark.asyncio
    async def test_custom_headers_merge(self, basic_context):
        client = DummyHttpClient(basic_context)
        mock_response_data = {"success": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response

            custom_headers = {"Authorization": "Bearer token", "X-Custom": "value"}
            result = await client.get("/test", headers=custom_headers)

            expected_headers = {
                "Content-Type": "application/json",
                "User-Agent": "DummyClient/1.0",
                "Authorization": "Bearer token",
                "X-Custom": "value",
            }

            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                "GET", "https://api.dummy.com/v1/test", headers=expected_headers
            )


class TestRetryAfterHeaderParsing:
    """Test parsing of Retry-After headers."""

    def test_retry_after_seconds(self, basic_context):
        client = DummyHttpClient(basic_context)
        result = client._retry_after_header_to_milliseconds("120")
        assert result == 120

    def test_retry_after_zero_seconds(self, basic_context):
        client = DummyHttpClient(basic_context)
        result = client._retry_after_header_to_milliseconds("0")
        assert result == 0

    def test_retry_after_http_date(self, basic_context):
        client = DummyHttpClient(basic_context)
        # Wed, 21 Oct 2015 07:28:00 GMT
        result = client._retry_after_header_to_milliseconds("Wed, 21 Oct 2015 07:28:00 GMT")
        assert result == 1445412480000  # timestamp in milliseconds

    def test_retry_after_invalid_format(self, basic_context):
        client = DummyHttpClient(basic_context)
        result = client._retry_after_header_to_milliseconds("invalid")
        assert result is None

    def test_retry_after_none(self, basic_context):
        client = DummyHttpClient(basic_context)
        result = client._retry_after_header_to_milliseconds(None)
        assert result is None

    def test_retry_after_empty_string(self, basic_context):
        client = DummyHttpClient(basic_context)
        result = client._retry_after_header_to_milliseconds("")
        assert result is None


class TestConcurrencyControl:
    """Test concurrent request limiting."""

    @pytest.mark.asyncio
    async def test_concurrent_request_limit(self, basic_context):
        client = DummyHttpClient(basic_context, max_concurrent_requests=2)

        # Track when requests start and finish
        request_log = []

        async def mock_request(*_args, **_kwargs):
            request_log.append("start")
            await asyncio.sleep(0.1)  # Simulate network delay
            request_log.append("end")

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.request.side_effect = mock_request

            # Start 3 concurrent requests
            tasks = [
                asyncio.create_task(client.get("/test1")),
                asyncio.create_task(client.get("/test2")),
                asyncio.create_task(client.get("/test3")),
            ]

            await asyncio.gather(*tasks)

            # With max_concurrent_requests=2, we should see:
            # - First 2 requests start immediately
            # - Third request waits until one of the first two finishes
            assert len(request_log) == 6  # 3 start + 3 end

            # The first two requests should start before any end
            start_count = 0
            for event in request_log:
                if event == "start":
                    start_count += 1
                elif event == "end":
                    # When we see the first end, we should have seen at most 2 starts
                    assert start_count <= 2
                    break
