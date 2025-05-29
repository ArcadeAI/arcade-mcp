import copy
from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT
from arcade_slack.models import ConversationType, ConversationTypeSlackName
from arcade_slack.tools.chat import (
    get_channel_metadata_by_name,
    get_conversation_metadata_by_id,
    get_direct_message_conversation_metadata_by_username,
    get_members_in_channel_by_name,
    get_members_in_conversation_by_id,
    get_messages_in_channel_by_name,
    get_messages_in_conversation_by_id,
    get_messages_in_direct_message_conversation_by_username,
    get_messages_in_multi_person_dm_conversation_by_usernames,
    get_multi_person_dm_conversation_metadata_by_usernames,
    list_conversations_metadata,
    list_direct_message_conversations_metadata,
    list_group_direct_message_conversations_metadata,
    list_private_channels_metadata,
    list_public_channels_metadata,
    send_dm_to_user,
    send_message_to_channel,
)
from arcade_slack.utils import extract_basic_user_info, extract_conversation_metadata


@pytest.fixture
def mock_list_conversations_metadata(mocker):
    return mocker.patch("arcade_slack.tools.chat.list_conversations_metadata", autospec=True)


@pytest.fixture
def mock_channel_info() -> dict:
    return {"name": "general", "id": "C12345", "is_member": True, "is_channel": True}


