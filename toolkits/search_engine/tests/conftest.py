"""Shared test fixtures and configuration for search engine tests."""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_tdk import ToolContext


class MockAsyncClient:
    """Mock httpx AsyncClient with proper async context manager support."""
    
    def __init__(self, responses=None, side_effect=None):
        self.responses = responses or []
        self.side_effect = side_effect
        self.call_count = 0
        self.get_calls = []
        self.post_calls = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None
        
    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        
        if self.side_effect:
            raise self.side_effect
            
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        else:
            # Default response
            return self._create_response({"results": []})
    
    async def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return await self.get(url, **kwargs)
    
    def _create_response(self, data, status_code=200):
        """Create a mock response object."""
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = data
        response.raise_for_status = MagicMock()
        response.text = json.dumps(data)
        return response


def create_mock_response(data: Dict[str, Any], status_code: int = 200) -> MagicMock:
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    response.text = json.dumps(data)
    return response


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext for testing."""
    context = MagicMock(spec=ToolContext)
    context.user_id = "test_user"
    context.session_id = "test_session"
    return context


@pytest.fixture
def sample_search_response():
    """Sample search response from SearXNG."""
    return {
        "query": "test query",
        "results": [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "content": "This is a test result",
                "engine": "google",
                "parsed_url": ["https", "example.com", "/1", "", "", ""],
                "engines": ["google", "bing"],
                "positions": [1, 2],
                "score": 2.0,
                "category": "general",
            },
            {
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "content": "Another test result",
                "engine": "duckduckgo",
                "parsed_url": ["https", "example.com", "/2", "", "", ""],
                "engines": ["duckduckgo"],
                "positions": [1],
                "score": 1.0,
                "category": "general",
            },
        ],
        "number_of_results": 2,
        "suggestions": ["test query suggestion"],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
        "engine_data": {
            "google": {"search_url": "https://google.com/search?q=test+query"},
            "bing": {"search_url": "https://bing.com/search?q=test+query"},
            "duckduckgo": {"search_url": "https://duckduckgo.com/?q=test+query"},
        },
    }


@pytest.fixture
def sample_image_search_response():
    """Sample image search response from SearXNG."""
    return {
        "query": "test image",
        "results": [
            {
                "url": "https://example.com/image1.jpg",
                "title": "Test Image 1",
                "content": "",
                "img_src": "https://example.com/thumb1.jpg",
                "thumbnail_src": "https://example.com/thumb1_small.jpg",
                "resolution": "1920x1080",
                "engine": "google images",
                "engines": ["google images"],
                "positions": [1],
                "score": 1.0,
                "category": "images",
                "img_format": "jpeg",
                "source": "https://example.com/page1",
            },
            {
                "url": "https://example.com/image2.png",
                "title": "Test Image 2",
                "content": "",
                "img_src": "https://example.com/thumb2.png",
                "thumbnail_src": "https://example.com/thumb2_small.png",
                "resolution": "800x600",
                "engine": "bing images",
                "engines": ["bing images"],
                "positions": [1],
                "score": 1.0,
                "category": "images",
                "img_format": "png",
                "source": "https://example.com/page2",
            },
        ],
        "number_of_results": 2,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }


@pytest.fixture
def sample_video_search_response():
    """Sample video search response from SearXNG."""
    return {
        "query": "test video",
        "results": [
            {
                "url": "https://youtube.com/watch?v=test1",
                "title": "Test Video 1",
                "content": "A test video description",
                "thumbnail": "https://i.ytimg.com/vi/test1/default.jpg",
                "publishedDate": "2024-01-01T00:00:00",
                "author": "Test Channel",
                "length": "10:30",
                "duration": 630,
                "engine": "youtube",
                "engines": ["youtube"],
                "positions": [1],
                "score": 1.0,
                "category": "videos",
                "embedded": True,
            },
            {
                "url": "https://vimeo.com/test2",
                "title": "Test Video 2",
                "content": "Another test video",
                "thumbnail": "https://vimeo.com/thumb2.jpg",
                "publishedDate": "2024-01-02T00:00:00",
                "author": "Test User",
                "length": "5:45",
                "duration": 345,
                "engine": "vimeo",
                "engines": ["vimeo"],
                "positions": [1],
                "score": 1.0,
                "category": "videos",
                "embedded": False,
            },
        ],
        "number_of_results": 2,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }


@pytest.fixture
def sample_news_search_response():
    """Sample news search response from SearXNG."""
    return {
        "query": "test news",
        "results": [
            {
                "url": "https://news.example.com/article1",
                "title": "Breaking: Test News Article 1",
                "content": "This is a test news article about recent events.",
                "publishedDate": "2024-01-15T12:00:00",
                "author": "Test Reporter",
                "engine": "google news",
                "engines": ["google news"],
                "positions": [1],
                "score": 1.0,
                "category": "news",
                "thumbnail": "https://news.example.com/thumb1.jpg",
                "source": "Example News",
            },
            {
                "url": "https://news.example.com/article2",
                "title": "Update: Test News Article 2",
                "content": "Another test news article with updates.",
                "publishedDate": "2024-01-14T18:30:00",
                "author": "Another Reporter",
                "engine": "bing news",
                "engines": ["bing news"],
                "positions": [1],
                "score": 1.0,
                "category": "news",
                "thumbnail": "https://news.example.com/thumb2.jpg",
                "source": "Example Daily",
            },
        ],
        "number_of_results": 2,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }


@pytest.fixture
def sample_engines_response():
    """Sample engines list response from SearXNG."""
    return [
        {"name": "google", "categories": ["general", "images", "videos", "news"], "enabled": True},
        {"name": "bing", "categories": ["general", "images", "videos", "news"], "enabled": True},
        {"name": "duckduckgo", "categories": ["general", "images"], "enabled": True},
        {"name": "wikipedia", "categories": ["general"], "enabled": True},
        {"name": "youtube", "categories": ["videos"], "enabled": True},
        {"name": "pubmed", "categories": ["science"], "enabled": True},
        {"name": "arxiv", "categories": ["science"], "enabled": True},
        {"name": "github", "categories": ["it"], "enabled": True},
    ]


@pytest.fixture
def sample_academic_response():
    """Sample academic search response."""
    return {
        "query": "machine learning",
        "results": [
            {
                "title": "Deep Learning in Computer Vision",
                "url": "https://arxiv.org/abs/2024.12345",
                "content": "A comprehensive survey of deep learning techniques...",
                "authors": "Smith, J., Doe, A.",
                "publishedDate": "2024-01-15",
                "engine": "arxiv",
                "engines": ["arxiv"],
                "positions": [1],
                "score": 1.0,
                "category": "science",
                "abstract": "This paper presents a comprehensive survey...",
                "pdf_url": "https://arxiv.org/pdf/2024.12345.pdf",
            },
            {
                "title": "Neural Networks for Natural Language Processing",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
                "content": "Recent advances in neural network architectures...",
                "authors": "Johnson, B., Williams, C.",
                "publishedDate": "2024-01-10",
                "engine": "pubmed",
                "engines": ["pubmed"],
                "positions": [1],
                "score": 1.0,
                "category": "science",
                "doi": "10.1234/journal.2024.12345",
            },
        ],
        "number_of_results": 2,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }


@pytest.fixture
def empty_response():
    """Empty search response."""
    return {
        "query": "no results",
        "results": [],
        "number_of_results": 0,
        "suggestions": [],
        "answers": [],
        "corrections": [],
        "infoboxes": [],
    }