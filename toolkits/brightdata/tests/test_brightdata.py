from os import environ
from unittest.mock import Mock, patch

import pytest
import requests
from arcade_tdk import ToolContext, ToolSecretItem
from arcade_tdk.errors import ToolExecutionError

from arcade_brightdata.bright_data_client import BrightDataClient
from arcade_brightdata.tools.bright_data_tools import (
    DeviceType,
    SourceType,
    scrape_as_markdown,
    search_engine,
    web_data_feed,
)

BRIGHTDATA_API_KEY = environ.get("TEST_BRIGHTDATA_API_KEY") or "api-key"
BRIGHTDATA_ZONE = environ.get("TEST_BRIGHTDATA_ZONE") or "unblocker"


@pytest.fixture
def mock_context():
    context = ToolContext()
    context.secrets = []
    context.secrets.append(ToolSecretItem(key="BRIGHTDATA_API_KEY", value=BRIGHTDATA_API_KEY))
    context.secrets.append(ToolSecretItem(key="BRIGHTDATA_ZONE", value=BRIGHTDATA_ZONE))
    return context


@pytest.fixture(autouse=True)
def cleanup_engines():
    """Clean up bright data clients after each test to prevent connection leaks."""
    yield
    BrightDataClient.clear_cache()


class TestBrightDataClient:
    def test_get_instance_creates_new_client(self):
        client1 = BrightDataClient.create_client("test_key_1", "zone1")
        client2 = BrightDataClient.create_client("test_key_2", "zone2")

        assert client1 != client2
        assert client1.api_key == "test_key_1"
        assert client1.zone == "zone1"
        assert client2.api_key == "test_key_2"
        assert client2.zone == "zone2"

    def test_get_instance_returns_cached_client(self):
        client1 = BrightDataClient.create_client("test_key", "zone1")
        client2 = BrightDataClient.create_client("test_key", "zone1")

        assert client1 is client2

    def test_clear_cache(self):
        client1 = BrightDataClient.create_client("test_key", "zone1")
        BrightDataClient.clear_cache()
        client2 = BrightDataClient.create_client("test_key", "zone1")

        assert client1 is not client2

    def test_encode_query(self):
        result = BrightDataClient.encode_query("hello world test")
        assert result == "hello%20world%20test"

    @patch("requests.post")
    def test_make_request_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success response"
        mock_post.return_value = mock_response

        client = BrightDataClient("test_key", "test_zone")
        result = client.make_request({"url": "https://example.com"})

        assert result == "Success response"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_make_request_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Client Error"
        )
        mock_post.return_value = mock_response

        client = BrightDataClient("test_key", "test_zone")

        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request({"url": "https://example.com"})


class TestScrapeAsMarkdown:
    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_scrape_as_markdown_success(self, mock_engine_class, mock_context):
        mock_client = Mock()
        mock_client.make_request.return_value = "# Test Page\n\nContent here"
        mock_engine_class.create_client.return_value = mock_client

        result = scrape_as_markdown(mock_context, "https://example.com")

        assert result == "# Test Page\n\nContent here"
        mock_engine_class.create_client.assert_called_once_with(
            api_key=BRIGHTDATA_API_KEY, zone=BRIGHTDATA_ZONE
        )
        mock_client.make_request.assert_called_once_with({
            "url": "https://example.com",
            "zone": BRIGHTDATA_ZONE,
            "format": "raw",
            "data_format": "markdown",
        })


