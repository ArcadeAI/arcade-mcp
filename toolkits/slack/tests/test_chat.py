import json
from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT
from arcade_slack.models import ConversationType, ConversationTypeSlackName
from arcade_slack.tools.chat import (
    get_conversation_metadata,
    get_messages,
    get_users_in_conversation,
    list_conversations,
    send_message,
)
from arcade_slack.utils import cast_user_dict, extract_conversation_metadata


@pytest.fixture
def mock_list_conversations(mocker):
    return mocker.patch("arcade_slack.tools.chat.list_conversations", autospec=True)


@pytest.fixture
def mock_channel_info() -> dict:
    return {"name": "general", "id": "C12345", "is_member": True, "is_channel": True}


@pytest.mark.asyncio
async def test_send_message_to_conversation_id(
    mock_context,
    mock_chat_slack_client,
):
    mock_slack_response = Mock(spec=AsyncSlackResponse)
    mock_slack_response.data = {"ok": True}
    mock_chat_slack_client.chat_postMessage.return_value = mock_slack_response

    response = await send_message(mock_context, conversation_id="abc123", message="Hello!")

    assert response["success"] is True
    assert response["data"]["ok"] is True
    mock_chat_slack_client.chat_postMessage.assert_called_once_with(channel="abc123", text="Hello!")


@pytest.mark.asyncio
async def test_send_message_to_username(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
):
    mock_chat_slack_client.auth_test.return_value = {"ok": True, "user_id": "current_user_id"}
    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [{"name": "foo", "id": "bar"}],
            "response_metadata": {"next_cursor": "123"},
        },
        {
            "ok": True,
            "members": [{"name": "foobar", "id": "foobar_user_id"}],
        },
    ]
    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": {
            "id": "conversation_id",
            "is_im": True,
        },
    }
    mock_slack_response = Mock(spec=AsyncSlackResponse)
    mock_slack_response.data = {"ok": True}
    mock_chat_slack_client.chat_postMessage.return_value = mock_slack_response

    response = await send_message(
        context=mock_context,
        usernames=["foobar"],
        message="Hello, world!",
    )

    assert response["success"] is True
    assert response["data"]["ok"] is True

    mock_chat_slack_client.auth_test.assert_called_once()
    assert mock_user_retrieval_slack_client.users_list.call_count == 2
    mock_chat_slack_client.conversations_open.assert_called_once_with(
        users=[
            "current_user_id",
            "foobar_user_id",
        ],
        return_im=True,
    )
    mock_chat_slack_client.chat_postMessage.assert_called_once_with(
        channel="conversation_id",
        text="Hello, world!",
    )


@pytest.mark.asyncio
async def test_send_dm_to_inexistent_user(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
):
    mock_chat_slack_client.auth_test.return_value = {"ok": True, "user_id": "current_user_id"}
    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [{"name": "foo", "id": "bar"}],
    }

    with pytest.raises(RetryableToolError) as error:
        await send_message(mock_context, usernames=["inexistent_user"], message="Hello!")

    assert "inexistent_user" in error.value.message
    assert "foo" in error.value.additional_prompt_content
    assert "bar" in error.value.additional_prompt_content
    mock_user_retrieval_slack_client.users_list.assert_called_once()
    mock_chat_slack_client.conversations_open.assert_not_called()
    mock_chat_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_to_channel_success(
    mock_context,
    mock_chat_slack_client,
    mock_conversation_retrieval_slack_client,
):
    mock_conversation_retrieval_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [{"id": "channel_id", "name": "general", "is_member": True, "is_group": True}],
    }
    mock_slack_response = Mock(spec=AsyncSlackResponse)
    mock_slack_response.data = {"ok": True}
    mock_chat_slack_client.chat_postMessage.return_value = mock_slack_response

    response = await send_message(mock_context, channel_name="general", message="Hello, channel!")

    assert response["success"] is True
    assert response["data"]["ok"] is True
    mock_conversation_retrieval_slack_client.conversations_list.assert_called_once()
    mock_chat_slack_client.chat_postMessage.assert_called_once_with(
        channel="channel_id", text="Hello, channel!"
    )


