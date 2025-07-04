from unittest.mock import MagicMock

import pytest
from arcade_tdk import ToolContext

from arcade_slack.conversation_retrieval import (
    get_conversations_by_user_ids,
    get_members_in_conversation_by_id,
)
from arcade_slack.models import ConversationType, ConversationTypeSlackName
from arcade_slack.tools.chat import list_conversations_metadata
from arcade_slack.utils import convert_conversation_type_to_slack_name


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

    conversations_found = await get_conversations_by_user_ids(
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

    conversations_found = await get_conversations_by_user_ids(
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
