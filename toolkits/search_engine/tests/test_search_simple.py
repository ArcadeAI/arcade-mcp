"""Simplified tests for search functionality to verify basic operation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_core.errors import ToolExecutionError

from arcade_search_engine.tools.search import (
    ResponseFormat,
    TimeRange,
    get_engines,
    search,
    search_with_bang,
)


@pytest.fixture
def mock_response_success():
    """Create a successful mock response."""
    return {
        "query": "test query",
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
                "engines": ["google"],
                "score": 1.0,
            }
        ],
        "number_of_results": 1,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }


@pytest.fixture
def mock_httpx_success(mock_response_success):
    """Create a properly mocked httpx client for successful responses."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_success
    mock_response.raise_for_status = MagicMock()
    mock_response.text = "html content"
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    return mock_context


class TestBasicSearch:
    """Basic tests for search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_returns_json(self, mock_httpx_success):
        """Test that search returns valid JSON."""
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_httpx_success):
            from arcade_tdk import ToolContext
            context = MagicMock(spec=ToolContext)
            
            result = await search(context=context, query="test query")
            
            # Should return valid JSON
            parsed = json.loads(result)
            assert parsed["query"] == "test query"
            assert len(parsed["results"]) == 1
            assert parsed["results"][0]["title"] == "Test Result"
    
    @pytest.mark.asyncio
    async def test_search_with_bang_adds_bang(self, mock_httpx_success):
        """Test that search_with_bang prepends the bang to query."""
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_httpx_success):
            from arcade_tdk import ToolContext
            context = MagicMock(spec=ToolContext)
            
            result = await search_with_bang(context=context, query="test", bang="!g")
            
            # Check that the bang was added to the query
            mock_httpx_success.__aenter__.return_value.get.assert_called_once()
            call_args = mock_httpx_success.__aenter__.return_value.get.call_args
            assert call_args[1]["params"]["q"] == "!g test"
    
    @pytest.mark.asyncio
    async def test_get_engines_returns_json(self):
        """Test that get_engines returns valid JSON."""
        mock_engines = [
            {"name": "google", "categories": ["general"], "enabled": True},
            {"name": "bing", "categories": ["general"], "enabled": True},
        ]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_engines
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_context):
            from arcade_tdk import ToolContext
            context = MagicMock(spec=ToolContext)
            
            result = await get_engines(context=context)
            
            # Should return valid JSON
            parsed = json.loads(result)
            assert len(parsed) == 2
            assert parsed[0]["name"] == "google"
    
    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """Test that search handles network errors properly."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_context):
            from arcade_tdk import ToolContext
            context = MagicMock(spec=ToolContext)
            
            with pytest.raises(ToolExecutionError) as exc_info:
                await search(context=context, query="test")
            
            assert "Network error" in str(exc_info.value) or "All SearXNG instances failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_parameters(self, mock_httpx_success):
        """Test that search passes parameters correctly."""
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_httpx_success):
            from arcade_tdk import ToolContext
            context = MagicMock(spec=ToolContext)
            
            await search(
                context=context,
                query="test",
                engines=["google", "bing"],
                categories=["general", "news"],
                language="fr",
                time_range=TimeRange.WEEK,
                safe_search=2,
                page=3,
            )
            
            # Check parameters were passed correctly
            mock_httpx_success.__aenter__.return_value.get.assert_called_once()
            call_args = mock_httpx_success.__aenter__.return_value.get.call_args
            params = call_args[1]["params"]
            
            assert params["q"] == "test"
            assert params["engines"] == "google,bing"
            assert params["categories"] == "general,news"
            assert params["language"] == "fr"
            assert params["time_range"] == "week"
            assert params["safesearch"] == 2
            assert params["pageno"] == 3


class TestSearchIntegration:
    """Integration tests that verify the search tools work together."""
    
    @pytest.mark.asyncio
    async def test_popular_engine_integration(self, mock_httpx_success):
        """Test that popular engine functions work with mocked search."""
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_httpx_success):
            from arcade_tdk import ToolContext
            from arcade_search_engine.tools.popular_engines import google_search
            
            context = MagicMock(spec=ToolContext)
            result = await google_search(context=context, query="test")
            
            # Should return valid JSON
            parsed = json.loads(result)
            assert "results" in parsed
    
    @pytest.mark.asyncio
    async def test_academic_tools_integration(self):
        """Test that academic tools handle responses correctly."""
        # Create multiple mock responses for different search calls
        responses = []
        for i in range(3):  # We'll need multiple responses
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{"title": f"Paper {i}", "url": f"https://example.com/{i}"}],
                "number_of_results": 1,
            }
            mock_response.raise_for_status = MagicMock()
            responses.append(mock_response)
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=responses)
        
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        
        # Need to patch at the module level since academic.py imports these
        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_context):
            from arcade_tdk import ToolContext
            from arcade_search_engine.tools.academic import research_papers, ResearchSource
            
            context = MagicMock(spec=ToolContext)
            result = await research_papers(
                context=context,
                topic="test topic",
                sources=[ResearchSource.ARXIV],
            )
            
            # Should return valid JSON with aggregated results
            parsed = json.loads(result)
            assert parsed["query"] == "test topic"
            assert "sources" in parsed