@pytest.mark.asyncio
async def test_send_dm_to_user(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.users_list.return_value = {
        "ok": True,
        "members": [{"name": "testuser", "id": "U12345"}],
    }
    mock_chat_slack_client.conversations_open.return_value = {
        "ok": True,
        "channel": {"id": "D12345"},
    }
    mock_slack_response = Mock(spec=AsyncSlackResponse)
    mock_slack_response.data = {"ok": True}
    mock_chat_slack_client.chat_postMessage.return_value = mock_slack_response

    response = await send_dm_to_user(mock_context, "testuser", "Hello!")

    assert response["response"]["ok"] is True
    mock_chat_slack_client.users_list.assert_called_once()
    mock_chat_slack_client.conversations_open.assert_called_once_with(users=["U12345"])
    mock_chat_slack_client.chat_postMessage.assert_called_once_with(channel="D12345", text="Hello!")


@pytest.mark.asyncio
async def test_send_dm_to_inexistent_user(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.users_list.return_value = {
        "ok": True,
        "members": [{"name": "testuser", "id": "U12345"}],
    }

    with pytest.raises(RetryableToolError):
        await send_dm_to_user(mock_context, "inexistent_user", "Hello!")

    mock_chat_slack_client.users_list.assert_called_once()
    mock_chat_slack_client.conversations_open.assert_not_called()
    mock_chat_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_to_channel(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [{"id": "C12345", "name": "general", "is_member": True, "is_group": True}],
    }
    mock_slack_response = Mock(spec=AsyncSlackResponse)
    mock_slack_response.data = {"ok": True}
    mock_chat_slack_client.chat_postMessage.return_value = mock_slack_response

    response = await send_message_to_channel(mock_context, "general", "Hello, channel!")

    assert response["response"]["ok"] is True
    mock_chat_slack_client.conversations_list.assert_called_once()
    mock_chat_slack_client.chat_postMessage.assert_called_once_with(
        channel="C12345", text="Hello, channel!"
    )


@pytest.mark.asyncio
async def test_send_message_to_inexistent_channel(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [],
    }

    with pytest.raises(RetryableToolError):
        await send_message_to_channel(mock_context, "inexistent_channel", "Hello!")

    mock_chat_slack_client.conversations_list.assert_called_once()
    mock_chat_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_list_conversations_metadata_with_default_args(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info],
    }

    response = await list_conversations_metadata(mock_context)

    assert response["conversations"] == [extract_conversation_metadata(mock_channel_info)]
    assert response["next_cursor"] is None

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=",".join([conv_type.value for conv_type in ConversationTypeSlackName]),
        exclude_archived=True,
        limit=MAX_PAGINATION_SIZE_LIMIT,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_list_conversations_metadata_filtering_single_conversation_type(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_list.return_value = {
        "ok": True,
        "channels": [mock_channel_info],
    }

    response = await list_conversations_metadata(
        mock_context, conversation_types=ConversationType.PUBLIC_CHANNEL
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

    response = await list_conversations_metadata(
        mock_context,
        conversation_types=[
            ConversationTypeSlackName.PUBLIC_CHANNEL,
            ConversationTypeSlackName.PRIVATE_CHANNEL,
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

    response = await list_conversations_metadata(mock_context, limit=3, next_cursor="123")

    assert response["conversations"] == [
        extract_conversation_metadata(mock_channel_info) for _ in range(3)
    ]
    assert response["next_cursor"] == "456"

    mock_chat_slack_client.conversations_list.assert_called_once_with(
        types=",".join([conv_type.value for conv_type in ConversationTypeSlackName]),
        exclude_archived=True,
        limit=3,
        cursor="123",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "faulty_slack_function_name, tool_function, tool_args",
    [
        ("users_list", send_dm_to_user, ("testuser", "Hello!")),
        ("conversations_list", send_message_to_channel, ("general", "Hello!")),
    ],
)
async def test_tools_with_slack_error(
    mock_context, mock_chat_slack_client, faulty_slack_function_name, tool_function, tool_args
):
    getattr(mock_chat_slack_client, faulty_slack_function_name).side_effect = SlackApiError(
        message="test_slack_error",
        response={"ok": False, "error": "test_slack_error"},
    )

    with pytest.raises(ToolExecutionError) as e:
        await tool_function(mock_context, *tool_args)
        assert "test_slack_error" in str(e.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_function, conversation_type",
    [
        (list_public_channels_metadata, ConversationType.PUBLIC_CHANNEL),
        (list_private_channels_metadata, ConversationType.PRIVATE_CHANNEL),
        (
            list_group_direct_message_conversations_metadata,
            ConversationType.MULTI_PERSON_DIRECT_MESSAGE,
        ),
        (list_direct_message_conversations_metadata, ConversationType.DIRECT_MESSAGE),
    ],
)
async def test_list_channels_metadata(
    mock_context,
    mock_list_conversations_metadata,
    tool_function,
    conversation_type,
):
    response = await tool_function(mock_context, limit=3)

    mock_list_conversations_metadata.assert_called_once_with(
        mock_context, conversation_types=[conversation_type], limit=3
    )

    assert response == mock_list_conversations_metadata.return_value


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_id(
    mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_chat_slack_client.conversations_info.return_value = {
        "ok": True,
        "channel": mock_channel_info,
    }

    response = await get_conversation_metadata_by_id(mock_context, "C12345")

    assert response == extract_conversation_metadata(mock_channel_info)
    mock_chat_slack_client.conversations_info.assert_called_once_with(
        channel="C12345",
        include_locale=True,
        include_num_members=True,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.list_conversations_metadata")
async def test_get_conversation_metadata_by_id_slack_api_error(
    mock_list_conversations_metadata, mock_context, mock_chat_slack_client, mock_channel_info
):
    mock_channel_info["name"] = "whatever_conversation_should_be_present_in_additional_prompt"
    mock_list_conversations_metadata.return_value = {
        "conversations": [extract_conversation_metadata(mock_channel_info)],
        "response_metadata": {"next_cursor": None},
    }
    mock_chat_slack_client.conversations_info.side_effect = SlackApiError(
        message="channel_not_found",
        response={"ok": False, "error": "channel_not_found"},
    )

    with pytest.raises(RetryableToolError) as e:
        await get_conversation_metadata_by_id(mock_context, "C12345")

        assert (
            "whatever_conversation_should_be_present_in_additional_prompt"
            in e.additional_prompt_content
        )

    mock_chat_slack_client.conversations_info.assert_called_once_with(
        channel="C12345",
        include_locale=True,
        include_num_members=True,
    )
    mock_list_conversations_metadata.assert_called_once_with(mock_context)


@pytest.mark.asyncio
async def test_get_conversation_metadata_by_name(
    mock_context, mock_list_conversations_metadata, mock_channel_info
):
    sample_conversation = extract_conversation_metadata(mock_channel_info)
    mock_list_conversations_metadata.return_value = {
        "conversations": [sample_conversation],
        "next_cursor": None,
    }

    response = await get_channel_metadata_by_name(mock_context, sample_conversation["name"])

    assert response == sample_conversation
    mock_list_conversations_metadata.assert_called_once_with(
        context=mock_context,
        conversation_types=[
            ConversationType.PUBLIC_CHANNEL,
            ConversationType.PRIVATE_CHANNEL,
        ],
        next_cursor=None,
    )


@pytest.mark.asyncio
async def test_get_channel_metadata_by_name_triggering_pagination(
    mock_context, mock_list_conversations_metadata, mock_channel_info
):
    target_channel = extract_conversation_metadata(mock_channel_info)
    another_channel = extract_conversation_metadata(mock_channel_info)
    another_channel["name"] = "another_channel"

    mock_list_conversations_metadata.side_effect = [
        {
            "conversations": [another_channel],
            "next_cursor": "123",
        },
        {
            "conversations": [target_channel],
            "next_cursor": None,
        },
    ]

    response = await get_channel_metadata_by_name(mock_context, target_channel["name"])

    assert response == target_channel
    assert mock_list_conversations_metadata.call_count == 2
    mock_list_conversations_metadata.assert_has_calls([
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor=None,
        ),
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor="123",
        ),
    ])


@pytest.mark.asyncio
async def test_get_channel_metadata_by_name_not_found(
    mock_context, mock_list_conversations_metadata, mock_channel_info
):
    first_channel = extract_conversation_metadata(mock_channel_info)
    second_channel = extract_conversation_metadata(mock_channel_info)
    second_channel["name"] = "second_channel"

    mock_list_conversations_metadata.side_effect = [
        {
            "conversations": [second_channel],
            "next_cursor": "123",
        },
        {
            "conversations": [first_channel],
            "next_cursor": None,
        },
    ]

    with pytest.raises(RetryableToolError):
        await get_channel_metadata_by_name(mock_context, "inexistent_channel")

    assert mock_list_conversations_metadata.call_count == 2
    mock_list_conversations_metadata.assert_has_calls([
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor=None,
        ),
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor="123",
        ),
    ])


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.async_paginate")
@patch("arcade_slack.tools.chat.get_user_info_by_id")
async def test_get_members_from_conversation_id(
    mock_get_user_info_by_id, mock_async_paginate, mock_context, mock_chat_slack_client
):
    member1 = {"id": "U123", "name": "testuser123"}
    member1_info = extract_basic_user_info(member1)
    member2 = {"id": "U456", "name": "testuser456"}
    member2_info = extract_basic_user_info(member2)

    mock_async_paginate.return_value = [member1["id"], member2["id"]], "token123"
    mock_get_user_info_by_id.side_effect = [member1_info, member2_info]

    response = await get_members_in_conversation_by_id(
        mock_context, conversation_id="C12345", limit=2
    )

    assert response == {
        "members": [member1_info, member2_info],
        "next_cursor": "token123",
    }
    mock_async_paginate.assert_called_once_with(
        mock_chat_slack_client.conversations_members,
        "members",
        limit=2,
        next_cursor=None,
        channel="C12345",
    )
    mock_get_user_info_by_id.assert_has_calls([
        call(mock_context, member1["id"]),
        call(mock_context, member2["id"]),
    ])


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.async_paginate")
@patch("arcade_slack.tools.chat.get_user_info_by_id")
@patch("arcade_slack.tools.chat.list_conversations_metadata")
async def test_get_members_from_conversation_id_channel_not_found(
    mock_list_conversations_metadata,
    mock_get_user_info_by_id,
    mock_async_paginate,
    mock_context,
    mock_chat_slack_client,
    mock_channel_info,
):
    conversations = [extract_conversation_metadata(mock_channel_info)] * 2
    mock_list_conversations_metadata.return_value = {
        "conversations": conversations,
        "next_cursor": None,
    }

    member1 = {"id": "U123", "name": "testuser123"}
    member1_info = extract_basic_user_info(member1)
    member2 = {"id": "U456", "name": "testuser456"}
    member2_info = extract_basic_user_info(member2)

    mock_async_paginate.side_effect = SlackApiError(
        message="channel_not_found",
        response={"ok": False, "error": "channel_not_found"},
    )
    mock_get_user_info_by_id.side_effect = [member1_info, member2_info]

    with pytest.raises(RetryableToolError):
        await get_members_in_conversation_by_id(mock_context, conversation_id="C12345", limit=2)

    mock_async_paginate.assert_called_once_with(
        mock_chat_slack_client.conversations_members,
        "members",
        limit=2,
        next_cursor=None,
        channel="C12345",
    )
    mock_get_user_info_by_id.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.list_conversations_metadata")
@patch("arcade_slack.tools.chat.get_members_in_conversation_by_id")
async def test_get_members_in_channel_by_name(
    mock_get_members_in_conversation_by_id,
    mock_list_conversations_metadata,
    mock_context,
    mock_channel_info,
):
    mock_list_conversations_metadata.return_value = {
        "conversations": [extract_conversation_metadata(mock_channel_info)],
        "next_cursor": None,
    }

    response = await get_members_in_channel_by_name(
        mock_context, mock_channel_info["name"], limit=2
    )

    assert response == mock_get_members_in_conversation_by_id.return_value
    mock_list_conversations_metadata.assert_called_once_with(
        context=mock_context,
        conversation_types=[
            ConversationType.PUBLIC_CHANNEL,
            ConversationType.PRIVATE_CHANNEL,
        ],
        next_cursor=None,
    )
    mock_get_members_in_conversation_by_id.assert_called_once_with(
        context=mock_context,
        conversation_id="C12345",
        limit=2,
        next_cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.list_conversations_metadata")
@patch("arcade_slack.tools.chat.get_members_in_conversation_by_id")
async def test_get_members_in_channel_by_name_triggering_pagination(
    mock_get_members_in_conversation_by_id,
    mock_list_conversations_metadata,
    mock_context,
    mock_channel_info,
):
    conversation1 = copy.deepcopy(mock_channel_info)
    conversation1["name"] = "conversation1"
    conversation2 = copy.deepcopy(mock_channel_info)
    conversation2["name"] = "conversation2"

    mock_list_conversations_metadata.side_effect = [
        {
            "conversations": [extract_conversation_metadata(conversation1)],
            "next_cursor": "123",
        },
        {
            "conversations": [extract_conversation_metadata(conversation2)],
            "next_cursor": None,
        },
    ]

    response = await get_members_in_channel_by_name(mock_context, conversation2["name"], limit=2)

    assert response == mock_get_members_in_conversation_by_id.return_value
    mock_list_conversations_metadata.assert_has_calls([
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor=None,
        ),
        call(
            context=mock_context,
            conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
            next_cursor="123",
        ),
    ])
    mock_get_members_in_conversation_by_id.assert_called_once_with(
        context=mock_context,
        conversation_id="C12345",
        limit=2,
        next_cursor=None,
    )


@pytest.mark.asyncio
async def test_get_conversation_history_by_id(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [{"text": "Hello, world!"}],
    }

    response = await get_messages_in_conversation_by_id(mock_context, "C12345", limit=1)

    assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
    mock_chat_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
    )


# TODO: pass a current unix timestamp to the tool, instead of mocking the datetime
# conversion. Have to wait until arcade.core.annotations.Inferrable is implemented.
@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.convert_relative_datetime_to_unix_timestamp")
@patch("arcade_slack.tools.chat.datetime")
async def test_get_conversation_history_by_id_with_relative_datetime_args(
    mock_datetime,
    mock_convert_relative_datetime_to_unix_timestamp,
    mock_context,
    mock_chat_slack_client,
):
    mock_chat_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [{"text": "Hello, world!"}],
    }

    expected_oldest_timestamp = 1716489600
    expected_latest_timestamp = 1716403200

    # Ideally we'd pass the current unix timestamp to the function, instead of mocking, but
    # currently there's no way to have a tool argument that is not exposed to the LLM. We
    # should have that soon, though.
    mock_datetime.now.return_value = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    expected_current_unix_timestamp = int(mock_datetime.now.return_value.timestamp())
    mock_convert_relative_datetime_to_unix_timestamp.side_effect = [
        expected_latest_timestamp,
        expected_oldest_timestamp,
    ]

    response = await get_messages_in_conversation_by_id(
        mock_context, "C12345", oldest_relative="02:00:00", latest_relative="01:00:00", limit=1
    )

    assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
    mock_convert_relative_datetime_to_unix_timestamp.assert_has_calls([
        call("01:00:00", expected_current_unix_timestamp),
        call("02:00:00", expected_current_unix_timestamp),
    ])
    mock_chat_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
        oldest=expected_oldest_timestamp,
        latest=expected_latest_timestamp,
    )


