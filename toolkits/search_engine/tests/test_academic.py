"""Tests for academic research tools."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from arcade_core.errors import ToolExecutionError

from arcade_search_engine.tools.academic import (
    ResearchSource,
    TimePeriod,
    YearRange,
    find_citations,
    find_code_implementations,
    find_datasets,
    get_year_range_tuple,
    literature_review,
    research_papers,
    research_trends,
)
from tests.conftest import MockAsyncClient, create_mock_response


class TestYearRangeConversion:
    """Test cases for year range conversion utility."""

    @pytest.mark.parametrize(
        "year_range,expected_offset",
        [
            (YearRange.THIS_YEAR, 0),
            (YearRange.LAST_TWO_YEARS, 2),
            (YearRange.LAST_FIVE_YEARS, 5),
            (YearRange.LAST_DECADE, 10),
        ],
    )
    def test_get_year_range_tuple_relative(self, year_range, expected_offset):
        """Test conversion of relative YearRange enums to tuples."""
        current_year = datetime.now().year
        result = get_year_range_tuple(year_range)
        assert result == (current_year - expected_offset, current_year)

    @pytest.mark.parametrize(
        "year_range,expected_start",
        [
            (YearRange.SINCE_2020, 2020),
            (YearRange.SINCE_2010, 2010),
            (YearRange.SINCE_2000, 2000),
        ],
    )
    def test_get_year_range_tuple_absolute(self, year_range, expected_start):
        """Test conversion of absolute YearRange enums to tuples."""
        current_year = datetime.now().year
        result = get_year_range_tuple(year_range)
        assert result == (expected_start, current_year)

    def test_get_year_range_tuple_all_time(self):
        """Test ALL_TIME returns None."""
        assert get_year_range_tuple(YearRange.ALL_TIME) is None


class TestResearchPapers:
    """Test cases for research_papers function."""

    @pytest.mark.asyncio
    async def test_research_papers_all_sources(self, mock_tool_context, sample_academic_response):
        """Test research papers search across all sources."""
        # Create different responses for each search engine
        arxiv_response = {
            "results": [{
                "title": "ArXiv Paper",
                "url": "https://arxiv.org/abs/2024.12345",
                "content": "Abstract from arxiv",
                "publishedDate": "2024-01-15",
            }]
        }
        pubmed_response = {
            "results": [{
                "title": "PubMed Paper",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
                "content": "Abstract from pubmed",
                "publishedDate": "2024-01-10",
            }]
        }
        google_response = {
            "results": [{
                "title": "Google Scholar Paper",
                "url": "https://scholar.google.com/paper123",
                "content": "Abstract from google scholar",
            }]
        }
        
        mock_client = MockAsyncClient(
            responses=[
                create_mock_response(arxiv_response),
                create_mock_response(pubmed_response),
                create_mock_response(google_response),
            ]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await research_papers(
                context=mock_tool_context,
                topic="machine learning",
                sources=[ResearchSource.ARXIV, ResearchSource.PUBMED, ResearchSource.GOOGLE_SCHOLAR],
                max_results=10,
            )

            parsed_result = json.loads(result)
            assert parsed_result["query"] == "machine learning"
            assert "arxiv" in parsed_result["sources"]
            assert "pubmed" in parsed_result["sources"]
            assert "google_scholar" in parsed_result["sources"]
            
            # Check the correct structure with nested results and count
            assert parsed_result["sources"]["arxiv"]["count"] == 1
            assert len(parsed_result["sources"]["arxiv"]["results"]) == 1
            assert parsed_result["sources"]["pubmed"]["count"] == 1
            assert parsed_result["sources"]["google_scholar"]["count"] == 1
            assert parsed_result["total_results"] == 3

    @pytest.mark.parametrize(
        "source,expected_bang",
        [
            (ResearchSource.ARXIV, "!arx"),
            (ResearchSource.PUBMED, "!pubmed"),
            (ResearchSource.GOOGLE_SCHOLAR, "!g"),  # Uses Google with site: constraint
        ],
    )
    @pytest.mark.asyncio
    async def test_research_papers_single_source(
        self, mock_tool_context, sample_academic_response, source, expected_bang
    ):
        """Test research papers with different single sources."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response(sample_academic_response)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await research_papers(
                context=mock_tool_context,
                topic="quantum computing",
                sources=[source],
                max_results=5,
            )

            parsed_result = json.loads(result)
            source_key = source.value
            assert source_key in parsed_result["sources"]
            assert parsed_result["total_results"] >= 1
            
            # Verify the correct search approach was used
            call_url, call_kwargs = mock_client.get_calls[0]
            query = call_kwargs["params"]["q"]
            if source == ResearchSource.GOOGLE_SCHOLAR:
                # Google Scholar uses a different approach
                assert query.startswith("!g") and "site:scholar.google.com" in query
            else:
                assert query.startswith(expected_bang)

    @pytest.mark.asyncio
    async def test_research_papers_error_handling(self, mock_tool_context):
        """Test error handling in research papers search."""
        # One successful response, one error
        success_response = {
            "results": [{
                "title": "Success Paper",
                "url": "https://example.com",
                "content": "Abstract"
            }]
        }
        
        mock_client = MockAsyncClient()
        call_count = 0
        
        async def get_with_error(url, **kwargs):
            nonlocal call_count
            mock_client.get_calls.append((url, kwargs))
            call_count += 1
            if call_count == 1:
                return create_mock_response(success_response)
            else:
                raise Exception("Search failed")
        
        mock_client.get = get_with_error

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await research_papers(
                context=mock_tool_context,
                topic="test",
                sources=[ResearchSource.ARXIV, ResearchSource.PUBMED],
            )

            parsed_result = json.loads(result)
            # Should have one successful source
            assert "sources" in parsed_result
            assert parsed_result["sources"]["arxiv"]["count"] == 1
            # Failed source should have error
            assert "error" in parsed_result["sources"]["pubmed"]
            assert parsed_result["sources"]["pubmed"]["count"] == 0


