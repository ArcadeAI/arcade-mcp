import json
from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem

from arcade_google_search.tools import search


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="serp_api_key", value="fake_api_key")])


@pytest.mark.asyncio
async def test_search_google_success(mock_context):
    with (
        patch("arcade_google_search.utils.SerpClient") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {
            "organic_results": [
                {"title": "Result 1", "link": "http://example.com/1"},
                {"title": "Result 2", "link": "http://example.com/2"},
                {"title": "Result 3", "link": "http://example.com/3"},
            ]
        }

        result = await search(mock_context, "test query", 2)

        expected_result = json.dumps([
            {"title": "Result 1", "link": "http://example.com/1"},
            {"title": "Result 2", "link": "http://example.com/2"},
        ])
        assert result == expected_result


@pytest.mark.asyncio
async def test_search_google_no_results(mock_context):
    with (
        patch("arcade_google_search.utils.SerpClient") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {"organic_results": []}

        result = await search(mock_context, "test query", 2)

        expected_result = json.dumps([])
        assert result == expected_result
