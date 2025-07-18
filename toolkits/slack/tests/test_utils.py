import asyncio
import copy
import json
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
    populate_users_in_messages,
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
@pytest.mark.asyncio
async def test_build_multiple_users_retrieval_response_success(
    users_by_email,
    users_by_username,
    expected_response,
    mock_context,
):
    response = await build_multiple_users_retrieval_response(
        context=mock_context,
        users_responses=[users_by_email, users_by_username],
    )
    assert response == expected_response


@pytest.mark.parametrize(
    "users_by_email, users_by_username",
    [
        # Both emails and usernames not found
        (
            {
                "users": [{"id": "U1", "name": "user1"}],
                "not_found": ["email_not_found"],
            },
            {
                "users": [{"id": "U2", "name": "user2"}],
                "not_found": ["username_not_found"],
                "available_users": [{"id": "U3", "name": "user3"}],
            },
        ),
        # Email not found, usernames found
        (
            {
                "users": [{"id": "U1", "name": "user1"}],
                "not_found": ["email_not_found"],
            },
            {
                "users": [{"id": "U2", "name": "user2"}],
                "not_found": [],
            },
        ),
        # Email found, username not found
        (
            {
                "users": [{"id": "U1", "name": "user1"}],
                "not_found": [],
            },
            {
                "users": [{"id": "U2", "name": "user2"}],
                "not_found": ["username_not_found"],
                "available_users": [{"id": "U3", "name": "user3"}],
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_build_multiple_users_retrieval_response_not_found(
    users_by_email,
    users_by_username,
    mock_context,
):
    with pytest.raises(RetryableToolError) as error:
        await build_multiple_users_retrieval_response(
            context=mock_context,
            users_responses=[users_by_email, users_by_username],
        )

    emails_not_found = users_by_email.get("not_found", [])
    usernames_not_found = users_by_username.get("not_found", [])
    available_users = users_by_username.get("available_users", [])

    for email in emails_not_found:
        assert email in error.value.message
    for username in usernames_not_found:
        assert username in error.value.message
    for user in available_users:
        assert json.dumps(user) in error.value.additional_prompt_content


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


@pytest.mark.asyncio
async def test_populate_users_in_messages(
    mock_context,
    mock_user_retrieval_slack_client,
    dummy_message_factory,
    dummy_reaction_factory,
    dummy_user_factory,
):
    user1 = dummy_user_factory(id_="U1", name="user1")
    user2 = dummy_user_factory(id_="U2", name="user2")
    user3 = dummy_user_factory(id_="U3", name="user3")
    user4 = dummy_user_factory(id_="U4", name="user4")
    user5 = dummy_user_factory(id_="U5", name="user5")

    user1_short = {"id": user1["id"], "name": user1["name"]}
    user2_short = {"id": user2["id"], "name": user2["name"]}
    user3_short = {"id": user3["id"], "name": user3["name"]}
    user4_short = {"id": user4["id"], "name": user4["name"]}

    user2_mention = f"<@{user2['name']} (id:{user2['id']})>"
    user5_mention = f"<@{user5['name']} (id:{user5['id']})>"

    reactions = [
        dummy_reaction_factory(name="thumbsup", user_ids=[user1["id"], user2["id"]]),
        dummy_reaction_factory(name="partyparrot", user_ids=[user3["id"], user4["id"]]),
    ]

    messages = [
        dummy_message_factory(
            user_id=user1["id"],
            text=f"Hello <@{user2['id']}>",
        ),
        dummy_message_factory(
            user_id=user2["id"],
            text="foobar",
            reactions=copy.deepcopy(reactions[:1]),
        ),
        dummy_message_factory(
            user_id=user3["id"],
            text=f"Is this @{user5['id']} a user mention?",
        ),
        dummy_message_factory(
            user_id=user4["id"],
            text="hello",
            reactions=copy.deepcopy(reactions),
        ),
    ]

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2, user3],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [user4, user5],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await populate_users_in_messages(
        auth_token=mock_context.get_auth_token_or_empty(),
        messages=messages,
    )

    msg1 = response[0]
    msg2 = response[1]
    msg3 = response[2]
    msg4 = response[3]

    assert msg1["user"] == user1_short
    assert msg1["text"] == f"Hello {user2_mention}"
    assert "reactions" not in msg1

    assert msg2["user"] == user2_short
    assert msg2["text"] == "foobar"
    assert "reactions" in msg2
    assert len(msg2["reactions"]) == 1
    assert msg2["reactions"][0]["name"] == "thumbsup"
    assert msg2["reactions"][0]["users"] == [user1_short, user2_short]

    assert msg3["user"] == user3_short
    assert msg3["text"] == f"Is this @{user5['id']} a user mention?"
    assert "reactions" not in msg3
    assert user5_mention not in msg3["text"]

    assert msg4["user"] == user4_short
    assert msg4["text"] == "hello"
    assert "reactions" in msg4
    assert len(msg4["reactions"]) == 2
    assert msg4["reactions"][0]["name"] == "thumbsup"
    assert msg4["reactions"][0]["users"] == [user1_short, user2_short]
    assert msg4["reactions"][1]["name"] == "partyparrot"
    assert msg4["reactions"][1]["users"] == [user3_short, user4_short]
