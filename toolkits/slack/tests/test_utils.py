import asyncio
from unittest.mock import AsyncMock, call, patch

import pytest
from arcade_tdk.errors import RetryableToolError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.exceptions import PaginationTimeoutError
from arcade_slack.models import (
    ConcurrencySafeCoroutineCaller,
    FindMultipleUsersByUsernameSentinel,
    FindUserByUsernameSentinel,
)
from arcade_slack.utils import (
    async_paginate,
    build_multiple_users_retrieval_response,
    filter_conversations_by_user_ids,
    gather_with_concurrency_limit,
    is_valid_email,
)


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
async def test_async_paginate_with_find_user_sentinel():
    mock_slack_client = AsyncMock()
    mock_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [
                {"id": "123", "name": "Jack"},
                {"id": "456", "name": "John"},
            ],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [{"id": "789", "name": "Jenifer"}],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "members": [{"id": "007", "name": "James"}],
            "response_metadata": {"next_cursor": None},
        },
    ]

    results, next_cursor = await async_paginate(
        func=mock_slack_client.users_list,
        response_key="members",
        sentinel=FindUserByUsernameSentinel(username="jenifer"),
    )

    assert results == [
        {"id": "123", "name": "Jack"},
        {"id": "456", "name": "John"},
        {"id": "789", "name": "Jenifer"},
    ]
    assert next_cursor == "cursor2"


@pytest.mark.asyncio
async def test_async_paginate_with_find_user_sentinel_not_found():
    mock_slack_client = AsyncMock()
    mock_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [
                {"id": "123", "name": "Jack"},
                {"id": "456", "name": "John"},
            ],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [{"id": "789", "name": "Jenifer"}],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "members": [{"id": "007", "name": "James"}],
            "response_metadata": {"next_cursor": None},
        },
    ]

    results, next_cursor = await async_paginate(
        func=mock_slack_client.users_list,
        response_key="members",
        sentinel=FindUserByUsernameSentinel(username="Do not find me"),
    )

    assert results == [
        {"id": "123", "name": "Jack"},
        {"id": "456", "name": "John"},
        {"id": "789", "name": "Jenifer"},
        {"id": "007", "name": "James"},
    ]
    assert next_cursor is None


@pytest.mark.asyncio
async def test_async_paginate_with_find_multiple_users_sentinel():
    mock_slack_client = AsyncMock()
    mock_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [
                {"id": "123", "name": "Jack"},
                {"id": "456", "name": "John"},
            ],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [
                {"id": "789", "name": "Jenifer"},
                {"id": "101", "name": "Janis"},
            ],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "members": [{"id": "007", "name": "James"}],
            "response_metadata": {"next_cursor": None},
        },
    ]

    results, next_cursor = await async_paginate(
        func=mock_slack_client.users_list,
        response_key="members",
        sentinel=FindMultipleUsersByUsernameSentinel(usernames=["jenifer", "jack"]),
    )

    assert results == [
        {"id": "123", "name": "Jack"},
        {"id": "456", "name": "John"},
        {"id": "789", "name": "Jenifer"},
        {"id": "101", "name": "Janis"},
    ]
    assert next_cursor == "cursor2"


@pytest.mark.asyncio
async def test_async_paginate_with_find_multiple_users_sentinel_not_found():
    mock_slack_client = AsyncMock()
    mock_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [
                {"id": "123", "name": "Jack"},
                {"id": "456", "name": "John"},
            ],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [
                {"id": "789", "name": "Jenifer"},
                {"id": "101", "name": "Janis"},
            ],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "members": [{"id": "007", "name": "James"}],
            "response_metadata": {"next_cursor": None},
        },
    ]

    results, next_cursor = await async_paginate(
        func=mock_slack_client.users_list,
        response_key="members",
        sentinel=FindMultipleUsersByUsernameSentinel(
            usernames=["jenifer", "jack", "do not find me"]
        ),
    )

    assert results == [
        {"id": "123", "name": "Jack"},
        {"id": "456", "name": "John"},
        {"id": "789", "name": "Jenifer"},
        {"id": "101", "name": "Janis"},
        {"id": "007", "name": "James"},
    ]
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


def test_filter_conversations_by_user_ids():
    conversations = [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}, {"id": "user3"}]},
        {"id": "456", "members": [{"id": "user2"}, {"id": "user3"}]},
    ]
    response = filter_conversations_by_user_ids(
        conversations=conversations,
        user_ids=["user1", "user2"],
        exact_match=False,
    )
    assert response == [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}, {"id": "user3"}]},
    ]


def test_filter_conversations_by_user_ids_empty_response():
    conversations = [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user3"}, {"id": "user4"}]},
        {"id": "456", "members": [{"id": "user2"}, {"id": "user3"}, {"id": "user4"}]},
    ]
    response = filter_conversations_by_user_ids(
        conversations=conversations,
        user_ids=["user1", "user2"],
        exact_match=False,
    )
    assert response == []


def test_filter_conversations_by_user_ids_multiple_matches():
    conversations = [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}, {"id": "user3"}]},
        {"id": "456", "members": [{"id": "user2"}, {"id": "user3"}]},
        {
            "id": "789",
            "members": [{"id": "user4"}, {"id": "user1"}, {"id": "user2"}, {"id": "user3"}],
        },
    ]
    response = filter_conversations_by_user_ids(
        conversations=conversations,
        user_ids=["user1", "user2"],
        exact_match=False,
    )
    assert response == [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}, {"id": "user3"}]},
        {
            "id": "789",
            "members": [{"id": "user4"}, {"id": "user1"}, {"id": "user2"}, {"id": "user3"}],
        },
    ]