class TestSearchEngine:
    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_search_engine_google_basic(self, mock_engine_class, mock_context):
        mock_client = Mock()
        mock_client.make_request.return_value = "# Search Results\n\nResult 1\nResult 2"
        mock_engine_class.create_client.return_value = mock_client
        mock_engine_class.encode_query.return_value = "test%20query"

        result = search_engine(mock_context, "test query")

        assert result == "# Search Results\n\nResult 1\nResult 2"
        mock_engine_class.create_client.assert_called_once_with(
            api_key=BRIGHTDATA_API_KEY, zone=BRIGHTDATA_ZONE
        )

    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_search_engine_bing(self, mock_engine_class, mock_context):
        mock_client = Mock()
        mock_client.make_request.return_value = "# Bing Results"
        mock_engine_class.create_client.return_value = mock_client
        mock_engine_class.encode_query.return_value = "test%20query"

        result = search_engine(mock_context, "test query", engine="bing")

        assert result == "# Bing Results"
        expected_payload = {
            "url": "https://www.bing.com/search?q=test%20query",
            "zone": BRIGHTDATA_ZONE,
            "format": "raw",
            "data_format": "markdown",
        }
        mock_client.make_request.assert_called_once_with(expected_payload)

    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_search_engine_google_with_parameters(self, mock_engine_class, mock_context):
        mock_client = Mock()
        mock_client.make_request.return_value = "# Google Results with params"
        mock_engine_class.create_client.return_value = mock_client
        mock_engine_class.encode_query.side_effect = lambda x: x.replace(" ", "%20")

        result = search_engine(
            mock_context,
            "test query",
            language="en",
            country_code="us",
            search_type="images",
            start=10,
            num_results=20,
            location="New York",
            device=DeviceType.MOBILE,
            return_json=True,
        )

        assert result == "# Google Results with params"
        call_args = mock_client.make_request.call_args[0][0]

        assert "hl=en" in call_args["url"]
        assert "gl=us" in call_args["url"]
        assert "tbm=isch" in call_args["url"]
        assert "start=10" in call_args["url"]
        assert "num=20" in call_args["url"]
        assert "brd_mobile=1" in call_args["url"]
        assert "brd_json=1" in call_args["url"]
        assert call_args["data_format"] == "raw"

    def test_search_engine_invalid_engine(self, mock_context):
        with pytest.raises(ToolExecutionError):
            search_engine(mock_context, "test query", engine="invalid_engine")

    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_search_engine_google_jobs(self, mock_engine_class, mock_context):
        mock_client = Mock()
        mock_client.make_request.return_value = "# Job Results"
        mock_engine_class.create_client.return_value = mock_client
        mock_engine_class.encode_query.return_value = "python%20developer"

        result = search_engine(mock_context, "python developer", search_type="jobs")

        assert result == "# Job Results"
        call_args = mock_client.make_request.call_args[0][0]
        assert "ibp=htl;jobs" in call_args["url"]


class TestWebDataFeed:
    @patch("arcade_brightdata.tools.bright_data_tools._extract_structured_data")
    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_web_data_feed_success(self, mock_engine_class, mock_extract, mock_context):
        mock_client = Mock()
        mock_engine_class.create_client.return_value = mock_client
        mock_extract.return_value = {"title": "Test Product", "price": "$19.99"}

        result = web_data_feed(mock_context, "amazon_product", "https://amazon.com/dp/B08N5WRWNW")

        expected_json = '{\n  "title": "Test Product",\n  "price": "$19.99"\n}'
        assert result == expected_json

        mock_engine_class.create_client.assert_called_once_with(api_key=BRIGHTDATA_API_KEY)
        mock_extract.assert_called_once_with(
            client=mock_client,
            source_type=SourceType.AMAZON_PRODUCT,
            url="https://amazon.com/dp/B08N5WRWNW",
            num_of_reviews=None,
            timeout=600,
            polling_interval=1,
        )

    @patch("arcade_brightdata.tools.bright_data_tools._extract_structured_data")
    @patch("arcade_brightdata.tools.bright_data_tools.BrightDataClient")
    def test_web_data_feed_with_reviews(self, mock_engine_class, mock_extract, mock_context):
        mock_client = Mock()
        mock_engine_class.create_client.return_value = mock_client
        mock_extract.return_value = [{"review": "Great product!", "rating": 5}]

        result = web_data_feed(
            mock_context,
            "facebook_company_reviews",
            "https://facebook.com/company",
            num_of_reviews=50,
            timeout=300,
            polling_interval=2,
        )

        expected_json = '[\n  {\n    "review": "Great product!",\n    "rating": 5\n  }\n]'
        assert result == expected_json

        mock_extract.assert_called_once_with(
            client=mock_client,
            source_type=SourceType.FACEBOOK_COMPANY_REVIEWS,
            url="https://facebook.com/company",
            num_of_reviews=50,
            timeout=300,
            polling_interval=2,
        )


