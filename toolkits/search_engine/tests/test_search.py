"""Tests for base search functionality in search.py."""

import json
from unittest.mock import patch

import httpx
import pytest
from arcade_core.errors import ToolExecutionError

from arcade_search_engine.tools.search import (
    ImageSize,
    ResponseFormat,
    SafeSearchLevel,
    TimeRange,
    VideoDuration,
    get_engines,
    search,
    search_images,
    search_news,
    search_videos,
    search_with_bang,
)
from tests.conftest import MockAsyncClient, create_mock_response


class TestSearch:
    """Test cases for the main search function."""

    @pytest.mark.asyncio
    async def test_search_success(self, mock_tool_context, sample_search_response):
        """Test successful search with default parameters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(context=mock_tool_context, query="test query")
            
            # The function returns JSON string
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test query"
            assert len(parsed_result["results"]) == 2
            assert parsed_result["results"][0]["title"] == "Test Result 1"
            assert parsed_result["results"][1]["title"] == "Test Result 2"
            
            # Verify the request
            assert len(mock_client.get_calls) == 1
            call_url, call_kwargs = mock_client.get_calls[0]
            assert "search" in call_url
            assert call_kwargs["params"]["q"] == "test query"

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(self, mock_tool_context, sample_search_response):
        """Test search with all optional parameters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(
                context=mock_tool_context,
                query="test query",
                categories=["general", "images"],
                engines=["google", "bing"],
                language="en",
                page=2,  # Correct parameter name
                time_range=TimeRange.WEEK,
                safe_search=SafeSearchLevel.MODERATE,  # Correct parameter name
                format=ResponseFormat.JSON,
            )

            assert isinstance(result, str)
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test query"
            assert len(parsed_result["results"]) == 2

            # Verify the request parameters
            call_url, call_kwargs = mock_client.get_calls[0]
            params = call_kwargs["params"]
            assert params["q"] == "test query"
            assert params["categories"] == "general,images"
            assert params["engines"] == "google,bing"
            assert params["language"] == "en"
            assert params["pageno"] == 2
            assert params["time_range"] == "week"
            assert params["safesearch"] == SafeSearchLevel.MODERATE
            assert params["format"] == "json"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_tool_context, empty_response):
        """Test search with no results."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(empty_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(context=mock_tool_context, query="obscure query")
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "no results"
            assert len(parsed_result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_network_error(self, mock_tool_context):
        """Test search with network error."""
        mock_client = MockAsyncClient(
            side_effect=httpx.NetworkError("Connection failed")
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ToolExecutionError) as exc_info:
                await search(context=mock_tool_context, query="test query")
            
            assert "Connection failed" in str(exc_info.value) or "All SearXNG instances failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_http_error_non_403(self, mock_tool_context):
        """Test search with non-403 HTTP error (should try next instance)."""
        error_response = create_mock_response({}, status_code=500)
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=None, response=error_response
        )
        # Return same error for all instances
        mock_client = MockAsyncClient(responses=[error_response] * 5)  # 5 instances in PUBLIC_INSTANCES
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            # Now all instances will fail, so it should raise an error
            with pytest.raises(ToolExecutionError) as exc_info:
                await search(context=mock_tool_context, query="test query")
            
            # The error message contains the last instance that failed
            assert "Search failed" in str(exc_info.value) or "All SearXNG instances failed" in str(exc_info.value)

    @pytest.mark.parametrize(
        "time_range,expected",
        [
            (TimeRange.DAY, "day"),
            (TimeRange.WEEK, "week"),
            (TimeRange.MONTH, "month"),
            (TimeRange.YEAR, "year"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_time_ranges(
        self, mock_tool_context, sample_search_response, time_range, expected
    ):
        """Test search with different time ranges."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            await search(context=mock_tool_context, query="test", time_range=time_range)
            
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["time_range"] == expected


