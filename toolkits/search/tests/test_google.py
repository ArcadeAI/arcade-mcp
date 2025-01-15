import json
from unittest.mock import patch

import pytest

from arcade_search.tools.google import search_google

GET_SECRET_PATCH_TARGET = "arcade_search.tools.google.get_secret"  # noqa: S105


@pytest.mark.asyncio
async def test_search_google_success():
    with (
        patch(GET_SECRET_PATCH_TARGET, return_value="fake_api_key"),
        patch("serpapi.Client") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {
            "organic_results": [
                {"title": "Result 1", "link": "http://example.com/1"},
                {"title": "Result 2", "link": "http://example.com/2"},
                {"title": "Result 3", "link": "http://example.com/3"},
            ]
        }

        result = await search_google("test query", 2)

        expected_result = json.dumps([
            {"title": "Result 1", "link": "http://example.com/1"},
            {"title": "Result 2", "link": "http://example.com/2"},
        ])
        assert result == expected_result


@pytest.mark.asyncio
async def test_search_google_no_results():
    with (
        patch(GET_SECRET_PATCH_TARGET, return_value="fake_api_key"),
        patch("serpapi.Client") as MockClient,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.search.return_value.as_dict.return_value = {"organic_results": []}

        result = await search_google("test query", 2)

        expected_result = json.dumps([])
        assert result == expected_result