class TestLiteratureReview:
    """Test cases for literature_review function."""

    @pytest.mark.asyncio
    async def test_literature_review_comprehensive(self, mock_tool_context):
        """Test comprehensive literature review."""
        # Mock responses for different searches
        wikipedia_response = {
            "results": [{
                "title": "Machine Learning",
                "content": "Overview from Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Machine_learning"
            }]
        }
        arxiv_response = {
            "results": [{
                "title": "ML Review Paper",
                "content": "Comprehensive review",
                "url": "https://arxiv.org/abs/2024.12345"
            }]
        }
        
        mock_client = MockAsyncClient(
            responses=[
                # Wikipedia search
                create_mock_response(wikipedia_response),
                # Review papers search (arxiv)
                create_mock_response(arxiv_response),
                # Recent papers search (arxiv)
                create_mock_response(arxiv_response),
            ]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await literature_review(
                context=mock_tool_context,
                topic="machine learning applications",
                include_definitions=True,
                include_reviews=True,
                include_recent_papers=True,
                # max_papers_per_section parameter doesn't exist
            )

            parsed_result = json.loads(result)
            assert parsed_result["topic"] == "machine learning applications"
            assert "sections" in parsed_result
            
            # Check overview section
            assert "overview" in parsed_result["sections"]
            assert parsed_result["sections"]["overview"]["source"] == "Wikipedia"
            assert len(parsed_result["sections"]["overview"]["content"]) > 0
            
            # Check review papers section
            assert "review_papers" in parsed_result["sections"]
            review_papers = parsed_result["sections"]["review_papers"]
            assert "sources" in review_papers
            assert "arxiv" in review_papers["sources"]
            
            # Check recent papers section
            assert "recent_papers" in parsed_result["sections"]

    @pytest.mark.asyncio
    async def test_literature_review_minimal(self, mock_tool_context):
        """Test literature review with minimal options."""
        arxiv_response = {
            "results": [{
                "title": "Paper",
                "content": "Abstract",
                "url": "https://arxiv.org/abs/2024.12345"
            }]
        }
        
        mock_client = MockAsyncClient(
            responses=[create_mock_response(arxiv_response)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await literature_review(
                context=mock_tool_context,
                topic="test topic",
                include_definitions=False,
                include_reviews=True,
                include_recent_papers=False,
            )

            parsed_result = json.loads(result)
            assert "sections" in parsed_result
            assert "overview" not in parsed_result["sections"]
            assert "review_papers" in parsed_result["sections"]
            assert "recent_papers" not in parsed_result["sections"]


class TestFindCitations:
    """Test cases for find_citations function."""

    @pytest.mark.asyncio
    async def test_find_citations_basic(self, mock_tool_context):
        """Test basic citation finding."""
        # First response for finding the paper itself
        paper_response = {
            "results": [{
                "title": "Original Paper Title",
                "url": "https://example.com/original",
                "content": "The original paper abstract",
            }]
        }
        
        # Second response for papers citing it
        citations_response = {
            "results": [
                {
                    "title": "Citing Paper 1",
                    "content": "This paper cites the original work...",
                    "url": "https://example.com/paper1",
                },
                {
                    "title": "Citing Paper 2",
                    "content": "Building upon the work of...",
                    "url": "https://example.com/paper2",
                },
            ]
        }
        
        mock_client = MockAsyncClient(
            responses=[
                create_mock_response(paper_response),
                create_mock_response(citations_response)
            ]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_citations(
                context=mock_tool_context,
                paper_title="Original Paper Title",
                author="John Doe",
            )

            parsed_result = json.loads(result)
            assert parsed_result["query_paper"]["title"] == "Original Paper Title"
            assert parsed_result["query_paper"]["author"] == "John Doe"
            
            # Check if citations were properly populated
            assert "citations" in parsed_result
            assert "citing_papers" in parsed_result["citations"]
            assert len(parsed_result["citations"]["citing_papers"]) == 2
            assert parsed_result["citations"]["count"] == 2

    @pytest.mark.asyncio
    async def test_find_citations_with_year(self, mock_tool_context):
        """Test citation finding with year parameter."""
        mock_client = MockAsyncClient(
            responses=[
                create_mock_response({"results": []}),
                create_mock_response({"results": []})
            ]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_citations(
                context=mock_tool_context,
                paper_title="Test Paper",
                year=2024,
            )

            # Verify year was included in search
            call_url, call_kwargs = mock_client.get_calls[0]
            query = call_kwargs["params"]["q"]
            assert "year:2024" in query
            
            parsed_result = json.loads(result)
            assert parsed_result["query_paper"]["year"] == 2024

    @pytest.mark.asyncio
    async def test_find_citations_error_handling(self, mock_tool_context):
        """Test error handling in find_citations."""
        mock_client = MockAsyncClient(
            side_effect=Exception("Search failed")
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_citations(
                context=mock_tool_context,
                paper_title="Test Paper",
            )

            parsed_result = json.loads(result)
            assert "error" in parsed_result
            assert "Search failed" in parsed_result["error"]


class TestResearchTrends:
    """Test cases for research_trends function."""

    @pytest.mark.parametrize(
        "time_period,expected_range",
        [
            (TimePeriod.DAY, "day"),
            (TimePeriod.WEEK, "week"),
            (TimePeriod.MONTH, "month"),
            (TimePeriod.YEAR, "year"),
        ],
    )
    @pytest.mark.asyncio
    async def test_research_trends_time_periods(
        self, mock_tool_context, time_period, expected_range
    ):
        """Test research trends with different time periods."""
        trend_response = {
            "results": [{
                "title": "Recent Paper",
                "url": "https://example.com",
                "publishedDate": "2024-01-15"
            }]
        }
        
        # Need 5 responses for all trend queries
        mock_client = MockAsyncClient(
            responses=[create_mock_response(trend_response) for _ in range(5)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await research_trends(
                context=mock_tool_context,
                field="artificial intelligence",
                time_period=time_period,
                include_conferences=True,
                include_journals=True,
            )

            parsed_result = json.loads(result)
            assert parsed_result["field"] == "artificial intelligence"
            assert parsed_result["time_period"] == expected_range
            assert "trends" in parsed_result
            
            # Should have 5 trend queries
            assert len(parsed_result["trends"]) == 5
            
            # Check that time range was used in queries
            for call in mock_client.get_calls:
                assert call[1]["params"]["time_range"] == expected_range

    @pytest.mark.asyncio
    async def test_research_trends_minimal(self, mock_tool_context):
        """Test research trends with minimal options."""
        trend_response = {
            "results": [{
                "title": "Paper",
                "url": "https://example.com"
            }]
        }
        
        # Only 3 responses needed without conferences/journals
        mock_client = MockAsyncClient(
            responses=[create_mock_response(trend_response) for _ in range(3)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await research_trends(
                context=mock_tool_context,
                field="quantum computing",
                time_period=TimePeriod.WEEK,
                include_conferences=False,
                include_journals=False,
            )

            parsed_result = json.loads(result)
            assert len(parsed_result["trends"]) == 3  # Only 3 basic queries


class TestFindDatasets:
    """Test cases for find_datasets function."""

    @pytest.mark.asyncio
    async def test_find_datasets_comprehensive(self, mock_tool_context):
        """Test comprehensive dataset search."""
        dataset_response = {
            "results": [{
                "title": "ML Dataset",
                "url": "https://example.com/dataset",
                "content": "1000 samples",
            }]
        }
        
        # Need 6 responses for all dataset sources
        mock_client = MockAsyncClient(
            responses=[create_mock_response(dataset_response) for _ in range(6)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_datasets(
                context=mock_tool_context,
                topic="machine learning classification",
                data_type="images",
                include_benchmarks=True,
            )

            parsed_result = json.loads(result)
            assert parsed_result["topic"] == "machine learning classification"
            assert parsed_result["data_type"] == "images"
            assert "results" in parsed_result
            
            # Check all expected sources
            expected_sources = ["general", "kaggle", "github", "papers_with_code", "huggingface", "benchmarks"]
            for source in expected_sources:
                assert source in parsed_result["results"]
                assert "datasets" in parsed_result["results"][source]
                assert "count" in parsed_result["results"][source]

    @pytest.mark.asyncio
    async def test_find_datasets_error_handling(self, mock_tool_context):
        """Test dataset search with errors."""
        mock_client = MockAsyncClient()
        call_count = 0
        
        async def get_with_partial_error(url, **kwargs):
            nonlocal call_count
            mock_client.get_calls.append((url, kwargs))
            call_count += 1
            if call_count == 1:
                return create_mock_response({"results": [{"title": "Dataset"}]})
            else:
                raise Exception("Search failed")
        
        mock_client.get = get_with_partial_error

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_datasets(
                context=mock_tool_context,
                topic="test dataset",
            )

            parsed_result = json.loads(result)
            # First source should succeed
            assert "datasets" in parsed_result["results"]["general"]
            # Others should have errors
            assert "error" in parsed_result["results"]["kaggle"]


class TestFindCodeImplementations:
    """Test cases for find_code_implementations function."""

    @pytest.mark.asyncio
    async def test_find_code_implementations_all_sources(self, mock_tool_context):
        """Test finding code implementations across all sources."""
        code_response = {
            "results": [{
                "title": "Paper Implementation",
                "url": "https://github.com/user/implementation",
                "content": "PyTorch implementation",
            }]
        }
        
        # Need 4 responses for all code sources
        mock_client = MockAsyncClient(
            responses=[create_mock_response(code_response) for _ in range(4)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_code_implementations(
                context=mock_tool_context,
                paper_title="Test Paper: A Novel Approach",
                language="python",
            )

            parsed_result = json.loads(result)
            assert parsed_result["paper"] == "Test Paper: A Novel Approach"
            assert parsed_result["language"] == "python"
            assert "sources" in parsed_result
            
            # Check all expected sources
            for source in ["github", "papers_with_code", "gitlab", "general"]:
                assert source in parsed_result["sources"]
                assert isinstance(parsed_result["sources"][source], list)

    @pytest.mark.parametrize(
        "algorithm,expected_term",
        [
            ("BERT", "BERT"),
            (None, "Test Paper"),
        ],
    )
    @pytest.mark.asyncio
    async def test_find_code_implementations_with_algorithm(
        self, mock_tool_context, algorithm, expected_term
    ):
        """Test code search with and without algorithm name."""
        mock_client = MockAsyncClient(
            responses=[create_mock_response({"results": []}) for _ in range(4)]
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_code_implementations(
                context=mock_tool_context,
                paper_title="Test Paper",
                algorithm_name=algorithm,  # Correct parameter name
            )

            # Verify the search term was included in the query
            # The actual format is: site:github.com "<search_term>" implementation python
            call_url, call_kwargs = mock_client.get_calls[0]
            query = call_kwargs["params"]["q"]
            assert f'"{expected_term}"' in query  # Check for quoted search term
            assert "implementation" in query
            assert "python" in query  # Default language
            
            parsed_result = json.loads(result)
            assert parsed_result["algorithm"] == (algorithm or "Test Paper")

    @pytest.mark.asyncio
    async def test_find_code_implementations_error_handling(self, mock_tool_context):
        """Test code search with errors."""
        mock_client = MockAsyncClient(
            side_effect=Exception("Search failed")
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            result = await find_code_implementations(
                context=mock_tool_context,
                paper_title="Test Paper",
            )

            parsed_result = json.loads(result)
            # All sources should have errors
            for source in ["github", "papers_with_code", "gitlab", "general"]:
                assert "error" in parsed_result["sources"][source]


class TestErrorHandling:
    """Test error handling across academic tools."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_tool_context):
        """Test handling of network errors."""
        mock_client = MockAsyncClient(
            side_effect=ToolExecutionError("Network error")
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            # Research papers should handle errors gracefully
            result = await research_papers(
                context=mock_tool_context,
                topic="test",
                sources=[ResearchSource.ARXIV],
            )

            parsed_result = json.loads(result)
            assert "sources" in parsed_result
            assert "error" in parsed_result["sources"]["arxiv"]
            assert parsed_result["total_results"] == 0

    @pytest.mark.parametrize(
        "func,args",
        [
            (research_papers, {"topic": "test", "sources": [ResearchSource.ARXIV]}),
            (literature_review, {"topic": "test"}),
            (find_citations, {"paper_title": "test"}),
            (research_trends, {"field": "test"}),
            (find_datasets, {"topic": "test"}),
            (find_code_implementations, {"paper_title": "test"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_all_functions_handle_errors_gracefully(
        self, mock_tool_context, func, args
    ):
        """Test that all academic functions handle errors without crashing."""
        mock_client = MockAsyncClient(
            side_effect=Exception("Unexpected error")
        )

        with patch("arcade_search_engine.tools.search.httpx.AsyncClient", return_value=mock_client):
            # All functions should return valid JSON even with errors
            result = await func(context=mock_tool_context, **args)
            
            # Should return valid JSON
            parsed_result = json.loads(result)
            assert isinstance(parsed_result, dict)