# TODO: pass a current unix timestamp to the tool, instead of mocking the datetime
# conversion. Have to wait until arcade.core.annotations.Inferrable is implemented.
@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.convert_datetime_to_unix_timestamp")
async def test_get_conversation_history_by_id_with_absolute_datetime_args(
    mock_convert_datetime_to_unix_timestamp, mock_context, mock_chat_slack_client
):
    mock_chat_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [{"text": "Hello, world!"}],
    }

    expected_latest_timestamp = 1716403200
    expected_oldest_timestamp = 1716489600

    # Ideally we'd pass the current unix timestamp to the function, instead of mocking, but
    # currently there's no way to have a tool argument that is not exposed to the LLM. We
    # should have that soon, though.
    mock_convert_datetime_to_unix_timestamp.side_effect = [
        expected_latest_timestamp,
        expected_oldest_timestamp,
    ]

    response = await get_messages_in_conversation_by_id(
        mock_context,
        "C12345",
        oldest_datetime="2025-01-01 00:00:00",
        latest_datetime="2025-01-02 00:00:00",
        limit=1,
    )

    assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
    mock_convert_datetime_to_unix_timestamp.assert_has_calls([
        call("2025-01-02 00:00:00"),
        call("2025-01-01 00:00:00"),
    ])
    mock_chat_slack_client.conversations_history.assert_called_once_with(
        channel="C12345",
        include_all_metadata=True,
        inclusive=True,
        limit=1,
        cursor=None,
        oldest=expected_oldest_timestamp,
        latest=expected_latest_timestamp,
    )