class TestSearchWithBang:
    """Test cases for search with bang syntax."""

    @pytest.mark.parametrize(
        "bang,query",
        [
            ("!g", "test query"),
            ("!ddg", "another test"),
            ("!bi", "bing search"),
            ("!w", "wikipedia search"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_with_bang_success(self, mock_tool_context, sample_search_response, bang, query):
        """Test successful search with various bang syntaxes."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_with_bang(
                context=mock_tool_context, query=query, bang=bang
            )
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test query"
            assert len(parsed_result["results"]) == 2
            
            # Verify the bang was added to the query
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == f"{bang} {query}"


class TestGetEngines:
    """Test cases for get_engines function."""

    @pytest.mark.asyncio
    async def test_get_engines_success(self, mock_tool_context, sample_engines_response):
        """Test successful retrieval of engines."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_engines_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await get_engines(context=mock_tool_context)
            
            parsed_result = json.loads(result)
            assert len(parsed_result) == 8
            engine_names = [e["name"] for e in parsed_result]
            assert "google" in engine_names
            assert "bing" in engine_names

    @pytest.mark.asyncio
    async def test_get_engines_error_handling(self, mock_tool_context):
        """Test error handling in get_engines."""
        mock_client = MockAsyncClient(
            side_effect=httpx.NetworkError("Connection failed")
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ToolExecutionError) as exc_info:
                await get_engines(context=mock_tool_context)
            
            assert "Failed to get engines" in str(exc_info.value)


class TestSearchImages:
    """Test cases for image search."""

    @pytest.mark.asyncio
    async def test_search_images_success(self, mock_tool_context, sample_image_search_response):
        """Test successful image search."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_image_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_images(context=mock_tool_context, query="test image")
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test image"
            assert len(parsed_result["results"]) == 2
            assert parsed_result["results"][0]["title"] == "Test Image 1"
            assert parsed_result["results"][0]["resolution"] == "1920x1080"

    @pytest.mark.parametrize(
        "size,expected_query",
        [
            (ImageSize.SMALL, "test image size:small"),
            (ImageSize.MEDIUM, "test image size:medium"),
            (ImageSize.LARGE, "test image size:large"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_images_with_size_filter(
        self, mock_tool_context, sample_image_search_response, size, expected_query
    ):
        """Test image search with various size filters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_image_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_images(
                context=mock_tool_context, query="test image", size=size
            )
            
            # Verify size filter was added to query
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == expected_query


class TestSearchVideos:
    """Test cases for video search."""

    @pytest.mark.asyncio
    async def test_search_videos_success(self, mock_tool_context, sample_video_search_response):
        """Test successful video search."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_video_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_videos(context=mock_tool_context, query="test video")
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test video"
            assert len(parsed_result["results"]) == 2
            assert parsed_result["results"][0]["title"] == "Test Video 1"
            assert parsed_result["results"][0]["author"] == "Test Channel"

    @pytest.mark.parametrize(
        "duration,expected_query",
        [
            (VideoDuration.SHORT, "test video duration:short"),
            (VideoDuration.MEDIUM, "test video duration:medium"),
            (VideoDuration.LONG, "test video duration:long"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_videos_with_duration_filter(
        self, mock_tool_context, sample_video_search_response, duration, expected_query
    ):
        """Test video search with various duration filters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_video_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_videos(
                context=mock_tool_context,
                query="test video",
                duration=duration,
            )
            
            # Verify duration filter was added to query
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == expected_query


class TestSearchNews:
    """Test cases for news search."""

    @pytest.mark.asyncio
    async def test_search_news_success(self, mock_tool_context, sample_news_search_response):
        """Test successful news search."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_news_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_news(context=mock_tool_context, query="test news")
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "test news"
            assert len(parsed_result["results"]) == 2
            assert parsed_result["results"][0]["title"] == "Breaking: Test News Article 1"
            assert parsed_result["results"][0]["source"] == "Example News"

    @pytest.mark.parametrize(
        "time_range",
        [TimeRange.DAY, TimeRange.WEEK, TimeRange.MONTH, TimeRange.YEAR],
    )
    @pytest.mark.asyncio
    async def test_search_news_with_time_range(
        self, mock_tool_context, sample_news_search_response, time_range
    ):
        """Test news search with different time range filters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_news_search_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_news(
                context=mock_tool_context, query="test news", time_range=time_range
            )
            
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["time_range"] == time_range.value

    @pytest.mark.asyncio
    async def test_search_news_no_results(self, mock_tool_context, empty_response):
        """Test news search with no results."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(empty_response)]
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await search_news(context=mock_tool_context, query="obscure news")
            
            parsed_result = json.loads(result)
            assert parsed_result["query"] == "no results"
            assert len(parsed_result["results"]) == 0


class TestErrorHandling:
    """Test error handling across all search functions."""

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_tool_context):
        """Test handling of invalid JSON response."""
        # Create a response that will fail JSON parsing
        bad_response = create_mock_response({})
        bad_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        # Return same error for all instances
        mock_client = MockAsyncClient(responses=[bad_response] * 5)  # 5 instances in PUBLIC_INSTANCES
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            # Should raise error when JSON parsing fails on all instances
            with pytest.raises(ToolExecutionError) as exc_info:
                await search(context=mock_tool_context, query="test")
            
            # The error message contains the last instance that failed
            assert "Search failed" in str(exc_info.value) or "All SearXNG instances failed" in str(exc_info.value)

    @pytest.mark.parametrize(
        "error_type,error_message",
        [
            (httpx.TimeoutException, "Request timed out"),
            (httpx.NetworkError, "Network connection failed"),
            (httpx.ConnectError, "Connection refused"),
        ],
    )
    @pytest.mark.asyncio
    async def test_various_network_errors(self, mock_tool_context, error_type, error_message):
        """Test handling of various network errors."""
        mock_client = MockAsyncClient(
            side_effect=error_type(error_message)
        )
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ToolExecutionError) as exc_info:
                await search(context=mock_tool_context, query="test")
            
            # The error message contains the instance that failed
            assert "Search failed" in str(exc_info.value) or error_message in str(exc_info.value)