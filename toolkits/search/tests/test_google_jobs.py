from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem

from arcade_search.exceptions import LanguageNotFoundError
from arcade_search.tools.google_jobs import search_jobs


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="serp_api_key", value="fake_api_key")])


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_search_jobs_success(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search().as_dict.return_value = {
        "jobs_results": [
            {"title": "Job 1", "link": "http://example.com/1"},
            {"title": "Job 2", "link": "http://example.com/2"},
        ]
    }

    result = await search_jobs(mock_context, "engenheiro de software", "Brazil", "pt", 10, None)
    assert result == {
        "jobs": [
            {"title": "Job 1", "link": "http://example.com/1"},
            {"title": "Job 2", "link": "http://example.com/2"},
        ],
        "next_page_token": None,
    }


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_search_jobs_success_with_custom_language_and_location(
    mock_serp_client, mock_context
):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search().as_dict.return_value = {
        "jobs_results": [
            {"title": "Job 1", "link": "http://example.com/1"},
            {"title": "Job 2", "link": "http://example.com/2"},
        ]
    }

    result = await search_jobs(
        context=mock_context,
        query="engenheiro de software",
        location="Brazil",
        language="pt",
        limit=10,
        next_page_token=None,
    )

    mock_serp_client_instance.search.assert_called_with({
        "engine": "google_jobs",
        "q": "engenheiro de software",
        "hl": "pt",
        "location": "Brazil",
    })

    assert result == {
        "jobs": [
            {"title": "Job 1", "link": "http://example.com/1"},
            {"title": "Job 2", "link": "http://example.com/2"},
        ],
        "next_page_token": None,
    }


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_search_jobs_language_not_found_error(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search().as_dict.return_value = {
        "jobs_results": [
            {"title": "Job 1", "link": "http://example.com/1"},
            {"title": "Job 2", "link": "http://example.com/2"},
        ]
    }

    with pytest.raises(LanguageNotFoundError):
        await search_jobs(
            context=mock_context,
            query="backend engineer",
            language="invalid_language",
        )
