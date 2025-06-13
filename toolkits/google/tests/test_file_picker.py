import base64
import json
from urllib.parse import parse_qs, urlparse

import pytest
from arcade_tdk import ToolContext, ToolMetadataItem, ToolMetadataKey

from arcade_google.tools import generate_google_file_picker_url


@pytest.fixture
def mock_context():
    context = ToolContext(
        metadata=[
            ToolMetadataItem(key=ToolMetadataKey.CLIENT_ID, value="1234-3444534323"),
            ToolMetadataItem(
                key=ToolMetadataKey.COORDINATOR_URL, value="https://mock_coordinator_url"
            ),
        ],
    )
    return context


@pytest.mark.asyncio
async def test_generate_google_file_picker_url(mock_context):
    expected_decoded_config = {
        "auth": {
            "client_id": "1234-3444534323",
            "app_id": "1234",
        },
    }

    result = generate_google_file_picker_url(mock_context)

    assert result["url"].startswith("https://mock_coordinator_url/google/drive_picker?config=")

    # Decode the config from the URL
    parsed_url = urlparse(result["url"])
    query_params = parse_qs(parsed_url.query)
    encoded_config = query_params.get("config", [None])[0]
    assert encoded_config is not None

    decoded_config = json.loads(base64.urlsafe_b64decode(encoded_config).decode("utf-8"))
    assert decoded_config == expected_decoded_config