@pytest.mark.asyncio
async def test_send_message_to_inexistent_channel(
    mock_context,
    mock_chat_slack_client,
    mock_conversation_retrieval_slack_client,
):
    mock_conversation_retrieval_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [
            {
                "id": "another_channel_id",
                "name": "another_channel",
                "is_member": True,
                "is_group": True,
            }
        ],
    }

    with pytest.raises(RetryableToolError) as error:
        await send_message(mock_context, channel_name="inexistent_channel", message="Hello!")

    assert "inexistent_channel" in error.value.message
    assert "another_channel" in error.value.additional_prompt_content
    assert "another_channel_id" in error.value.additional_prompt_content

    mock_conversation_retrieval_slack_client.conversations_list.assert_called_once()
    mock_chat_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_list_conversations_metadata_with_default_args(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info],
    }

    response = await list_conversations(mock_context)

    assert response["conversations"] == [extract_conversation_metadata(mock_channel_info)]
    assert response["next_cursor"] is None

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=None,
        exclude_archived=True,
        limit=MAX_PAGINATION_SIZE_LIMIT,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_list_conversations_metadata_with_more_pages(
    mock_context, mock_chat_slack_client, dummy_channel_factory, random_str_factory
):
    channel1 = dummy_channel_factory(is_channel=True)
    channel2 = dummy_channel_factory(is_im=True)
    channel3 = dummy_channel_factory(is_mpim=True)
    next_cursor = random_str_factory()

    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [channel1, channel2, channel3],
        "response_metadata": {"next_cursor": next_cursor},
    }

    response = await list_conversations(mock_context, limit=3)

    assert response["conversations"] == [
        extract_conversation_metadata(channel1),
        extract_conversation_metadata(channel2),
        extract_conversation_metadata(channel3),
    ]
    assert response["next_cursor"] == next_cursor


