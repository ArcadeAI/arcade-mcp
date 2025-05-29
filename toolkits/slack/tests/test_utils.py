import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from arcade_tdk import ToolContext
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.exceptions import PaginationTimeoutError
from arcade_slack.models import (
    ConversationType,
    ConversationTypeSlackName,
)
from arcade_slack.tools.chat import (
    get_members_in_conversation_by_id,
    list_conversations_metadata,
)
from arcade_slack.utils import (
    async_paginate,
    convert_conversation_type_to_slack_name,
    filter_conversations_by_user_ids,
    retrieve_conversations_by_user_ids,
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "search_user_ids, conversation_types, exact_match, limit, expected_conversation_ids",
    [
        (["U1", "U2"], [ConversationType.DIRECT_MESSAGE], False, 1, ["C1"]),
        (["U1", "U2"], [ConversationType.DIRECT_MESSAGE], True, 1, ["C1"]),
        (["U1", "U2", "U3"], [ConversationType.DIRECT_MESSAGE], False, 1, []),
        (
            ["U1", "U2"],
            [ConversationType.DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            False,
            10,
            ["C1", "C3", "C4"],
        ),
        (
            ["U1", "U2"],
            [ConversationType.DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            True,
            10,
            ["C1", "C3"],
        ),
    ],
)
async def test_retrieve_conversations_by_user_ids(
    mock_chat_slack_client,
    mock_users_slack_client,
    search_user_ids,
    conversation_types,
    exact_match,
    limit,
    expected_conversation_ids,
):
    context = MagicMock(spec=ToolContext)
    context.authorization = MagicMock()
    context.authorization.token = MagicMock()

    conversation_types_slack_name_str = [
        convert_conversation_type_to_slack_name(conv_type).value
        for conv_type in conversation_types or ConversationType
    ]

    conversations = [
        {
            "conversation": {
                "id": "C1",
                "type": ConversationTypeSlackName.IM.value,
                "name": "im-1",
                "is_channel": False,
                "is_im": True,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
            ],
        },
        {
            "conversation": {
                "id": "C2",
                "type": ConversationTypeSlackName.IM.value,
                "name": "im-2",
                "is_channel": False,
                "is_im": True,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U2", "U3"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
            ],
        },
        {
            "conversation": {
                "id": "C3",
                "type": ConversationTypeSlackName.PUBLIC_CHANNEL.value,
                "name": "general",
                "is_channel": True,
                "is_im": False,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
            ],
        },
        {
            "conversation": {
                "id": "C4",
                "type": ConversationTypeSlackName.PUBLIC_CHANNEL.value,
                "name": "random",
                "is_channel": True,
                "is_im": False,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2", "U3", "U4"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
                {"ok": True, "user": {"id": "U4", "team_id": "T123", "name": "user4"}},
            ],
        },
    ]

    conversations_listed = [
        conversation
        for conversation in conversations
        if conversation["conversation"]["type"] in conversation_types_slack_name_str
    ]

    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [conversation["conversation"] for conversation in conversations_listed],
        "response_metadata": {"next_cursor": None},
    }

    mock_chat_slack_client.conversations_members.side_effect = [
        conversation["members"] for conversation in conversations_listed
    ]

    mock_users_slack_client.users_info.side_effect = [
        user for conversation in conversations_listed for user in conversation["users"]
    ]

    conversations_found = await retrieve_conversations_by_user_ids(
        list_conversations_func=list_conversations_metadata,
        get_members_in_conversation_func=get_members_in_conversation_by_id,
        context=context,
        conversation_types=conversation_types,
        user_ids=search_user_ids,
        exact_match=exact_match,
        limit=limit,
        next_cursor=None,
    )

    assert [conversation["id"] for conversation in conversations_found] == expected_conversation_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "search_user_ids, conversation_types, exact_match, limit, "
        "expected_conversation_ids, expected_conversations_list_calls"
    ),
    [
        (
            ["U1", "U2", "U3"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
            False,
            None,
            ["C1", "C3"],
            2,
        ),
        (
            ["U1", "U2", "U3"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
            True,
            None,
            ["C1"],
            2,
        ),
        (["U1", "U2", "U99"], [ConversationType.MULTI_PERSON_DIRECT_MESSAGE], False, None, [], 2),
        (
            ["U1", "U2"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            False,
            None,
            ["C1", "C3", "C4", "C6"],
            2,
        ),
        (
            ["U1", "U2"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            False,
            1,
            ["C1"],
            2,
        ),
        (
            ["U1", "U2"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            False,
            3,
            ["C1", "C3", "C4"],
            2,
        ),
        (
            ["U1", "U2"],
            [ConversationType.MULTI_PERSON_DIRECT_MESSAGE, ConversationType.PUBLIC_CHANNEL],
            True,
            None,
            ["C4"],
            2,
        ),
    ],
)
async def test_retrieve_conversations_by_user_ids_with_pagination(
    mock_chat_slack_client,
    mock_users_slack_client,
    search_user_ids,
    conversation_types,
    exact_match,
    limit,
    expected_conversation_ids,
    expected_conversations_list_calls,
):
    context = MagicMock(spec=ToolContext)
    context.authorization = MagicMock()
    context.authorization.token = MagicMock()

    conversation_types_slack_name_str = [
        convert_conversation_type_to_slack_name(conv_type).value
        for conv_type in conversation_types or ConversationType
    ]

    conversations = [
        {
            "conversation": {
                "id": "C1",
                "type": ConversationTypeSlackName.MPIM.value,
                "name": "mpim-1",
                "is_channel": False,
                "is_im": False,
                "is_mpim": True,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2", "U3"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
            ],
        },
        {
            "conversation": {
                "id": "C2",
                "type": ConversationTypeSlackName.MPIM.value,
                "name": "mpim-2",
                "is_channel": False,
                "is_im": False,
                "is_mpim": True,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U2", "U3"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
            ],
        },
        {
            "conversation": {
                "id": "C3",
                "type": ConversationTypeSlackName.MPIM.value,
                "name": "mpim-3",
                "is_channel": False,
                "is_im": False,
                "is_mpim": True,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2", "U3", "U4"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
                {"ok": True, "user": {"id": "U4", "team_id": "T123", "name": "user4"}},
            ],
        },
        {
            "conversation": {
                "id": "C4",
                "type": ConversationTypeSlackName.PUBLIC_CHANNEL.value,
                "name": "channel-4",
                "is_channel": True,
                "is_im": False,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
            ],
        },
        {
            "conversation": {
                "id": "C5",
                "type": ConversationTypeSlackName.PUBLIC_CHANNEL.value,
                "name": "channel-5",
                "is_channel": True,
                "is_im": False,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U2", "U3", "U4"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
                {"ok": True, "user": {"id": "U4", "team_id": "T123", "name": "user4"}},
            ],
        },
        {
            "conversation": {
                "id": "C6",
                "type": ConversationTypeSlackName.PUBLIC_CHANNEL.value,
                "name": "channel-6",
                "is_channel": True,
                "is_im": False,
                "is_member": True,
            },
            "members": {
                "ok": True,
                "members": ["U1", "U2", "U3", "U4"],
                "response_metadata": {"next_cursor": None},
            },
            "users": [
                {"ok": True, "user": {"id": "U1", "team_id": "T123", "name": "user1"}},
                {"ok": True, "user": {"id": "U2", "team_id": "T123", "name": "user2"}},
                {"ok": True, "user": {"id": "U3", "team_id": "T123", "name": "user3"}},
                {"ok": True, "user": {"id": "U4", "team_id": "T123", "name": "user4"}},
            ],
        },
    ]

    conversations_listed = [
        conversation
        for conversation in conversations
        if conversation["conversation"]["type"] in conversation_types_slack_name_str
    ]

    split_size = len(conversations_listed) // 2

    conversations_listed_1 = conversations_listed[:split_size]
    conversations_listed_2 = conversations_listed[split_size:]

    mock_chat_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [conversation["conversation"] for conversation in conversations_listed_1],
            "response_metadata": {"next_cursor": "cursor_1"},
        },
        {
            "ok": True,
            "channels": [conversation["conversation"] for conversation in conversations_listed_2],
            "response_metadata": {"next_cursor": None},
        },
    ]

    mock_chat_slack_client.conversations_members.side_effect = [
        conversation["members"] for conversation in conversations_listed
    ]

    mock_users_slack_client.users_info.side_effect = [
        user for conversation in conversations_listed for user in conversation["users"]
    ]

    conversations_found = await retrieve_conversations_by_user_ids(
        list_conversations_func=list_conversations_metadata,
        get_members_in_conversation_func=get_members_in_conversation_by_id,
        context=context,
        conversation_types=conversation_types,
        user_ids=search_user_ids,
        exact_match=exact_match,
        limit=limit,
        next_cursor=None,
    )

    assert [conversation["id"] for conversation in conversations_found] == expected_conversation_ids
    assert mock_chat_slack_client.conversations_list.call_count == expected_conversations_list_calls
