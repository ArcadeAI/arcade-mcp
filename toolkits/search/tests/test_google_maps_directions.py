from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem

from arcade_search.exceptions import CountryNotFoundError, LanguageNotFoundError
from arcade_search.tools.google_maps import (
    get_directions_between_addresses,
    get_directions_between_coordinates,
)


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="serp_api_key", value="fake_api_key")])


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_get_directions_between_coordinates_success(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search.return_value.as_dict.return_value = {
        "directions": [
            {
                "arrive_around": 1741789839,
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }

    result = await get_directions_between_coordinates(
        context=mock_context,
        origin_latitude="1",
        origin_longitude="2",
        destination_latitude="3",
        destination_longitude="4",
    )

    assert result == {
        "directions": [
            {
                "arrive_around": {
                    "datetime": "2025-03-12T14:30:39+00:00",
                    "timestamp": 1741789839,
                },
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_get_directions_between_addresses_success(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search.return_value.as_dict.return_value = {
        "directions": [
            {
                "arrive_around": 1741789839,
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }

    result = await get_directions_between_addresses(
        context=mock_context,
        origin_address="1",
        destination_address="2",
    )

    assert result == {
        "directions": [
            {
                "arrive_around": {
                    "datetime": "2025-03-12T14:30:39+00:00",
                    "timestamp": 1741789839,
                },
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_get_directions_between_addresses_country_not_found(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search.return_value.as_dict.return_value = {
        "directions": [
            {
                "arrive_around": 1741789839,
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }

    with pytest.raises(CountryNotFoundError):
        await get_directions_between_addresses(
            context=mock_context,
            origin_address="1",
            destination_address="2",
            country="invalid",
        )


@pytest.mark.asyncio
@patch("arcade_search.utils.SerpClient")
async def test_get_directions_between_addresses_language_not_found(mock_serp_client, mock_context):
    mock_serp_client_instance = mock_serp_client.return_value
    mock_serp_client_instance.search.return_value.as_dict.return_value = {
        "directions": [
            {
                "arrive_around": 1741789839,
                "distance": "100 miles",
                "duration": "1 hour",
            }
        ]
    }

    with pytest.raises(LanguageNotFoundError):
        await get_directions_between_addresses(
            context=mock_context,
            origin_address="1",
            destination_address="2",
            language="invalid",
        )