@pytest.mark.asyncio
async def test_list_conversations_metadata_filtering_single_conversation_type(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info],
    }

    response = await list_conversations(
        mock_context, conversation_types=[ConversationType.PUBLIC_CHANNEL]
    )

    assert response["conversations"] == [extract_conversation_metadata(mock_channel_info)]
    assert response["next_cursor"] is None

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=ConversationTypeSlackName.PUBLIC_CHANNEL.value,
        exclude_archived=True,
        limit=MAX_PAGINATION_SIZE_LIMIT,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_list_conversations_metadata_filtering_multiple_conversation_types(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info],
    }

    response = await list_conversations(
        mock_context,
        conversation_types=[
            ConversationType.PUBLIC_CHANNEL,
            ConversationType.PRIVATE_CHANNEL,
        ],
    )

    assert response["conversations"] == [extract_conversation_metadata(mock_channel_info)]
    assert response["next_cursor"] is None

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
        exclude_archived=True,
        limit=MAX_PAGINATION_SIZE_LIMIT,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_list_conversations_metadata_with_custom_pagination_args(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info] * 3,
        "response_metadata": {"next_cursor": "456"},
    }

    response = await list_conversations(mock_context, limit=3, next_cursor="123")

    assert response["conversations"] == [
        extract_conversation_metadata(mock_channel_info) for _ in range(3)
    ]
    assert response["next_cursor"] == "456"

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=None,
        exclude_archived=True,
        limit=3,
        cursor="123",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "faulty_slack_function_name, tool_function, tool_args",
    [
        ("users_list", send_message, {"usernames": ["testuser"], "message": "Hello!"}),
        ("conversations_list", send_message, {"channel_name": "general", "message": "Hello!"}),
    ],
)
async def test_tools_with_slack_error(
    mock_context, mock_chat_slack_client, faulty_slack_function_name, tool_function, tool_args
):
    mock_chat_slack_client.auth_test.return_value = {"ok": True, "user_id": "current_user_id"}
    getattr(mock_chat_slack_client, faulty_slack_function_name).side_effect = SlackApiError(
        message="test_slack_error",
        response={"ok": False, "error": "test_slack_error"},
    )

    with pytest.raises(ToolExecutionError) as e:
        await tool_function(mock_context, **tool_args)
        assert "test_slack_error" in str(e.value)


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_id(
    mock_context, mock_conversation_retrieval_slack_client, mock_channel_info
):
    mock_conversation_retrieval_slack_client.conversations_info.return_value = {
        "ok": True,
        "channel": mock_channel_info,
    }

    response = await get_conversation_metadata(mock_context, conversation_id="C12345")

    assert response == extract_conversation_metadata(mock_channel_info)
    mock_conversation_retrieval_slack_client.conversations_info.assert_called_once_with(
        channel="C12345",
        include_locale=True,
        include_num_members=True,
    )


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_id_slack_api_error(
    mock_context,
    mock_conversation_retrieval_slack_client,
    mock_channel_info,
):
    mock_conversation_retrieval_slack_client.conversations_info.side_effect = SlackApiError(
        message="channel_not_found",
        response={"ok": False, "error": "channel_not_found"},
    )

    with pytest.raises(ToolExecutionError) as e:
        await get_conversation_metadata(mock_context, conversation_id="C12345")

    assert "C12345" in e.value.message
    assert "not found" in e.value.message


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_channel_name(
    mock_context,
    mock_conversation_retrieval_slack_client,
    dummy_channel_factory,
    random_str_factory,
):
    channel_name = random_str_factory()
    channel1 = dummy_channel_factory(is_channel=True, name=f"{channel_name}_another_channel")
    channel2 = dummy_channel_factory(is_channel=True, name=channel_name)

    mock_conversation_retrieval_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [channel1, channel2],
    }

    response = await get_conversation_metadata(mock_context, channel_name=channel_name)

    assert response == extract_conversation_metadata(channel2)
    mock_conversation_retrieval_slack_client.conversations_list.assert_called_once_with(
        types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
        exclude_archived=True,
        limit=MAX_PAGINATION_SIZE_LIMIT,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_channel_name_triggering_pagination(
    mock_context,
    mock_conversation_retrieval_slack_client,
    dummy_channel_factory,
    random_str_factory,
):
    target_channel_name = random_str_factory()
    target_channel = dummy_channel_factory(is_channel=True, name=target_channel_name)
    another_channel = dummy_channel_factory(
        is_channel=True, name=f"{target_channel_name}_another_channel"
    )

    mock_conversation_retrieval_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [another_channel],
            "response_metadata": {"next_cursor": "123"},
        },
        {
            "ok": True,
            "channels": [target_channel],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await get_conversation_metadata(mock_context, channel_name=target_channel_name)

    assert response == extract_conversation_metadata(target_channel)
    assert mock_conversation_retrieval_slack_client.conversations_list.call_count == 2
    mock_conversation_retrieval_slack_client.conversations_list.assert_has_calls([
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor=None,
        ),
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor="123",
        ),
    ])


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_channel_name_not_found(
    mock_context,
    mock_conversation_retrieval_slack_client,
    dummy_channel_factory,
    random_str_factory,
):
    not_found_name = random_str_factory()
    channel1 = dummy_channel_factory(is_channel=True, name=f"{not_found_name}_first")
    channel2 = dummy_channel_factory(is_channel=True, name=f"{not_found_name}_second")

    mock_conversation_retrieval_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [channel1],
            "response_metadata": {"next_cursor": "123"},
        },
        {
            "ok": True,
            "channels": [channel2],
            "response_metadata": {"next_cursor": None},
        },
    ]

    with pytest.raises(RetryableToolError) as error:
        await get_conversation_metadata(mock_context, channel_name=not_found_name)

    assert "not found" in error.value.message
    assert not_found_name in error.value.message
    assert (
        json.dumps([
            {"id": channel1["id"], "name": channel1["name"]},
            {"id": channel2["id"], "name": channel2["name"]},
        ])
        in error.value.additional_prompt_content
    )

    assert mock_conversation_retrieval_slack_client.conversations_list.call_count == 2
    mock_conversation_retrieval_slack_client.conversations_list.assert_has_calls([
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor=None,
        ),
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor="123",
        ),
    ])


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_username(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_channel_factory,
):
    current_user = dummy_user_factory(id_="U1", name="current_user")
    other_user = dummy_user_factory(id_="U2", name="other_user")
    conversation = dummy_channel_factory(is_im=True)

    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": current_user["id"],
    }

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [current_user, other_user],
        "response_metadata": {"next_cursor": None},
    }

    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": conversation,
    }

    response = await get_conversation_metadata(mock_context, usernames=[other_user["name"]])

    assert response == extract_conversation_metadata(conversation)