class TestExtractStructuredData:
    @patch("requests.get")
    @patch("requests.post")
    def test_extract_structured_data_success(self, mock_post, mock_get):
        from arcade_brightdata.tools.bright_data_tools import _extract_structured_data

        client = BrightDataClient("test_key", "test_zone")

        mock_trigger_response = Mock()
        mock_trigger_response.json.return_value = {"snapshot_id": "snap_123"}
        mock_post.return_value = mock_trigger_response

        mock_snapshot_response = Mock()
        mock_snapshot_response.json.return_value = {"data": "extracted_data"}
        mock_get.return_value = mock_snapshot_response

        result = _extract_structured_data(
            client=client,
            source_type=SourceType.AMAZON_PRODUCT,
            url="https://amazon.com/dp/TEST",
            timeout=10,
            polling_interval=0.1,
        )

        assert result == {"data": "extracted_data"}

        mock_post.assert_called_once()
        trigger_call = mock_post.call_args
        assert "gd_l7q7dkf244hwjntr0" in str(trigger_call)  # Amazon product dataset ID

        mock_get.assert_called_once()
        snapshot_call = mock_get.call_args
        assert "snap_123" in str(snapshot_call)

    @patch("requests.get")
    @patch("requests.post")
    def test_extract_structured_data_with_polling(self, mock_post, mock_get):
        from arcade_brightdata.tools.bright_data_tools import _extract_structured_data

        client = BrightDataClient("test_key", "test_zone")

        mock_trigger_response = Mock()
        mock_trigger_response.json.return_value = {"snapshot_id": "snap_123"}
        mock_post.return_value = mock_trigger_response

        running_response = Mock()
        running_response.json.return_value = {"status": "running"}

        complete_response = Mock()
        complete_response.json.return_value = {"data": "final_data"}

        mock_get.side_effect = [running_response, complete_response]

        result = _extract_structured_data(
            client=client,
            source_type=SourceType.LINKEDIN_PERSON_PROFILE,
            url="https://linkedin.com/in/test",
            timeout=10,
            polling_interval=0.1,
        )

        assert result == {"data": "final_data"}
        assert mock_get.call_count == 2

    @patch("requests.post")
    def test_extract_structured_data_invalid_source_type(self, mock_post):
        from arcade_brightdata.tools.bright_data_tools import _extract_structured_data

        client = BrightDataClient("test_key", "test_zone")

        # Create a mock SourceType that doesn't exist in the datasets dict
        class InvalidSourceType:
            value = "invalid_source"

        with pytest.raises(KeyError):
            _extract_structured_data(
                client=client, source_type=InvalidSourceType(), url="https://example.com"
            )

    @patch("requests.get")
    @patch("requests.post")
    def test_extract_structured_data_no_snapshot_id(self, mock_post, mock_get):
        from arcade_brightdata.tools.bright_data_tools import _extract_structured_data

        client = BrightDataClient("test_key", "test_zone")

        # Mock trigger response without snapshot_id
        mock_trigger_response = Mock()
        mock_trigger_response.json.return_value = {}
        mock_post.return_value = mock_trigger_response

        with pytest.raises(Exception) as exc_info:
            _extract_structured_data(
                client=client,
                source_type=SourceType.AMAZON_PRODUCT,
                url="https://amazon.com/dp/TEST",
            )

        assert "No snapshot ID returned from trigger request" in str(exc_info.value)

    @patch("requests.get")
    @patch("requests.post")
    @patch("time.sleep")
    def test_extract_structured_data_timeout(self, mock_sleep, mock_post, mock_get):
        from arcade_brightdata.tools.bright_data_tools import _extract_structured_data

        client = BrightDataClient("test_key", "test_zone")

        # Mock trigger response
        mock_trigger_response = Mock()
        mock_trigger_response.json.return_value = {"snapshot_id": "snap_123"}
        mock_post.return_value = mock_trigger_response

        # Mock snapshot response that always returns running
        mock_snapshot_response = Mock()
        mock_snapshot_response.json.return_value = {"status": "running"}
        mock_get.return_value = mock_snapshot_response

        with pytest.raises(TimeoutError) as exc_info:
            _extract_structured_data(
                client=client,
                source_type=SourceType.AMAZON_PRODUCT,
                url="https://amazon.com/dp/TEST",
                timeout=2,
                polling_interval=0.1,
            )

        assert "Timeout after 2 seconds waiting for amazon_product data" in str(exc_info.value)


class TestIntegration:
    """Integration tests that test the full flow without mocking internal components."""

    @patch("requests.post")
    def test_scrape_as_markdown_integration(self, mock_post, mock_context):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Integration Test\n\nThis is a test page"
        mock_post.return_value = mock_response

        result = scrape_as_markdown(mock_context, "https://example.com")

        assert result == "# Integration Test\n\nThis is a test page"

        # Verify the request was made correctly
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {BRIGHTDATA_API_KEY}"
        assert "https://api.brightdata.com/request" in str(call_args)

    @patch("requests.post")
    def test_search_engine_integration(self, mock_post, mock_context):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Search Results\n\n1. First result\n2. Second result"
        mock_post.return_value = mock_response

        result = search_engine(mock_context, "test query", engine="google")

        assert result == "# Search Results\n\n1. First result\n2. Second result"

        call_args = mock_post.call_args
        payload = call_args[1]["data"]
        assert '"url": "https://www.google.com/search?q=test%20query' in payload
        assert '"data_format": "markdown"' in payload
