import json
from unittest.mock import Mock, call

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT
from arcade_slack.models import ConversationType, ConversationTypeSlackName
from arcade_slack.tools.chat import (
    get_conversation_metadata,
    list_conversations,
    send_message,
)
from arcade_slack.utils import extract_conversation_metadata


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
async def test_get_channel_metadata_by_name_triggering_pagination(
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
async def test_get_channel_metadata_by_name_not_found(
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


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.async_paginate")
# @patch("arcade_slack.tools.chat.get_user_info_by_id")
# async def test_get_members_from_conversation_id(
#     mock_get_user_info_by_id, mock_async_paginate, mock_context, mock_chat_slack_client
# ):
#     member1 = {"id": "U123", "name": "testuser123"}
#     member1_info = extract_basic_user_info(member1)
#     member2 = {"id": "U456", "name": "testuser456"}
#     member2_info = extract_basic_user_info(member2)

#     mock_async_paginate.return_value = [member1["id"], member2["id"]], "token123"
#     mock_get_user_info_by_id.side_effect = [member1_info, member2_info]

#     response = await get_members_in_conversation_by_id(
#         mock_context, conversation_id="C12345", limit=2
#     )

#     assert response == {
#         "members": [member1_info, member2_info],
#         "next_cursor": "token123",
#     }
#     mock_async_paginate.assert_called_once_with(
#         mock_chat_slack_client.conversations_members,
#         "members",
#         limit=2,
#         next_cursor=None,
#         channel="C12345",
#     )
#     mock_get_user_info_by_id.assert_has_calls([
#         call(mock_context, member1["id"]),
#         call(mock_context, member2["id"]),
#     ])


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.async_paginate")
# @patch("arcade_slack.tools.chat.get_user_info_by_id")
# @patch("arcade_slack.tools.chat.list_conversations_metadata")
# async def test_get_members_from_conversation_id_channel_not_found(
#     mock_list_conversations_metadata,
#     mock_get_user_info_by_id,
#     mock_async_paginate,
#     mock_context,
#     mock_chat_slack_client,
#     mock_channel_info,
# ):
#     conversations = [extract_conversation_metadata(mock_channel_info)] * 2
#     mock_list_conversations_metadata.return_value = {
#         "conversations": conversations,
#         "next_cursor": None,
#     }

#     member1 = {"id": "U123", "name": "testuser123"}
#     member1_info = extract_basic_user_info(member1)
#     member2 = {"id": "U456", "name": "testuser456"}
#     member2_info = extract_basic_user_info(member2)

#     mock_async_paginate.side_effect = SlackApiError(
#         message="channel_not_found",
#         response={"ok": False, "error": "channel_not_found"},
#     )
#     mock_get_user_info_by_id.side_effect = [member1_info, member2_info]

#     with pytest.raises(RetryableToolError):
#         await get_members_in_conversation_by_id(mock_context, conversation_id="C12345", limit=2)

#     mock_async_paginate.assert_called_once_with(
#         mock_chat_slack_client.conversations_members,
#         "members",
#         limit=2,
#         next_cursor=None,
#         channel="C12345",
#     )
#     mock_get_user_info_by_id.assert_not_called()


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.list_conversations_metadata")
# @patch("arcade_slack.tools.chat.get_members_in_conversation_by_id")
# async def test_get_members_in_channel_by_name(
#     mock_get_members_in_conversation_by_id,
#     mock_list_conversations_metadata,
#     mock_context,
#     mock_channel_info,
# ):
#     mock_list_conversations_metadata.return_value = {
#         "conversations": [extract_conversation_metadata(mock_channel_info)],
#         "next_cursor": None,
#     }

#     response = await get_members_in_channel_by_name(
#         mock_context, mock_channel_info["name"], limit=2
#     )

#     assert response == mock_get_members_in_conversation_by_id.return_value
#     mock_list_conversations_metadata.assert_called_once_with(
#         context=mock_context,
#         conversation_types=[
#             ConversationType.PUBLIC_CHANNEL,
#             ConversationType.PRIVATE_CHANNEL,
#         ],
#         next_cursor=None,
#     )
#     mock_get_members_in_conversation_by_id.assert_called_once_with(
#         context=mock_context,
#         conversation_id="C12345",
#         limit=2,
#         next_cursor=None,
#     )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.list_conversations_metadata")
# @patch("arcade_slack.tools.chat.get_members_in_conversation_by_id")
# async def test_get_members_in_channel_by_name_triggering_pagination(
#     mock_get_members_in_conversation_by_id,
#     mock_list_conversations_metadata,
#     mock_context,
#     mock_channel_info,
# ):
#     conversation1 = copy.deepcopy(mock_channel_info)
#     conversation1["name"] = "conversation1"
#     conversation2 = copy.deepcopy(mock_channel_info)
#     conversation2["name"] = "conversation2"

#     mock_list_conversations_metadata.side_effect = [
#         {
#             "conversations": [extract_conversation_metadata(conversation1)],
#             "next_cursor": "123",
#         },
#         {
#             "conversations": [extract_conversation_metadata(conversation2)],
#             "next_cursor": None,
#         },
#     ]

#     response = await get_members_in_channel_by_name(mock_context, conversation2["name"], limit=2)

#     assert response == mock_get_members_in_conversation_by_id.return_value
#     mock_list_conversations_metadata.assert_has_calls([
#         call(
#             context=mock_context,
#             conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
#             next_cursor=None,
#         ),
#         call(
#             context=mock_context,
#             conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
#             next_cursor="123",
#         ),
#     ])
#     mock_get_members_in_conversation_by_id.assert_called_once_with(
#         context=mock_context,
#         conversation_id="C12345",
#         limit=2,
#         next_cursor=None,
#     )


# @pytest.mark.asyncio
# async def test_get_conversation_history_by_id(mock_context, mock_chat_slack_client):
#     mock_chat_slack_client.conversations_history.return_value = {
#         "ok": True,
#         "messages": [{"text": "Hello, world!"}],
#     }

#     response = await get_messages_in_conversation_by_id(mock_context, "C12345", limit=1)

#     assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
#     mock_chat_slack_client.conversations_history.assert_called_once_with(
#         channel="C12345",
#         include_all_metadata=True,
#         inclusive=True,
#         limit=1,
#         cursor=None,
#     )


# # TODO: pass a current unix timestamp to the tool, instead of mocking the datetime
# # conversion. Have to wait until arcade.core.annotations.Inferrable is implemented.
# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.convert_relative_datetime_to_unix_timestamp")
# @patch("arcade_slack.tools.chat.datetime")
# async def test_get_conversation_history_by_id_with_relative_datetime_args(
#     mock_datetime,
#     mock_convert_relative_datetime_to_unix_timestamp,
#     mock_context,
#     mock_chat_slack_client,
# ):
#     mock_chat_slack_client.conversations_history.return_value = {
#         "ok": True,
#         "messages": [{"text": "Hello, world!"}],
#     }

#     expected_oldest_timestamp = 1716489600
#     expected_latest_timestamp = 1716403200

#     # Ideally we'd pass the current unix timestamp to the function, instead of mocking, but
#     # currently there's no way to have a tool argument that is not exposed to the LLM. We
#     # should have that soon, though.
#     mock_datetime.now.return_value = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
#     expected_current_unix_timestamp = int(mock_datetime.now.return_value.timestamp())
#     mock_convert_relative_datetime_to_unix_timestamp.side_effect = [
#         expected_latest_timestamp,
#         expected_oldest_timestamp,
#     ]

#     response = await get_messages_in_conversation_by_id(
#         mock_context, "C12345", oldest_relative="02:00:00", latest_relative="01:00:00", limit=1
#     )

#     assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
#     mock_convert_relative_datetime_to_unix_timestamp.assert_has_calls([
#         call("01:00:00", expected_current_unix_timestamp),
#         call("02:00:00", expected_current_unix_timestamp),
#     ])
#     mock_chat_slack_client.conversations_history.assert_called_once_with(
#         channel="C12345",
#         include_all_metadata=True,
#         inclusive=True,
#         limit=1,
#         cursor=None,
#         oldest=expected_oldest_timestamp,
#         latest=expected_latest_timestamp,
#     )


# # TODO: pass a current unix timestamp to the tool, instead of mocking the datetime
# # conversion. Have to wait until arcade.core.annotations.Inferrable is implemented.
# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.convert_datetime_to_unix_timestamp")
# async def test_get_conversation_history_by_id_with_absolute_datetime_args(
#     mock_convert_datetime_to_unix_timestamp, mock_context, mock_chat_slack_client
# ):
#     mock_chat_slack_client.conversations_history.return_value = {
#         "ok": True,
#         "messages": [{"text": "Hello, world!"}],
#     }

#     expected_latest_timestamp = 1716403200
#     expected_oldest_timestamp = 1716489600

#     # Ideally we'd pass the current unix timestamp to the function, instead of mocking, but
#     # currently there's no way to have a tool argument that is not exposed to the LLM. We
#     # should have that soon, though.
#     mock_convert_datetime_to_unix_timestamp.side_effect = [
#         expected_latest_timestamp,
#         expected_oldest_timestamp,
#     ]

#     response = await get_messages_in_conversation_by_id(
#         mock_context,
#         "C12345",
#         oldest_datetime="2025-01-01 00:00:00",
#         latest_datetime="2025-01-02 00:00:00",
#         limit=1,
#     )

#     assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
#     mock_convert_datetime_to_unix_timestamp.assert_has_calls([
#         call("2025-01-02 00:00:00"),
#         call("2025-01-01 00:00:00"),
#     ])
#     mock_chat_slack_client.conversations_history.assert_called_once_with(
#         channel="C12345",
#         include_all_metadata=True,
#         inclusive=True,
#         limit=1,
#         cursor=None,
#         oldest=expected_oldest_timestamp,
#         latest=expected_latest_timestamp,
#     )


# @pytest.mark.asyncio
# async def test_get_conversation_history_by_id_with_messed_oldest_args(
#     mock_context, mock_chat_slack_client
# ):
#     with pytest.raises(ToolExecutionError):
#         await get_messages_in_conversation_by_id(
#             mock_context,
#             "C12345",
#             oldest_datetime="2025-01-01 00:00:00",
#             oldest_relative="01:00:00",
#         )


# @pytest.mark.asyncio
# async def test_get_conversation_history_by_id_with_messed_latest_args(
#     mock_context, mock_chat_slack_client
# ):
#     with pytest.raises(ToolExecutionError):
#         await get_messages_in_conversation_by_id(
#             mock_context,
#             "C12345",
#             latest_datetime="2025-01-01 00:00:00",
#             latest_relative="01:00:00",
#         )


# @pytest.mark.asyncio
# async def test_get_conversation_history_by_name(mock_context, mock_chat_slack_client):
#     mock_chat_slack_client.conversations_list.return_value = {
#         "ok": True,
#         "channels": [
#             {
#                 "id": "C12345",
#                 "name": "general",
#                 "is_member": True,
#                 "is_channel": True,
#             }
#         ],
#     }
#     mock_chat_slack_client.conversations_history.return_value = {
#         "ok": True,
#         "messages": [{"text": "Hello, world!"}],
#     }

#     response = await get_messages_in_channel_by_name(mock_context, "general", limit=1)

#     assert response == {"messages": [{"text": "Hello, world!"}], "next_cursor": None}
#     mock_chat_slack_client.conversations_history.assert_called_once_with(
#         channel="C12345", include_all_metadata=True, inclusive=True, limit=1, cursor=None
#     )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
# async def test_get_direct_message_conversation_metadata_by_user(
#     mock_retrieve_conversations_by_user_ids,
#     mock_context,
#     mock_chat_slack_client,
#     mock_user_retrieval_slack_client,
# ):
#     mock_chat_slack_client.auth_test.return_value = {
#         "ok": True,
#         "user_id": "U1",
#         "team_id": "T1",
#         "user": "user1",
#     }

#     mock_user_retrieval_slack_client.users_list.return_value = {
#         "ok": True,
#         "members": [
#             {"id": "U1", "name": "user1"},
#             {"id": "U2", "name": "user2"},
#         ],
#         "response_metadata": {"next_cursor": None},
#     }

#     conversation = {
#         "id": "C12345",
#         "type": ConversationTypeSlackName.IM.value,
#         "is_im": True,
#         "members": ["U1", "U2"],
#     }

#     mock_retrieve_conversations_by_user_ids.return_value = [conversation]

#     response = await get_direct_message_conversation_metadata_by_user(
#         context=mock_context, username_or_email="user2"
#     )

#     assert response == conversation
#     mock_retrieve_conversations_by_user_ids.assert_called_once_with(
#         list_conversations_func=list_conversations_metadata,
#         get_members_in_conversation_func=get_members_in_conversation_by_id,
#         context=mock_context,
#         conversation_types=[ConversationType.DIRECT_MESSAGE],
#         user_ids=["U1", "U2"],
#         exact_match=True,
#         limit=1,
#         next_cursor=None,
#     )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
# async def test_get_direct_message_conversation_metadata_by_user_username_not_found(
#     mock_retrieve_conversations_by_user_ids,
#     mock_context,
#     mock_chat_slack_client,
#     mock_user_retrieval_slack_client,
# ):
#     mock_chat_slack_client.users_identity.return_value = {
#         "ok": True,
#         "user": {"id": "U1", "name": "user1"},
#         "team": {"id": "T1", "name": "team1"},
#     }

#     mock_user_retrieval_slack_client.users_list.return_value = {
#         "ok": True,
#         "members": [
#             {"id": "U1", "name": "user1"},
#             {"id": "U2", "name": "user2"},
#         ],
#         "response_metadata": {"next_cursor": None},
#     }

#     mock_retrieve_conversations_by_user_ids.side_effect = TimeoutError()

#     with pytest.raises(RetryableToolError):
#         await get_direct_message_conversation_metadata_by_user(
#             context=mock_context, username_or_email="user999"
#         )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.get_messages_in_conversation_by_id")
# @patch("arcade_slack.tools.chat.get_direct_message_conversation_metadata_by_user")
# async def test_get_messages_in_direct_conversation_by_username(
#     mock_get_direct_message_conversation_metadata_by_user,
#     mock_get_messages_in_conversation_by_id,
#     mock_context,
# ):
#     mock_get_direct_message_conversation_metadata_by_user.return_value = {
#         "id": "C12345",
#     }

#     response = await get_messages_in_direct_message_conversation_by_user(
#         context=mock_context, username_or_email="user2"
#     )

#     assert response == mock_get_messages_in_conversation_by_id.return_value
#     mock_get_direct_message_conversation_metadata_by_user.assert_called_once_with(
#         context=mock_context, username_or_email="user2"
#     )
#     mock_get_messages_in_conversation_by_id.assert_called_once_with(
#         context=mock_context,
#         conversation_id="C12345",
#         oldest_relative=None,
#         latest_relative=None,
#         oldest_datetime=None,
#         latest_datetime=None,
#         limit=None,
#         next_cursor=None,
#     )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.get_direct_message_conversation_metadata_by_user")
# async def test_get_messages_in_direct_conversation_by_username_not_found(
#     mock_get_direct_message_conversation_metadata_by_user,
#     mock_context,
# ):
#     mock_get_direct_message_conversation_metadata_by_user.return_value = None

#     with pytest.raises(ToolExecutionError):
#         await get_messages_in_direct_message_conversation_by_user(
#             context=mock_context, username_or_email="user2"
#         )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
# async def test_get_multi_person_direct_message_conversation_metadata_by_username(
#     mock_retrieve_conversations_by_user_ids,
#     mock_context,
#     mock_chat_slack_client,
#     mock_user_retrieval_slack_client,
# ):
#     mock_chat_slack_client.auth_test.return_value = {
#         "ok": True,
#         "user_id": "U1",
#         "team_id": "T1",
#         "user": "user1",
#     }

#     mock_user_retrieval_slack_client.users_list.return_value = {
#         "ok": True,
#         "members": [
#             {"id": "U1", "name": "user1"},
#             {"id": "U2", "name": "user2"},
#             {"id": "U3", "name": "user3"},
#             {"id": "U4", "name": "user4"},
#             {"id": "U5", "name": "user5"},
#         ],
#         "response_metadata": {"next_cursor": None},
#     }

#     conversation = {
#         "id": "C12345",
#         "type": ConversationTypeSlackName.MPIM.value,
#         "is_mpim": True,
#         "members": ["U1", "U4", "U5"],
#     }

#     mock_retrieve_conversations_by_user_ids.return_value = [conversation]

#     response = await get_multi_person_dm_conversation_metadata_by_users(
#         context=mock_context, usernames_or_emails=["user1", "user4", "user5"]
#     )

#     assert response == conversation
#     mock_retrieve_conversations_by_user_ids.assert_called_once_with(
#         list_conversations_func=list_conversations_metadata,
#         get_members_in_conversation_func=get_members_in_conversation_by_id,
#         context=mock_context,
#         conversation_types=[ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
#         user_ids=["U1", "U4", "U5"],
#         exact_match=True,
#         limit=1,
#         next_cursor=None,
#     )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.retrieve_conversations_by_user_ids")
# async def test_get_multi_person_direct_message_conversation_metadata_by_username_username_not_found(
#     mock_retrieve_conversations_by_user_ids,
#     mock_context,
#     mock_chat_slack_client,
#     mock_user_retrieval_slack_client,
# ):
#     mock_chat_slack_client.users_identity.return_value = {
#         "ok": True,
#         "user": {"id": "U1", "name": "user1"},
#         "team": {"id": "T1", "name": "team1"},
#     }

#     mock_user_retrieval_slack_client.users_list.return_value = {
#         "ok": True,
#         "members": [
#             {"id": "U1", "name": "user1"},
#             {"id": "U2", "name": "user2"},
#         ],
#         "response_metadata": {"next_cursor": None},
#     }

#     mock_retrieve_conversations_by_user_ids.side_effect = TimeoutError()

#     with pytest.raises(RetryableToolError):
#         await get_multi_person_dm_conversation_metadata_by_users(
#             context=mock_context, usernames_or_emails=["user999", "user1", "user2"]
#         )


# @pytest.mark.asyncio
# @patch("arcade_slack.tools.chat.get_messages_in_conversation_by_id")
# @patch("arcade_slack.tools.chat.get_multi_person_dm_conversation_metadata_by_users")
# async def test_get_messages_in_multi_person_dm_conversation_by_users(
#     mock_get_multi_person_dm_conversation_metadata_by_users,
#     mock_get_messages_in_conversation_by_id,
#     mock_context,
# ):
#     mock_get_multi_person_dm_conversation_metadata_by_users.return_value = {
#         "id": "C12345",
#     }

#     response = await get_messages_in_multi_person_dm_conversation_by_users(
#         context=mock_context, usernames_or_emails=["user1", "user4", "user5"]
#     )

#     assert response == mock_get_messages_in_conversation_by_id.return_value

#     mock_get_multi_person_dm_conversation_metadata_by_users.assert_called_once_with(
#         context=mock_context, usernames_or_emails=["user1", "user4", "user5"]
#     )

#     mock_get_messages_in_conversation_by_id.assert_called_once_with(
#         context=mock_context,
#         conversation_id="C12345",
#         oldest_relative=None,
#         latest_relative=None,
#         oldest_datetime=None,
#         latest_datetime=None,
#         limit=None,
#         next_cursor=None,
#     )