@pytest.mark.asyncio
async def test_get_dm_conversation_metadata_by_username_not_found(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_channel_factory,
    random_str_factory,
):
    current_user = dummy_user_factory(id_="U1", name="current_user")
    other_user = dummy_user_factory(id_="U2", name="other_user")
    conversation = dummy_channel_factory(is_im=True)
    not_found_user_name = random_str_factory()

    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": current_user["id"],
    }

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [current_user, other_user],
        "response_metadata": {"next_cursor": None},
    }

    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": conversation,
    }

    with pytest.raises(RetryableToolError) as error:
        await get_conversation_metadata(mock_context, usernames=[not_found_user_name])

    assert "not found" in error.value.message
    assert not_found_user_name in error.value.message
    assert other_user["id"] in error.value.additional_prompt_content
    assert other_user["name"] in error.value.additional_prompt_content

    mock_chat_slack_client.conversations_open.assert_not_called()


@pytest.mark.asyncio
async def test_get_mpim_conversation_metadata_by_usernames(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_channel_factory,
):
    current_user = dummy_user_factory(id_="U1", name="current_user")
    other_user1 = dummy_user_factory(id_="U2", name="other_user1")
    other_user2 = dummy_user_factory(id_="U3", name="other_user2")
    other_user3 = dummy_user_factory(id_="U4", name="other_user3")
    other_user4 = dummy_user_factory(id_="U5", name="other_user4")

    conversation = dummy_channel_factory(is_mpim=True)

    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": current_user["id"],
    }

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [current_user, other_user1, other_user3],
            "response_metadata": {"next_cursor": "users_list_cursor1"},
        },
        {
            "ok": True,
            "members": [current_user, other_user2, other_user4],
            "response_metadata": {"next_cursor": None},
        },
    ]

    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": conversation,
    }

    response = await get_conversation_metadata(
        mock_context,
        usernames=[other_user1["name"], other_user2["name"]],
    )

    assert response == extract_conversation_metadata(conversation)

    mock_chat_slack_client.conversations_open.assert_called_once_with(
        users=[current_user["id"], other_user1["id"], other_user2["id"]],
        return_im=True,
    )


@pytest.mark.asyncio
async def test_get_mpim_conversation_metadata_by_user_ids_and_usernames(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_channel_factory,
):
    current_user = dummy_user_factory(id_="U1", name="current_user")
    other_user1 = dummy_user_factory(id_="U2", name="other_user1")
    other_user2 = dummy_user_factory(id_="U3", name="other_user2")
    other_user3 = dummy_user_factory(id_="U4", name="other_user3")
    other_user4 = dummy_user_factory(id_="U5", name="other_user4")

    conversation = dummy_channel_factory(is_mpim=True)

    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": current_user["id"],
    }

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [current_user, other_user1, other_user3],
            "response_metadata": {"next_cursor": "users_list_cursor1"},
        },
        {
            "ok": True,
            "members": [current_user, other_user2, other_user4],
            "response_metadata": {"next_cursor": None},
        },
    ]

    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": conversation,
    }

    response = await get_conversation_metadata(
        mock_context,
        user_ids=[other_user3["id"]],
        usernames=[other_user1["name"], other_user2["name"]],
    )

    assert response == extract_conversation_metadata(conversation)

    mock_chat_slack_client.conversations_open.assert_called_once_with(
        users=[other_user3["id"], current_user["id"], other_user1["id"], other_user2["id"]],
        return_im=True,
    )


