import json
from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem

from arcade_search.tools import search_google


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="serp_api_key", value="fake_api_key")])


@pytest.mark.asyncio
async def test_search_google_success(mock_context):
    with (
        patch("arcade_search.utils.SerpClient") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {
            "organic_results": [
                {"title": "Result 1", "link": "http://example.com/1"},
                {"title": "Result 2", "link": "http://example.com/2"},
                {"title": "Result 3", "link": "http://example.com/3"},
            ]
        }

        result = await search_google(mock_context, "test query", 2)

        expected_result = json.dumps([
            {"title": "Result 1", "link": "http://example.com/1"},
            {"title": "Result 2", "link": "http://example.com/2"},
        ])
        assert result == expected_result


@pytest.mark.asyncio
async def test_search_google_no_results(mock_context):
    with (
        patch("arcade_search.utils.SerpClient") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {"organic_results": []}

        result = await search_google(mock_context, "test query", 2)

        expected_result = json.dumps([])
        assert result == expected_result
