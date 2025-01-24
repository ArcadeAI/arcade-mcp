import asyncio
from unittest.mock import AsyncMock, call, patch

import pytest
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.exceptions import PaginationTimeoutError
from arcade_slack.utils import async_paginate


@pytest.mark.asyncio
async def test_async_paginate():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.return_value = {
        "ok": True,
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
async def test_async_paginate_with_response_error():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.side_effect = SlackApiError(
        message="slack_error",
        response={"ok": False, "error": "slack_error"},
    )

    with pytest.raises(SlackApiError) as e:
        await async_paginate(
            func=mock_slack_client.conversations_list,
            response_key="channels",
        )
        assert str(e.value) == "slack_error"


@pytest.mark.asyncio
async def test_async_paginate_with_custom_pagination_args():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [{"id": "123"}],
        "response_metadata": {"next_cursor": "456"},
    }

    results, next_cursor = await async_paginate(
        func=mock_slack_client.conversations_list,
        response_key="channels",
        limit=1,
        next_cursor="123",
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
@pytest.mark.parametrize(
    "test_limit, last_next_cursor, last_expected_limit",
    [(5, "cursor3", 1), (None, None, 2)],
)
async def test_async_paginate_large_limit(test_limit, last_next_cursor, last_expected_limit):
    mock_slack_client = AsyncMock(spec=AsyncWebClient)
    mock_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [{"id": "channel1"}, {"id": "channel2"}],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "channels": [{"id": "channel3"}, {"id": "channel4"}],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "channels": [{"id": "channel5"}],
            "response_metadata": {"next_cursor": last_next_cursor},
        },
    ]

    with patch("arcade_slack.utils.MAX_PAGINATION_SIZE_LIMIT", 2):
        results, next_cursor = await async_paginate(
            func=mock_slack_client.conversations_list,
            response_key="channels",
            limit=test_limit,
            hello="world",
        )

    assert results == [
        {"id": "channel1"},
        {"id": "channel2"},
        {"id": "channel3"},
        {"id": "channel4"},
        {"id": "channel5"},
    ]
    assert next_cursor == last_next_cursor
    assert mock_slack_client.conversations_list.call_count == 3
    mock_slack_client.conversations_list.assert_has_calls([
        call(hello="world", limit=2, cursor=None),
        call(hello="world", limit=2, cursor="cursor1"),
        call(hello="world", limit=last_expected_limit, cursor="cursor2"),
    ])


@pytest.mark.asyncio
async def test_async_paginate_large_limit_with_response_error():
    mock_slack_client = AsyncMock()
    mock_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [{"id": "channel1"}, {"id": "channel2"}],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        SlackApiError(message="slack_error", response={"ok": False, "error": "slack_error"}),
        {
            "ok": True,
            "channels": [{"id": "channel5"}],
            "response_metadata": {"next_cursor": "cursor3"},
        },
    ]

    with (
        patch("arcade_slack.utils.MAX_PAGINATION_SIZE_LIMIT", 2),
        pytest.raises(SlackApiError) as e,
    ):
        await async_paginate(
            func=mock_slack_client.conversations_list,
            response_key="channels",
            limit=5,
            hello="world",
        )
        assert str(e.value) == "slack_error"

    assert mock_slack_client.conversations_list.call_count == 2
    mock_slack_client.conversations_list.assert_has_calls([
        call(hello="world", limit=2, cursor=None),
        call(hello="world", limit=2, cursor="cursor1"),
    ])


@pytest.mark.asyncio
async def test_async_paginate_with_timeout():
    # Mock Slack client
    mock_slack_client = AsyncMock()

    # Simulate a network delay by making the mock function sleep
    async def mock_conversations_list(*args, **kwargs):
        await asyncio.sleep(1)  # Sleep for 1 second to simulate delay
        return {
            "ok": True,
            "channels": [{"id": "123"}],
            "response_metadata": {"next_cursor": None},
        }

    mock_slack_client.conversations_list.side_effect = mock_conversations_list

    # Set a low timeout to trigger the timeout error quickly during the test
    max_pagination_timeout_seconds = 0.1  # 100 milliseconds

    with pytest.raises(PaginationTimeoutError) as exc_info:
        await async_paginate(
            func=mock_slack_client.conversations_list,
            response_key="channels",
            max_pagination_timeout_seconds=max_pagination_timeout_seconds,
        )

    assert (
        str(exc_info.value)
        == f"The pagination process timed out after {max_pagination_timeout_seconds} seconds."
    )