@pytest.mark.asyncio
async def test_get_mpim_conversation_metadata_by_user_ids_usernames_and_emails(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_channel_factory,
):
    current_user = dummy_user_factory(id_="U1", name="current_user")
    other_user1 = dummy_user_factory(id_="U2", name="other_user1")
    other_user2 = dummy_user_factory(id_="U3", name="other_user2")
    other_user3 = dummy_user_factory(id_="U4", name="other_user3")
    other_user4 = dummy_user_factory(id_="U5", name="other_user4")
    other_user5 = dummy_user_factory(id_="U6", name="other_user5")

    conversation = dummy_channel_factory(is_mpim=True)

    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": current_user["id"],
    }

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [current_user, other_user1, other_user3],
            "response_metadata": {"next_cursor": "users_list_cursor1"},
        },
        {
            "ok": True,
            "members": [current_user, other_user2, other_user4],
            "response_metadata": {"next_cursor": None},
        },
    ]

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {
            "ok": True,
            "user": other_user5,
        },
    ]

    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": conversation,
    }

    response = await get_conversation_metadata(
        mock_context,
        user_ids=[other_user3["id"]],
        usernames=[other_user1["name"], other_user2["name"]],
        emails=[other_user5["profile"]["email"]],
    )

    assert response == extract_conversation_metadata(conversation)

    mock_chat_slack_client.conversations_open.assert_called_once_with(
        users=[
            other_user3["id"],
            current_user["id"],
            other_user1["id"],
            other_user2["id"],
            other_user5["id"],
        ],
        return_im=True,
    )


@pytest.mark.asyncio
async def test_get_users_in_conversation_by_id_with_conversation_and_user_paginations(
    mock_context,
    mock_chat_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    random_str_factory,
):
    conversation_id = random_str_factory()
    user1 = dummy_user_factory(id_="1")
    user2 = dummy_user_factory(id_="2")
    user3 = dummy_user_factory(id_="3")

    mock_chat_slack_client.conversations_members.side_effect = [
        {
            "ok": True,
            "members": [user1["id"], user2["id"]],
            "response_metadata": {"next_cursor": "conversations_members_cursor1"},
        },
        {
            "ok": True,
            "members": [user3["id"]],
            "response_metadata": {"next_cursor": "conversations_members_cursor2"},
        },
    ]

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": "users_list_cursor"},
        },
        {
            "ok": True,
            "members": [user3],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await get_users_in_conversation(
        context=mock_context,
        conversation_id=conversation_id,
        limit=3,
    )

    assert response == {
        "users": [
            cast_user_dict(user1),
            cast_user_dict(user2),
            cast_user_dict(user3),
        ],
        "next_cursor": "conversations_members_cursor2",
    }

    mock_chat_slack_client.conversations_members.assert_has_calls([
        call(
            channel=conversation_id,
            limit=3,
            cursor=None,
        ),
        call(
            channel=conversation_id,
            limit=1,
            cursor="conversations_members_cursor1",
        ),
    ])

    mock_user_retrieval_slack_client.users_list.assert_has_calls([
        call(
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor=None,
        ),
        call(
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor="users_list_cursor",
        ),
    ])


@pytest.mark.asyncio
async def test_get_users_in_conversation_by_channel_name(
    mock_context,
    mock_chat_slack_client,
    mock_conversation_retrieval_slack_client,
    mock_user_retrieval_slack_client,
    dummy_channel_factory,
    dummy_user_factory,
    random_str_factory,
):
    channel_name = random_str_factory()
    channel1 = dummy_channel_factory(is_channel=True, name=f"{channel_name}_another_channel")
    channel2 = dummy_channel_factory(is_channel=True, name=channel_name)

    mock_conversation_retrieval_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [channel1],
            "response_metadata": {"next_cursor": "123"},
        },
        {
            "ok": True,
            "channels": [channel2],
            "response_metadata": {"next_cursor": None},
        },
    ]

    user1 = dummy_user_factory(id_="1")
    user2 = dummy_user_factory(id_="2")

    mock_chat_slack_client.conversations_members.side_effect = [
        {
            "ok": True,
            "members": [user1["id"], user2["id"]],
            "response_metadata": {"next_cursor": None},
        },
    ]

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await get_users_in_conversation(mock_context, channel_name=channel_name)

    assert response == {
        "users": [
            cast_user_dict(user1),
            cast_user_dict(user2),
        ],
        "next_cursor": None,
    }