@pytest.mark.asyncio
async def test_get_conversation_history_by_id_with_messed_oldest_args(
    mock_context, mock_chat_slack_client
):
    with pytest.raises(ToolExecutionError):
        await get_messages_in_conversation_by_id(
            mock_context,
            "C12345",
            oldest_datetime="2025-01-01 00:00:00",
            oldest_relative="01:00:00",
        )


@pytest.mark.asyncio
async def test_get_conversation_history_by_id_with_messed_latest_args(
    mock_context, mock_chat_slack_client
):
    with pytest.raises(ToolExecutionError):
        await get_messages_in_conversation_by_id(
            mock_context,
            "C12345",
            latest_datetime="2025-01-01 00:00:00",
            latest_relative="01:00:00",
        )


@pytest.mark.asyncio
async def test_get_conversation_history_by_name(mock_context, mock_chat_slack_client):
    mock_chat_slack_client.conversations_list.return_value = {
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
    mock_chat_slack_client.conversations_history.return_value = {
        "ok": True,
        "messages": [{"text": "Hello, world!"}],
    }

    response = await get_messages_in_channel_by_name(mock_context, "general", limit=1)

    assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
    mock_chat_slack_client.conversations_history.assert_called_once_with(
        channel="C12345", include_all_metadata=True, inclusive=True, limit=1, cursor=None
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
async def test_get_direct_message_conversation_metadata_by_username(
    mock_retrieve_conversations_by_user_ids,
    mock_context,
    mock_chat_slack_client,
    mock_users_slack_client,
):
    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": "U1",
        "team_id": "T1",
        "user": "user1",
    }

    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [
            {"id": "U1", "name": "user1"},
            {"id": "U2", "name": "user2"},
        ],
        "response_metadata": {"next_cursor": None},
    }

    conversation = {
        "id": "C12345",
        "type": ConversationTypeSlackName.IM.value,
        "is_im": True,
        "members": ["U1", "U2"],
    }

    mock_retrieve_conversations_by_user_ids.return_value = [conversation]

    response = await get_direct_message_conversation_metadata_by_username(
        context=mock_context, username="user2"
    )

    assert response == conversation
    mock_retrieve_conversations_by_user_ids.assert_called_once_with(
        list_conversations_func=list_conversations_metadata,
        get_members_in_conversation_func=get_members_in_conversation_by_id,
        context=mock_context,
        conversation_types=[ConversationType.DIRECT_MESSAGE],
        user_ids=["U1", "U2"],
        exact_match=True,
        limit=1,
        next_cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
async def test_get_direct_message_conversation_metadata_by_username_username_not_found(
    mock_retrieve_conversations_by_user_ids,
    mock_context,
    mock_chat_slack_client,
    mock_users_slack_client,
):
    mock_chat_slack_client.users_identity.return_value = {
        "ok": True,
        "user": {"id": "U1", "name": "user1"},
        "team": {"id": "T1", "name": "team1"},
    }

    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [
            {"id": "U1", "name": "user1"},
            {"id": "U2", "name": "user2"},
        ],
        "response_metadata": {"next_cursor": None},
    }

    mock_retrieve_conversations_by_user_ids.side_effect = TimeoutError()

    with pytest.raises(RetryableToolError):
        await get_direct_message_conversation_metadata_by_username(
            context=mock_context, username="user999"
        )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.get_messages_in_conversation_by_id")
