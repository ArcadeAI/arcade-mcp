"""Tests for popular search engine tools."""

import json
from unittest.mock import patch

import httpx
import pytest
from arcade_core.errors import ToolExecutionError
from arcade_search_engine.tools.popular_engines import (
    MastodonSearchType,
    TranslationEngine,
    arxiv_search,
    bing_search,
    brave_search,
    duckduckgo_search,
    github_search,
    google_search,
    mastodon_search,
    npm_search,
    openstreetmap_search,
    piratebay_search,
    pubmed_search,
    pypi_search,
    reddit_search,
    soundcloud_search,
    stackoverflow_search,
    startpage_search,
    translate_text,
    wikipedia_search,
    wiktionary_search,
    youtube_search,
)
from arcade_search_engine.tools.search import TimeRange

from tests.conftest import MockAsyncClient, create_mock_response


class TestWebSearchEngines:
    """Test cases for web search engine functions."""

    @pytest.mark.parametrize(
        "search_func,bang,func_name",
        [
            (google_search, "!g", "Google"),
            (duckduckgo_search, "!ddg", "DuckDuckGo"),
            (brave_search, "!br", "Brave"),
            (bing_search, "!bi", "Bing"),
            (startpage_search, "!sp", "Startpage"),
        ],
    )
    @pytest.mark.asyncio
    async def test_web_search_engines_basic(
        self, mock_tool_context, sample_search_response, search_func, bang, func_name
    ):
        """Test basic web search engine functions."""
        # Modify response to include the func_name
        modified_response = sample_search_response.copy()
        modified_response["results"][0]["title"] = f"{func_name} Result"
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await search_func(context=mock_tool_context, query="test query")

            # Verify the bang was added to the query
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == f"{bang} test query"
            assert f"{func_name} Result" in result

    @pytest.mark.asyncio
    async def test_google_search_with_all_params(
        self, mock_tool_context, sample_search_response
    ):
        """Test Google search with all parameters."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await google_search(
                context=mock_tool_context,
                query="advanced search",
                language="fr",
                safe_search=2,
                time_range=TimeRange.WEEK,
                page=2,
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            params = call_kwargs["params"]
            assert params["q"] == "!g advanced search"
            assert params["language"] == "fr"
            assert params["safesearch"] == 2
            assert params["pageno"] == 2

    @pytest.mark.parametrize(
        "search_func",
        [
            google_search,
            duckduckgo_search,
            bing_search,
            brave_search,
            startpage_search,
        ],
    )
    @pytest.mark.asyncio
    async def test_search_engine_error_handling(self, mock_tool_context, search_func):
        """Test error handling in search engine functions."""
        mock_client = MockAsyncClient(side_effect=httpx.NetworkError("Search failed"))

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(ToolExecutionError) as exc_info:
                await search_func(context=mock_tool_context, query="test")

            assert "Search failed" in str(exc_info.value)


class TestSpecializedSearchEngines:
    """Test cases for specialized search engine functions."""

    @pytest.mark.parametrize(
        "search_func,bang,expected_content",
        [
            (
                wikipedia_search,
                "!wp",
                "Wikipedia article",
            ),  # Correct bang for Wikipedia
            (wiktionary_search, "!wt", "Definition"),
            (arxiv_search, "!arx", "Research paper"),
            (pubmed_search, "!pubmed", "Medical study"),
            (github_search, "!gh", "Repository"),
            (stackoverflow_search, "!so", "Answer"),
            (npm_search, "!npm", "Package"),
            (pypi_search, "!pypi", "Python package"),
        ],
    )
    @pytest.mark.asyncio
    async def test_specialized_search_engines(
        self,
        mock_tool_context,
        sample_search_response,
        search_func,
        bang,
        expected_content,
    ):
        """Test specialized search engine functions."""
        # Modify response for test
        modified_response = sample_search_response.copy()
        modified_response["results"][0]["title"] = expected_content
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await search_func(context=mock_tool_context, query="test query")

            # Verify bang was prepended
            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == f"{bang} test query"
            assert expected_content in result

    @pytest.mark.asyncio
    async def test_wikipedia_search_with_language(
        self, mock_tool_context, sample_search_response
    ):
        """Test Wikipedia search with language parameter."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0]["title"] = "Article en français"
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await wikipedia_search(
                context=mock_tool_context, query="Paris", language="fr"
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == "!wp Paris"  # Correct Wikipedia bang
            assert call_kwargs["params"]["language"] == "fr"


class TestMediaSearchEngines:
    """Test cases for media search engine functions."""

    @pytest.mark.asyncio
    async def test_youtube_search(self, mock_tool_context, sample_search_response):
        """Test YouTube search function."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=test",
            "author": "Test Channel",
            "duration": "10:30",
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await youtube_search(
                context=mock_tool_context,
                query="test video",
                safe_search=2,
                page=1,
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            params = call_kwargs["params"]
            assert params["q"] == "!yt test video"
            assert params["safesearch"] == 2
            assert params["pageno"] == 1
            assert "Test Video" in result

    @pytest.mark.asyncio
    async def test_soundcloud_search(self, mock_tool_context, sample_search_response):
        """Test SoundCloud search function."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "Test Track",
            "author": "Test Artist",
            "duration": "3:45",
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await soundcloud_search(
                context=mock_tool_context, query="test music"
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == "!sc test music"
            assert "Test Track" in result


class TestTranslationFunction:
    """Test cases for translation function."""

    @pytest.mark.asyncio
    async def test_translate_text_basic(
        self, mock_tool_context, sample_search_response
    ):
        """Test basic translation functionality."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0]["title"] = "Bonjour le monde"
        modified_response["results"][0]["content"] = "Translation: Bonjour le monde"
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await translate_text(
                context=mock_tool_context,
                text="Hello world",
                source_language="en",
                target_language="fr",
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            # Default engine is LINGVA with bang !lv
            assert call_kwargs["params"]["q"] == "!lv en:fr Hello world"
            assert "Bonjour le monde" in result

    @pytest.mark.parametrize(
        "engine,expected_bang",
        [
            (TranslationEngine.LINGVA, "!lv"),
            (TranslationEngine.LIBRETRANSLATE, "!lt"),
            (TranslationEngine.MOZHI, "!mz"),
            (TranslationEngine.MYMEMORY, "!tl"),
        ],
    )
    @pytest.mark.asyncio
    async def test_translate_text_engines(
        self, mock_tool_context, sample_search_response, engine, expected_bang
    ):
        """Test translation with different engines."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await translate_text(
                context=mock_tool_context,
                text="Hello",
                source_language="en",
                target_language="es",
                engine=engine,
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == f"{expected_bang} en:es Hello"

    @pytest.mark.asyncio
    async def test_translate_text_auto_detect(
        self, mock_tool_context, sample_search_response
    ):
        """Test translation with auto-detect source language."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await translate_text(
                context=mock_tool_context,
                text="Hello",
                source_language="auto",
                target_language="es",
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == "!lv auto:es Hello"


class TestLocationSearchEngines:
    """Test cases for location-based search engines."""

    @pytest.mark.asyncio
    async def test_openstreetmap_search(
        self, mock_tool_context, sample_search_response
    ):
        """Test OpenStreetMap search function."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "Eiffel Tower",
            "content": "Paris, France",
            "url": "https://www.openstreetmap.org/?mlat=48.8584&mlon=2.2945",
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await openstreetmap_search(
                context=mock_tool_context,
                query="Eiffel Tower",
                language="en",
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            params = call_kwargs["params"]
            assert params["q"] == "!osm Eiffel Tower"
            assert params["language"] == "en"
            assert "Eiffel Tower" in result
            assert "Paris, France" in result


class TestSocialMediaSearchEngines:
    """Test cases for social media search engines."""

    @pytest.mark.asyncio
    async def test_reddit_search(self, mock_tool_context, sample_search_response):
        """Test Reddit search function."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "Test post on r/test",
            "content": "This is a test post",
            "author": "testuser",
            "subreddit": "r/test",
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await reddit_search(context=mock_tool_context, query="test post")

            call_url, call_kwargs = mock_client.get_calls[0]
            assert (
                call_kwargs["params"]["q"] == "!re test post"
            )  # Correct Reddit bang
            assert "Test post on r/test" in result

    @pytest.mark.asyncio
    async def test_mastodon_search_hashtags(
        self, mock_tool_context, sample_search_response
    ):
        """Test Mastodon search for hashtags."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "#testtag",
            "content": "Posts with this hashtag",
            "instances": ["mastodon.social"],
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await mastodon_search(
                context=mock_tool_context,
                query="testtag",
                search_type=MastodonSearchType.HASHTAGS,
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == "!mah testtag"
            assert "#testtag" in result

    @pytest.mark.parametrize(
        "search_type,expected_bang",
        [
            (MastodonSearchType.HASHTAGS, "!mah"),
            (MastodonSearchType.USERS, "!mau"),
        ],
    )
    @pytest.mark.asyncio
    async def test_mastodon_search_types(
        self, mock_tool_context, sample_search_response, search_type, expected_bang
    ):
        """Test Mastodon search with different search types."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await mastodon_search(
                context=mock_tool_context,
                query="test",
                search_type=search_type,
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == f"{expected_bang} test"


class TestTorrentSearchEngines:
    """Test cases for torrent search engines."""

    @pytest.mark.asyncio
    async def test_piratebay_search(self, mock_tool_context, sample_search_response):
        """Test PirateBay search function."""
        modified_response = sample_search_response.copy()
        modified_response["results"][0] = {
            "title": "Test Content",
            "seeds": "100",
            "leeches": "10",
            "size": "1.5 GB",
            "uploaded": "2024-01-15",
        }
        mock_client = MockAsyncClient(
            responses=[create_mock_response(modified_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await piratebay_search(
                context=mock_tool_context, query="test content"
            )

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"] == "!tpb test content"
            assert "Test Content" in result


class TestErrorScenarios:
    """Test error scenarios across all popular engines."""

    @pytest.mark.asyncio
    async def test_empty_results_handling(self, mock_tool_context, empty_response):
        """Test handling of empty results."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(empty_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await google_search(
                context=mock_tool_context, query="nonexistent query"
            )

            parsed_result = json.loads(result)
            assert parsed_result["results"] == []

    @pytest.mark.asyncio
    async def test_network_error_propagation(self, mock_tool_context):
        """Test that network errors are properly propagated."""
        mock_client = MockAsyncClient(side_effect=httpx.NetworkError("Network error"))

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(ToolExecutionError) as exc_info:
                await duckduckgo_search(context=mock_tool_context, query="test")

            assert "Network error" in str(
                exc_info.value
            ) or "All SearXNG instances failed" in str(exc_info.value)

    @pytest.mark.parametrize(
        "search_func,expected_bang",
        [
            (google_search, "!g"),
            (wikipedia_search, "!wp"),
            (reddit_search, "!re"),
            (github_search, "!gh"),
            (youtube_search, "!yt"),
        ],
    )
    @pytest.mark.asyncio
    async def test_bang_consistency(
        self, mock_tool_context, sample_search_response, search_func, expected_bang
    ):
        """Test that all search functions use consistent bang syntax."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_search_response)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await search_func(context=mock_tool_context, query="test")

            call_url, call_kwargs = mock_client.get_calls[0]
            assert call_kwargs["params"]["q"].startswith(expected_bang + " ")

    @pytest.mark.asyncio
    async def test_invalid_language_code(self, mock_tool_context):
        """Test handling of invalid language codes."""
        response_with_error = {"error": "Invalid language code", "results": []}
        mock_client = MockAsyncClient(
            responses=[create_mock_response(response_with_error)]
        )

        with patch(
            "arcade_search_engine.tools.search.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await wikipedia_search(
                context=mock_tool_context,
                query="test",
                language="invalid_lang",
            )

            # The function should still return results
            parsed_result = json.loads(result)
            assert parsed_result["results"] == []