@pytest.mark.asyncio
async def test_get_users_in_conversation_by_channel_name_not_found(
    mock_context,
    mock_conversation_retrieval_slack_client,
    dummy_channel_factory,
    random_str_factory,
):
    not_found_channel_name = random_str_factory()
    channel1 = dummy_channel_factory(is_channel=True, name=f"{not_found_channel_name}_first")
    channel2 = dummy_channel_factory(is_channel=True, name=f"{not_found_channel_name}_second")

    mock_conversation_retrieval_slack_client.conversations_list.side_effect = [
        {
            "ok": True,
            "channels": [channel1],
            "response_metadata": {"next_cursor": "123"},
        },
        {
            "ok": True,
            "channels": [channel2],
            "response_metadata": {"next_cursor": None},
        },
    ]

    with pytest.raises(RetryableToolError) as error:
        await get_users_in_conversation(mock_context, channel_name=not_found_channel_name)

    assert "not found" in error.value.message
    assert not_found_channel_name in error.value.message
    assert (
        json.dumps([
            {"id": channel1["id"], "name": channel1["name"]},
            {"id": channel2["id"], "name": channel2["name"]},
        ])
        in error.value.additional_prompt_content
    )

    assert mock_conversation_retrieval_slack_client.conversations_list.call_count == 2
    mock_conversation_retrieval_slack_client.conversations_list.assert_has_calls([
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor=None,
        ),
        call(
            types=f"{ConversationTypeSlackName.PUBLIC_CHANNEL.value},{ConversationTypeSlackName.PRIVATE_CHANNEL.value}",
            exclude_archived=True,
            limit=MAX_PAGINATION_SIZE_LIMIT,
            cursor="123",
        ),
    ])


@pytest.mark.asyncio
async def test_get_messages_by_conversation_id(
    mock_context,
    mock_message_retrieval_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_message_factory,
):
    user = dummy_user_factory()
    message = dummy_message_factory(user_id=user["id"])

    mock_message_retrieval_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [message],
        "response_metadata": {"next_cursor": "cursor"},
    }

    mock_user_retrieval_slack_client.users_info.return_value = {
        "ok": True,
        "user": user,
    }

    response = await get_messages(mock_context, "C12345", limit=1)

    assert response["next_cursor"] == "cursor"
    assert len(response["messages"]) == 1
    returned_message = response["messages"][0]
    assert returned_message["user"] == {"id": user["id"], "name": user["name"]}
    assert returned_message["text"] == message["text"]

    mock_message_retrieval_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.message_retrieval.convert_relative_datetime_to_unix_timestamp")
@patch("arcade_slack.message_retrieval.datetime")
async def test_get_messages_by_conversation_id_with_relative_datetime_args(
    mock_datetime,
    mock_convert_relative_datetime_to_unix_timestamp,
    mock_context,
    mock_message_retrieval_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_message_factory,
):
    user = dummy_user_factory()
    message = dummy_message_factory(user_id=user["id"])

    mock_message_retrieval_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [message],
    }

    mock_user_retrieval_slack_client.users_info.return_value = {
        "ok": True,
        "user": user,
    }

    expected_oldest_timestamp = 1716489600
    expected_latest_timestamp = 1716403200

    mock_datetime.now.return_value = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    expected_current_unix_timestamp = int(mock_datetime.now.return_value.timestamp())
    mock_convert_relative_datetime_to_unix_timestamp.side_effect = [
        expected_latest_timestamp,
        expected_oldest_timestamp,
    ]

    response = await get_messages(
        context=mock_context,
        conversation_id="C12345",
        oldest_relative="02:00:00",
        latest_relative="01:00:00",
        limit=1,
    )

    assert response["next_cursor"] is None
    assert len(response["messages"]) == 1
    returned_message = response["messages"][0]
    assert returned_message["user"] == {"id": user["id"], "name": user["name"]}
    assert returned_message["text"] == message["text"]

    mock_convert_relative_datetime_to_unix_timestamp.assert_has_calls([
        call("01:00:00", expected_current_unix_timestamp),
        call("02:00:00", expected_current_unix_timestamp),
    ])
    mock_message_retrieval_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
        oldest=expected_oldest_timestamp,
        latest=expected_latest_timestamp,
    )