def test_filter_conversations_by_user_ids_exact_match():
    conversations = [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}]},
        {"id": "456", "members": [{"id": "user2"}, {"id": "user3"}]},
    ]
    response = filter_conversations_by_user_ids(
        conversations=conversations,
        user_ids=["user1", "user2"],
        exact_match=True,
    )
    assert response == [{"id": "123", "members": [{"id": "user1"}, {"id": "user2"}]}]


def test_filter_conversations_by_user_ids_exact_match_empty_response():
    conversations = [
        {"id": "123", "members": [{"id": "user1"}, {"id": "user2"}, {"id": "user3"}]},
        {"id": "456", "members": [{"id": "user2"}, {"id": "user3"}]},
    ]
    response = filter_conversations_by_user_ids(
        conversations=conversations,
        user_ids=["user1", "user2"],
        exact_match=True,
    )
    assert response == []


@pytest.mark.parametrize(
    "users_by_email, users_by_username, expected_response",
    [
        (
            {"users": [{"id": "U1", "name": "user1"}]},
            {"users": [{"id": "U2", "name": "user2"}]},
            [{"id": "U1", "name": "user1"}, {"id": "U2", "name": "user2"}],
        ),
        (
            {"users": [{"id": "U1", "name": "user1"}]},
            {"users": []},
            [{"id": "U1", "name": "user1"}],
        ),
        (
            {"users": []},
            {"users": [{"id": "U2", "name": "user2"}]},
            [{"id": "U2", "name": "user2"}],
        ),
        (
            {"users": []},
            {"users": []},
            [],
        ),
    ],
)
def test_build_multiple_users_retrieval_response_success(
    users_by_email,
    users_by_username,
    expected_response,
):
    response = build_multiple_users_retrieval_response(
        users_responses=[users_by_email, users_by_username],
    )
    assert response == expected_response


@pytest.mark.parametrize(
    "users_by_email, users_by_username",
    [
        (
            {"users": [{"id": "U1", "name": "user1"}], "emails_not_found": ["email_not_found"]},
            {
                "users": [{"id": "U2", "name": "user2"}],
                "usernames_not_found": ["username_not_found"],
                "other_available_users": [{"id": "U3", "name": "user3"}],
            },
        ),
        (
            {"users": [{"id": "U1", "name": "user1"}], "emails_not_found": ["email_not_found"]},
            {"users": [{"id": "U2", "name": "user2"}]},
        ),
        (
            {"users": [{"id": "U1", "name": "user1"}]},
            {
                "users": [{"id": "U2", "name": "user2"}],
                "usernames_not_found": ["username_not_found"],
                "other_available_users": [{"id": "U3", "name": "user3"}],
            },
        ),
    ],
)
def test_build_multiple_users_retrieval_response_not_found(
    users_by_email,
    users_by_username,
):
    with pytest.raises(RetryableToolError) as error:
        build_multiple_users_retrieval_response(
            users_responses=[users_by_email, users_by_username],
        )

        emails_not_found = users_by_email.get("emails_not_found", [])
        usernames_not_found = users_by_username.get("usernames_not_found", [])
        other_available_users = users_by_username.get("other_available_users", [])

        for email in emails_not_found:
            assert email in error.value.message
        for username in usernames_not_found:
            assert username in error.value.message
        for user in other_available_users:
            assert str(user) in error.value.additional_prompt_content


def test_is_valid_email():
    assert is_valid_email("test@example.com")
    assert is_valid_email("test+123@example.com")
    assert is_valid_email("test-123@example.com")
    assert is_valid_email("test_123@example.com")
    assert is_valid_email("test.123@example.com")
    assert is_valid_email("test123@example.com")
    assert is_valid_email("test@example.co")
    assert is_valid_email("test@example.com.co")
    assert not is_valid_email("test123@example")
    assert not is_valid_email("test@example")
    assert not is_valid_email("test@example.")
    assert not is_valid_email("test@.com")
    assert not is_valid_email("test@example.c")
    assert not is_valid_email("test@example.com.")
    assert not is_valid_email("test@example.com.c")


@pytest.mark.asyncio
async def test_gather_with_concurrency_limit():
    mock_func1 = AsyncMock()
    mock_func2 = AsyncMock()

    caller1 = ConcurrencySafeCoroutineCaller(mock_func1, "arg1", "arg2", kwarg1="kwarg1")
    caller2 = ConcurrencySafeCoroutineCaller(mock_func2, "arg1", "arg2", kwarg1="kwarg1")

    mock_semaphore = AsyncMock(spec=asyncio.Semaphore)

    response = await gather_with_concurrency_limit(
        coroutine_callers=[caller1, caller2],
        semaphore=mock_semaphore,
    )

    response = tuple(response)

    assert len(response) == 2
    assert response[0] == mock_func1.return_value
    assert response[1] == mock_func2.return_value

    mock_func1.assert_awaited_once_with("arg1", "arg2", kwarg1="kwarg1")
    mock_func2.assert_awaited_once_with("arg1", "arg2", kwarg1="kwarg1")

    assert mock_semaphore.__aenter__.await_count == 2
    assert mock_semaphore.__aexit__.await_count == 2