@patch("arcade_slack.tools.chat.get_direct_message_conversation_metadata_by_username")
async def test_get_messages_in_direct_conversation_by_username(
    mock_get_direct_message_conversation_metadata_by_username,
    mock_get_messages_in_conversation_by_id,
    mock_context,
):
    mock_get_direct_message_conversation_metadata_by_username.return_value = {
        "id": "C12345",
    }

    response = await get_messages_in_direct_message_conversation_by_username(
        context=mock_context, username="user2"
    )

    assert response == mock_get_messages_in_conversation_by_id.return_value
    mock_get_direct_message_conversation_metadata_by_username.assert_called_once_with(
        context=mock_context, username="user2"
    )
    mock_get_messages_in_conversation_by_id.assert_called_once_with(
        context=mock_context,
        conversation_id="C12345",
        oldest_relative=None,
        latest_relative=None,
        oldest_datetime=None,
        latest_datetime=None,
        limit=None,
        next_cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.get_direct_message_conversation_metadata_by_username")
async def test_get_messages_in_direct_conversation_by_username_not_found(
    mock_get_direct_message_conversation_metadata_by_username,
    mock_context,
):
    mock_get_direct_message_conversation_metadata_by_username.return_value = None

    with pytest.raises(ToolExecutionError):
        await get_messages_in_direct_message_conversation_by_username(
            context=mock_context, username="user2"
        )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
async def test_get_multi_person_direct_message_conversation_metadata_by_username(
    mock_retrieve_conversations_by_user_ids,
    mock_context,
    mock_chat_slack_client,
    mock_users_slack_client,
):
    mock_chat_slack_client.auth_test.return_value = {
        "ok": True,
        "user_id": "U1",
        "team_id": "T1",
        "user": "user1",
    }

    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [
            {"id": "U1", "name": "user1"},
            {"id": "U2", "name": "user2"},
            {"id": "U3", "name": "user3"},
            {"id": "U4", "name": "user4"},
            {"id": "U5", "name": "user5"},
        ],
        "response_metadata": {"next_cursor": None},
    }

    conversation = {
        "id": "C12345",
        "type": ConversationTypeSlackName.MPIM.value,
        "is_mpim": True,
        "members": ["U1", "U4", "U5"],
    }

    mock_retrieve_conversations_by_user_ids.return_value = [conversation]

    response = await get_multi_person_dm_conversation_metadata_by_usernames(
        context=mock_context, usernames=["user1", "user4", "user5"]
    )

    assert response == conversation
    mock_retrieve_conversations_by_user_ids.assert_called_once_with(
        list_conversations_func=list_conversations_metadata,
        get_members_in_conversation_func=get_members_in_conversation_by_id,
        context=mock_context,
        conversation_types=[ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
        user_ids=["U1", "U4", "U5"],
        exact_match=True,
        limit=1,
        next_cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
async def test_get_multi_person_direct_message_conversation_metadata_by_username_username_not_found(
    mock_retrieve_conversations_by_user_ids,
    mock_context,
    mock_chat_slack_client,
    mock_users_slack_client,
):
    mock_chat_slack_client.users_identity.return_value = {
        "ok": True,
        "user": {"id": "U1", "name": "user1"},
        "team": {"id": "T1", "name": "team1"},
    }

    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [
            {"id": "U1", "name": "user1"},
            {"id": "U2", "name": "user2"},
        ],
        "response_metadata": {"next_cursor": None},
    }

    mock_retrieve_conversations_by_user_ids.side_effect = TimeoutError()

    with pytest.raises(RetryableToolError):
        await get_multi_person_dm_conversation_metadata_by_usernames(
            context=mock_context, usernames=["user999", "user1", "user2"]
        )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.get_messages_in_conversation_by_id")
@patch("arcade_slack.tools.chat.get_multi_person_dm_conversation_metadata_by_usernames")
async def test_get_messages_in_multi_person_dm_conversation_by_usernames(
    mock_get_multi_person_dm_conversation_metadata_by_usernames,
    mock_get_messages_in_conversation_by_id,
    mock_context,
):
    mock_get_multi_person_dm_conversation_metadata_by_usernames.return_value = {
        "id": "C12345",
    }

    response = await get_messages_in_multi_person_dm_conversation_by_usernames(
        context=mock_context, usernames=["user1", "user4", "user5"]
    )

    assert response == mock_get_messages_in_conversation_by_id.return_value

    mock_get_multi_person_dm_conversation_metadata_by_usernames.assert_called_once_with(
        context=mock_context, usernames=["user1", "user4", "user5"]
    )

    mock_get_messages_in_conversation_by_id.assert_called_once_with(
        context=mock_context,
        conversation_id="C12345",
        oldest_relative=None,
        latest_relative=None,
        oldest_datetime=None,
        latest_datetime=None,
        limit=None,
        next_cursor=None,
    )


@pytest.mark.asyncio
@patch("arcade_slack.tools.chat.get_multi_person_dm_conversation_metadata_by_usernames")
async def test_get_messages_in_multi_person_dm_conversation_by_usernames_not_found(
    mock_get_multi_person_dm_conversation_metadata_by_usernames,
    mock_context,
):
    mock_get_multi_person_dm_conversation_metadata_by_usernames.return_value = None

    with pytest.raises(ToolExecutionError):
        await get_messages_in_direct_message_conversation_by_username(
            context=mock_context, username="user2"
        )