@pytest.mark.asyncio
@patch("arcade_slack.message_retrieval.convert_datetime_to_unix_timestamp")
async def test_get_messages_by_conversation_id_with_absolute_datetime_args(
    mock_convert_datetime_to_unix_timestamp,
    mock_context,
    mock_message_retrieval_slack_client,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
    dummy_message_factory,
):
    user = dummy_user_factory()
    message = dummy_message_factory(user_id=user["id"])

    mock_message_retrieval_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [message],
    }

    mock_user_retrieval_slack_client.users_info.return_value = {
        "ok": True,
        "user": user,
    }

    expected_latest_timestamp = 1716403200
    expected_oldest_timestamp = 1716489600

    mock_convert_datetime_to_unix_timestamp.side_effect = [
        expected_latest_timestamp,
        expected_oldest_timestamp,
    ]

    response = await get_messages(
        context=mock_context,
        conversation_id="C12345",
        oldest_datetime="2025-01-01 00:00:00",
        latest_datetime="2025-01-02 00:00:00",
        limit=1,
    )

    assert response["next_cursor"] is None
    assert len(response["messages"]) == 1
    returned_message = response["messages"][0]
    assert returned_message["user"] == {"id": user["id"], "name": user["name"]}
    assert returned_message["text"] == message["text"]

    mock_convert_datetime_to_unix_timestamp.assert_has_calls([
        call("2025-01-02 00:00:00"),
        call("2025-01-01 00:00:00"),
    ])
    mock_message_retrieval_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
        oldest=expected_oldest_timestamp,
        latest=expected_latest_timestamp,
    )


@pytest.mark.asyncio
async def test_get_messages_by_conversation_id_with_messed_oldest_args(
    mock_context, mock_message_retrieval_slack_client
):
    with pytest.raises(ToolExecutionError):
        await get_messages(
            context=mock_context,
            conversation_id="C12345",
            oldest_datetime="2025-01-01 00:00:00",
            oldest_relative="01:00:00",
        )

    mock_message_retrieval_slack_client.conversations_history.assert_not_called()


@pytest.mark.asyncio
async def test_get_messages_by_conversation_id_with_messed_latest_args(
    mock_context, mock_message_retrieval_slack_client
):
    with pytest.raises(ToolExecutionError):
        await get_messages(
            context=mock_context,
            conversation_id="C12345",
            latest_datetime="2025-01-01 00:00:00",
            latest_relative="01:00:00",
        )

    mock_message_retrieval_slack_client.conversations_history.assert_not_called()


@pytest.mark.asyncio
async def test_get_messages_by_channel_name(
    mock_context,
    mock_message_retrieval_slack_client,
    mock_conversation_retrieval_slack_client,
    mock_user_retrieval_slack_client,
    dummy_message_factory,
    dummy_user_factory,
):
    mock_conversation_retrieval_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [
            {
                "id": "C12345",
                "name": "general",
                "is_member": True,
                "is_channel": True,
            }
        ],
    }

    user = dummy_user_factory()
    message = dummy_message_factory(user_id=user["id"])
    mock_message_retrieval_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [message],
    }

    mock_user_retrieval_slack_client.users_info.return_value = {
        "ok": True,
        "user": user,
    }

    response = await get_messages(
        context=mock_context,
        channel_name="general",
        limit=1,
    )

    assert response["next_cursor"] is None
    assert len(response["messages"]) == 1
    returned_message = response["messages"][0]
    assert returned_message["user"] == {"id": user["id"], "name": user["name"]}
    assert returned_message["text"] == message["text"]

    mock_message_retrieval_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
    )
