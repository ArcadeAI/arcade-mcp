from unittest.mock import AsyncMock, call, patch

import pytest

from arcade_slack.utils import async_paginate


@pytest.mark.asyncio
async def test_async_paginate():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.return_value = {
        "channels": [{"id": "123"}],
        "response_metadata": {"next_cursor": None},
    }

    results, next_cursor = await async_paginate(
        func=mock_slack_client.conversations_list,
        response_key="channels",
    )

    assert results == [{"id": "123"}]
    assert next_cursor is None


@pytest.mark.asyncio
async def test_async_paginate_with_custom_pagination_args():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.return_value = {
        "channels": [{"id": "123"}],
        "response_metadata": {"next_cursor": "456"},
    }

    results, next_cursor = await async_paginate(
        func=mock_slack_client.conversations_list,
        response_key="channels",
        limit=1,
        cursor="123",
        hello="world",
    )

    assert results == [{"id": "123"}]
    assert next_cursor == "456"

    mock_slack_client.conversations_list.assert_called_once_with(
        hello="world",
        limit=1,
        cursor="123",
    )


@pytest.mark.asyncio
async def test_async_paginate_large_limit():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.side_effect = [
        {
            "channels": [{"id": "channel1"}, {"id": "channel2"}],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "channels": [{"id": "channel3"}, {"id": "channel4"}],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "channels": [{"id": "channel5"}],
            "response_metadata": {"next_cursor": "cursor3"},
        },
    ]

    with patch("arcade_slack.utils.MAX_PAGINATION_LIMIT", 2):
        results, next_cursor = await async_paginate(
            func=mock_slack_client.conversations_list,
            response_key="channels",
            limit=5,
            hello="world",
        )

    assert results == [
        {"id": "channel1"},
        {"id": "channel2"},
        {"id": "channel3"},
        {"id": "channel4"},
        {"id": "channel5"},
    ]
    assert next_cursor == "cursor3"
    assert mock_slack_client.conversations_list.call_count == 3
    mock_slack_client.conversations_list.assert_has_calls([
        call(hello="world", limit=2, cursor=None),
        call(hello="world", limit=2, cursor="cursor1"),
        call(hello="world", limit=1, cursor="cursor2"),
    ])
