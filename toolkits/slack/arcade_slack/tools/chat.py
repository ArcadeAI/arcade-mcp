from typing import Annotated, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from arcade_tdk.errors import ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT
from arcade_slack.conversation_retrieval import (
    get_channel_by_name,
    get_conversation_by_id,
)
from arcade_slack.message_retrieval import retrieve_messages_in_conversation
from arcade_slack.models import (
    ConversationType,
)
from arcade_slack.user_retrieval import (
    get_users_by_id,
    get_users_by_id_username_or_email,
)
from arcade_slack.utils import (
    async_paginate,
    extract_conversation_metadata,
    populate_users_in_messages,
    raise_for_users_not_found,
)


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
            "chat:write",
            "mpim:write",
            "im:write",
        ],
    )
)
async def send_message(
    context: ToolContext,
    message: Annotated[str, "The content of the message to send."],
    channel_name: Annotated[
        str | None,
        "The channel name to send the message to. Prefer providing a conversation_id, "
        "when available, since the performance is better.",
    ] = None,
    conversation_id: Annotated[str | None, "The conversation ID to send the message to."] = None,
    user_ids: Annotated[list[str] | None, "The Slack user IDs of the people to message."] = None,
    emails: Annotated[list[str] | None, "The emails of the people to message."] = None,
    usernames: Annotated[
        list[str] | None,
        "The Slack usernames of the people to message. Prefer providing user_ids and/or emails, "
        "when available, since the performance is better.",
    ] = None,
) -> Annotated[dict, "The response from the Slack API"]:
    """Send a message to a Channel, Direct Message (IM/DM), or Multi-Person (MPIM) conversation

    Provide exactly one of:
    - channel_name; or
    - conversation_id; or
    - any combination of user_ids, usernames, and/or emails.

    In case multiple user_ids, usernames, and/or emails are provided, the tool will open a
    multi-person conversation with the specified people and send the message to it.
    """
    if conversation_id and any([channel_name, user_ids, usernames, emails]):
        raise ToolExecutionError(
            "Provide exactly one of: channel_name, OR conversation_id, OR any combination of "
            "user_ids, usernames, and/or emails."
        )

    if not conversation_id:
        conversation = await get_conversation_metadata(
            context=context,
            channel_name=channel_name,
            user_ids=user_ids,
            usernames=usernames,
            emails=emails,
        )
        conversation_id = conversation["id"]

    slack_client = AsyncWebClient(token=context.get_auth_token_or_empty())
    response = await slack_client.chat_postMessage(channel=cast(str, conversation_id), text=message)
    return {"success": True, "data": response.data}


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "im:read",
            "mpim:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_users_in_conversation(
    context: ToolContext,
    conversation_id: Annotated[str | None, "The ID of the conversation to get users in."] = None,
    channel_name: Annotated[
        str | None,
        "The name of the channel to get users in. Prefer providing a conversation_id, "
        "when available, since the performance is better.",
    ] = None,
    # The user object is relatively small, so we allow a higher limit.
    limit: Annotated[
        int, "The maximum number of users to return. Defaults to 200. Maximum is 500."
    ] = 200,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[dict, "Information about each user in the conversation"]:
    """Get the users in a Slack conversation (Channel, DM/IM, or MPIM) by its ID or by channel name.

    Provide exactly one of conversation_id or channel_name. Prefer providing a conversation_id,
    when available, since the performance is better.
    """
    limit = max(1, min(limit, 500))

    if sum({bool(conversation_id), bool(channel_name)}) != 1:
        raise ToolExecutionError("Provide exactly one of conversation_id OR channel_name.")

    auth_token = context.get_auth_token_or_empty()

    if not conversation_id:
        channel = await get_channel_by_name(auth_token, cast(str, channel_name))
        conversation_id = channel["id"]

    slack_client = AsyncWebClient(token=auth_token)
    user_ids, next_cursor = await async_paginate(
        func=slack_client.conversations_members,
        response_key="members",
        limit=limit,
        next_cursor=next_cursor,
        channel=conversation_id,
    )

    response = await get_users_by_id(auth_token, user_ids)

    await raise_for_users_not_found(context, [response])

    return {
        "users": [user for user in response["users"] if not user.get("is_bot")],
        "next_cursor": next_cursor,
    }


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
            "channels:history",
            "groups:history",
            "mpim:history",
            "im:history",
        ]
    )
)
async def get_messages(
    context: ToolContext,
    conversation_id: Annotated[
        str | None,
        "The ID of the conversation to get messages from. Provide exactly one of conversation_id "
        "OR any combination of user_ids, usernames, and/or emails.",
    ] = None,
    channel_name: Annotated[
        str | None,
        "The name of the channel to get messages from. Prefer providing a conversation_id, "
        "when available, since the performance is better.",
    ] = None,
    user_ids: Annotated[
        list[str] | None, "The IDs of the users in the conversation to get messages from."
    ] = None,
    usernames: Annotated[
        list[str] | None,
        "The usernames of the users in the conversation to get messages from. Prefer providing"
        "user_ids and/or emails, when available, since the performance is better.",
    ] = None,
    emails: Annotated[
        list[str] | None,
        "The emails of the users in the conversation to get messages from.",
    ] = None,
    oldest_relative: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[
        # The message object can be relatively large, so we limit maximum to 100
        # to preserve LLM's context window and reduce the likelihood of hallucinations.
        int, "The maximum number of messages to return. Defaults to 20. Maximum is 100."
    ] = 20,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    "The messages in a Slack Channel, DM (direct message) or MPIM (multi-person) conversation.",
]:
    """Get messages in a Slack Channel, DM (direct message) or MPIM (multi-person) conversation.

    Provide exactly one of:
    - conversation_id; or
    - channel_name; or
    - any combination of user_ids, usernames, and/or emails.

    To filter messages by an absolute datetime, use 'oldest_datetime' and/or 'latest_datetime'. If
    only 'oldest_datetime' is provided, it will return messages from the oldest_datetime to the
    current time. If only 'latest_datetime' is provided, it will return messages since the
    beginning of the conversation to the latest_datetime.

    To filter messages by a relative datetime (e.g. 3 days ago, 1 hour ago, etc.), use
    'oldest_relative' and/or 'latest_relative'. If only 'oldest_relative' is provided, it will
    return messages from the oldest_relative to the current time. If only 'latest_relative' is
    provided, it will return messages from the current time to the latest_relative.

    Do not provide both 'oldest_datetime' and 'oldest_relative' or both 'latest_datetime' and
    'latest_relative'.

    Leave all arguments with the default None to get messages without date/time filtering"""
    limit = max(1, min(limit, 100))

    if not conversation_id:
        conversation = await get_conversation_metadata(
            context=context,
            channel_name=channel_name,
            user_ids=user_ids,
            usernames=usernames,
            emails=emails,
        )
        conversation_id = conversation["id"]

    response = await retrieve_messages_in_conversation(
        auth_token=context.get_auth_token_or_empty(),
        conversation_id=cast(str, conversation_id),
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )

    response["messages"] = await populate_users_in_messages(
        auth_token=context.get_auth_token_or_empty(),
        messages=response["messages"],
    )

    return cast(dict, response)


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_conversation_metadata(
    context: ToolContext,
    conversation_id: Annotated[str | None, "The ID of the conversation to get metadata for"] = None,
    channel_name: Annotated[
        str | None,
        "The name of the channel to get metadata for. Prefer providing a conversation_id, "
        "when available, since the performance is better.",
    ] = None,
    usernames: Annotated[
        list[str] | None,
        "The usernames of the users to get the conversation metadata. "
        "Prefer providing user_ids and/or emails, when available, since the performance is better.",
    ] = None,
    emails: Annotated[
        list[str] | None,
        "The emails of the users to get the conversation metadata.",
    ] = None,
    user_ids: Annotated[
        list[str] | None,
        "The IDs of the users to get the conversation metadata.",
    ] = None,
) -> Annotated[
    dict | None,
    "The conversation metadata.",
]:
    """Get metadata of a Channel, a Direct Message (IM / DM) or a Multi-Person (MPIM) conversation.

    Use this tool to retrieve metadata about a conversation with a conversation_id, a channel name,
    or by the user_id(s), username(s), and/or email(s) of the user(s) in the conversation.

    This tool does not return the messages in a conversation. To get the messages, use the
    'Slack.GetMessages' tool instead.

    Provide exactly one of:
    - conversation_id; or
    - channel_name; or
    - any combination of user_ids, usernames, and/or emails.
    """
    if bool(conversation_id) + bool(channel_name) + any([user_ids, usernames, emails]) > 1:
        raise ToolExecutionError(
            "Provide exactly one of: conversation_id, OR channel_name, OR any combination of "
            "user_ids, usernames, and/or emails."
        )

    auth_token = context.get_auth_token_or_empty()

    if conversation_id:
        return await get_conversation_by_id(auth_token, conversation_id)

    elif channel_name:
        return await get_channel_by_name(auth_token, channel_name)

    user_ids_list = user_ids if isinstance(user_ids, list) else []

    slack_client = AsyncWebClient(token=auth_token)

    try:
        current_user = await slack_client.auth_test()
    except SlackApiError as e:
        message = "Failed to get currently authenticated user's info."
        developer_message = f"{message} Slack error: '{e.response.get('error', 'unknown_error')}'"
        raise ToolExecutionError(message, developer_message)

    if current_user["user_id"] not in user_ids_list:
        user_ids_list.append(current_user["user_id"])

    if usernames or emails:
        other_users = await get_users_by_id_username_or_email(
            context=context,
            usernames=usernames,
            emails=emails,
        )
        user_ids_list.extend([user["id"] for user in other_users])

    try:
        response = await slack_client.conversations_open(users=user_ids_list, return_im=True)
        return dict(**extract_conversation_metadata(response["channel"]))
    except SlackApiError as e:
        message = "Failed to retrieve conversation metadata."
        slack_error = e.response.get("error", "unknown_error")
        raise ToolExecutionError(
            message=message,
            developer_message=f"{message} Slack error: '{slack_error}'",
        )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def list_conversations(
    context: ToolContext,
    conversation_types: Annotated[
        list[ConversationType] | None,
        "Optionally filter by the type(s) of conversations. Defaults to None (all types).",
    ] = None,
    # The conversation object is relatively small, so we allow a higher limit.
    limit: Annotated[
        int,
        f"The maximum number of conversations to list. Defaults to {MAX_PAGINATION_SIZE_LIMIT}. "
        "Maximum is 500.",
    ] = MAX_PAGINATION_SIZE_LIMIT,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[dict, "The list of conversations found with metadata"]:
    """List metadata for Slack conversations (channels, DMs, MPIMs) the user is a member of.

    This tool does not return the messages in a conversation. To get the messages, use the
    'Slack.GetMessages' tool instead. Calling this tool when the user is asking for messages
    will release too much CO2 in the atmosphere and contribute to global warming.
    """
    limit = max(1, min(limit, 500))

    if conversation_types:
        conversation_types_filter = ",".join(
            conversation_type.to_slack_name_str() for conversation_type in conversation_types
        )
    else:
        conversation_types_filter = None

    slack_client = AsyncWebClient(token=context.get_auth_token_or_empty())

    results, next_cursor = await async_paginate(
        slack_client.conversations_list,
        "channels",
        limit=limit,
        next_cursor=next_cursor,
        types=conversation_types_filter,
        exclude_archived=True,
    )

    return {
        "conversations": [
            dict(**extract_conversation_metadata(conversation))
            for conversation in results
            if conversation.get("is_im") or conversation.get("is_member")
        ],
        "next_cursor": next_cursor,
    }


##################################################################################
# NOTE: The tools below are kept here for backwards compatibility. Prefer using: #
# - send_message
# - get_messages
# - get_conversation_metadata
# - get_users_in_conversation
# - list_conversations
##################################################################################


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
            "chat:write",
            "mpim:write",
            "im:write",
        ],
    )
)
async def send_dm_to_user(
    context: ToolContext,
    user_name: Annotated[
        str,
        (
            "The Slack username of the person you want to message. "
            "Slack usernames are ALWAYS lowercase."
        ),
    ],
    message: Annotated[str, "The message you want to send"],
) -> Annotated[dict, "The response from the Slack API"]:
    """Send a direct message to a user in Slack.

    This tool is deprecated. Use `Slack.SendMessage` instead.
    """
    return await send_message(  # type: ignore[no-any-return]
        context=context,
        usernames=[user_name],
        message=message,
    )


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
            "chat:write",
            "mpim:write",
            "im:write",
        ],
    )
)
async def send_message_to_channel(
    context: ToolContext,
    channel_name: Annotated[str, "The Slack channel name where you want to send the message. "],
    message: Annotated[str, "The message you want to send"],
) -> Annotated[dict, "The response from the Slack API"]:
    """Send a message to a channel in Slack.

    This tool is deprecated. Use `Slack.SendMessage` instead.
    """
    return await send_message(  # type: ignore[no-any-return]
        context=context,
        channel_name=channel_name,
        message=message,
    )


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "im:read",
            "mpim:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_members_in_conversation_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get members for"],
    limit: Annotated[int | None, "The maximum number of members to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[dict, "Information about each member in the conversation"]:
    """Get the members of a conversation in Slack by the conversation's ID.

    This tool is deprecated. Use the `Slack.GetUsersInConversation` tool instead.
    """
    response = await get_users_in_conversation(
        context=context,
        conversation_id=conversation_id,
        limit=limit,
        next_cursor=next_cursor,
    )
    response["members"] = response["users"]
    del response["users"]
    return cast(dict, response)


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "im:read",
            "mpim:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_members_in_channel_by_name(
    context: ToolContext,
    channel_name: Annotated[str, "The name of the channel to get members for"],
    limit: Annotated[int | None, "The maximum number of members to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[dict, "The channel members' IDs and Names"]:
    """Get the members of a conversation in Slack by the conversation's name.

    This tool is deprecated. Use the `Slack.GetUsersInConversation` tool instead.
    """
    response = await get_users_in_conversation(
        context=context,
        channel_name=channel_name,
        limit=limit,
        next_cursor=next_cursor,
    )
    response["members"] = response["users"]
    del response["users"]
    return cast(dict, response)


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:history",
            "channels:read",
            "groups:history",
            "groups:read",
            "im:history",
            "im:read",
            "mpim:history",
            "mpim:read",
        ],
    )
)
async def get_messages_in_channel_by_name(
    context: ToolContext,
    channel_name: Annotated[str, "The name of the channel"],
    oldest_relative: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[int | None, "The maximum number of messages to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    (
        "The messages in a channel and next cursor for paginating results (when "
        "there are additional messages to retrieve)."
    ),
]:
    """Get the messages in a channel by the channel's name.

    This tool is deprecated. Use the `Slack.GetMessages` tool instead.

    To filter messages by an absolute datetime, use 'oldest_datetime' and/or 'latest_datetime'. If
    only 'oldest_datetime' is provided, it will return messages from the oldest_datetime to the
    current time. If only 'latest_datetime' is provided, it will return messages since the
    beginning of the channel to the latest_datetime.

    To filter messages by a relative datetime (e.g. 3 days ago, 1 hour ago, etc.), use
    'oldest_relative' and/or 'latest_relative'. If only 'oldest_relative' is provided, it will
    return messages from the oldest_relative to the current time. If only 'latest_relative' is
    provided, it will return messages from the current time to the latest_relative.

    Do not provide both 'oldest_datetime' and 'oldest_relative' or both 'latest_datetime' and
    'latest_relative'.

    Leave all arguments with the default None to get messages without date/time filtering"""
    return await get_messages(  # type: ignore[no-any-return]
        context=context,
        channel_name=channel_name,
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:history", "groups:history", "im:history", "mpim:history"],
    )
)
async def get_messages_in_conversation_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get history for"],
    oldest_relative: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[int | None, "The maximum number of messages to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    (
        "The messages in a conversation and next cursor for paginating results (when "
        "there are additional messages to retrieve)."
    ),
]:
    """Get the messages in a conversation by the conversation's ID.

    This tool is deprecated. Use the 'Slack.GetMessages' tool instead.

    A conversation can be a channel, a DM, or a group DM.

    To filter by an absolute datetime, use 'oldest_datetime' and/or 'latest_datetime'. If
    only 'oldest_datetime' is provided, it returns messages from the oldest_datetime to the
    current time. If only 'latest_datetime' is provided, it returns messages since the
    beginning of the conversation to the latest_datetime.

    To filter by a relative datetime (e.g. 3 days ago, 1 hour ago, etc.), use
    'oldest_relative' and/or 'latest_relative'. If only 'oldest_relative' is provided, it returns
    messages from the oldest_relative to the current time. If only 'latest_relative' is provided,
    it returns messages from the current time to the latest_relative.

    Do not provide both 'oldest_datetime' and 'oldest_relative' or both 'latest_datetime' and
    'latest_relative'.

    Leave all arguments with the default None to get messages without date/time filtering"""
    return await get_messages(  # type: ignore[no-any-return]
        context=context,
        conversation_id=conversation_id,
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(requires_auth=Slack(scopes=["im:history", "im:read", "users:read", "users:read.email"]))
async def get_messages_in_direct_message_conversation_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the user to get messages from"],
    oldest_relative: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[int | None, "The maximum number of messages to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    (
        "The messages in a direct message conversation and next cursor for paginating results "
        "when there are additional messages to retrieve."
    ),
]:
    """Get the messages in a direct conversation by the user's name.

    This tool is deprecated. Use the `Slack.GetMessages` tool instead.
    """
    return await get_messages(  # type: ignore[no-any-return]
        context=context,
        usernames=[username],
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(requires_auth=Slack(scopes=["im:history", "im:read", "users:read", "users:read.email"]))
async def get_messages_in_multi_person_dm_conversation_by_usernames(
    context: ToolContext,
    usernames: Annotated[list[str], "The usernames of the users to get messages from"],
    oldest_relative: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        str | None,
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        str | None,
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[int | None, "The maximum number of messages to return."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    (
        "The messages in a multi-person direct message conversation and next cursor for "
        "paginating results (when there are additional messages to retrieve)."
    ),
]:
    """Get the messages in a multi-person direct message conversation by the usernames.

    This tool is deprecated. Use the `Slack.GetMessages` tool instead.
    """
    return await get_messages(  # type: ignore[no-any-return]
        context=context,
        usernames=usernames,
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def list_conversations_metadata(
    context: ToolContext,
    conversation_types: Annotated[
        list[ConversationType] | None,
        "Optionally filter by the type(s) of conversations. Defaults to None (all types).",
    ] = None,
    limit: Annotated[int | None, "The maximum number of conversations to list."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
) -> Annotated[dict, "The list of conversations found with metadata"]:
    """
    List Slack conversations (channels, DMs, MPIMs) the user is a member of.

    This tool is deprecated. Use the `Slack.ListConversations` tool instead.

    This tool does not return the messages in a conversation. To get the messages, use the
    'Slack.GetMessages' tool instead. Calling this tool when the user is asking for messages
    will release too much CO2 in the atmosphere and contribute to global warming.
    """
    return await list_conversations(  # type: ignore[no-any-return]
        context=context,
        conversation_types=conversation_types,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:read"],
    )
)
async def list_public_channels_metadata(
    context: ToolContext,
    limit: Annotated[int | None, "The maximum number of channels to list."] = None,
) -> Annotated[dict, "The public channels"]:
    """List metadata for public channels in Slack that the user is a member of.

    This tool is deprecated. Use the `Slack.ListConversations` tool instead.
    """
    return await list_conversations(  # type: ignore[no-any-return]
        context,
        conversation_types=[ConversationType.PUBLIC_CHANNEL],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["groups:read"],
    )
)
async def list_private_channels_metadata(
    context: ToolContext,
    limit: Annotated[int | None, "The maximum number of channels to list."] = None,
) -> Annotated[dict, "The private channels"]:
    """List metadata for private channels in Slack that the user is a member of.

    This tool is deprecated. Use the `Slack.ListConversations` tool instead.
    """
    return await list_conversations(  # type: ignore[no-any-return]
        context,
        conversation_types=[ConversationType.PRIVATE_CHANNEL],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["mpim:read"],
    )
)
async def list_group_direct_message_conversations_metadata(
    context: ToolContext,
    limit: Annotated[int | None, "The maximum number of conversations to list."] = None,
) -> Annotated[dict, "The group direct message conversations metadata"]:
    """List metadata for group direct message conversations that the user is a member of.

    This tool is deprecated. Use the `Slack.ListConversations` tool instead.
    """
    return await list_conversations(  # type: ignore[no-any-return]
        context,
        conversation_types=[ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
        limit=limit,
    )


# Note: Bots are included in the results.
# Note: Direct messages with no conversation history are included in the results.
@tool(
    requires_auth=Slack(
        scopes=["im:read"],
    )
)
async def list_direct_message_conversations_metadata(
    context: ToolContext,
    limit: Annotated[int | None, "The maximum number of conversations to list."] = None,
) -> Annotated[dict, "The direct message conversations metadata"]:
    """List metadata for direct message conversations in Slack that the user is a member of.

    This tool is deprecated. Use the `Slack.ListConversations` tool instead.
    """
    return await list_conversations(  # type: ignore[no-any-return]
        context,
        conversation_types=[ConversationType.DIRECT_MESSAGE],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_conversation_metadata_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack searching by its ID.

    This tool is deprecated. Use the `Slack.GetConversationMetadata` tool instead.
    """
    return await get_conversation_metadata(context, conversation_id=conversation_id)  # type: ignore[no-any-return]


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_channel_metadata_by_name(
    context: ToolContext,
    channel_name: Annotated[str, "The name of the channel to get metadata for"],
    # We kept the `next_cursor` argument for backwards compatibility, but it isn't actually used,
    # since this tool never really paginates.
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[dict, "The channel metadata"]:
    """Get the metadata of a channel in Slack searching by its name.

    This tool is deprecated. Use the `Slack.GetConversationMetadata` tool instead."""
    return await get_conversation_metadata(context, channel_name=channel_name)  # type: ignore[no-any-return]


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_direct_message_conversation_metadata_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the user/person to get messages with"],
    # We kept the `next_cursor` argument for backwards compatibility, but it isn't actually used,
    # since this tool never really paginates.
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[
    dict | None,
    "The direct message conversation metadata.",
]:
    """Get the metadata of a direct message conversation in Slack by the username.

    This tool is deprecated. Use the `Slack.GetConversationMetadata` tool instead."""
    return await get_conversation_metadata(context, usernames=[username])  # type: ignore[no-any-return]


@tool(
    requires_auth=Slack(
        scopes=[
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            "users:read",
            "users:read.email",
        ],
    )
)
async def get_multi_person_dm_conversation_metadata_by_usernames(
    context: ToolContext,
    usernames: Annotated[list[str], "The usernames of the users/people to get messages with"],
    # We kept the `next_cursor` argument for backwards compatibility, but it isn't actually used,
    # since this tool never really paginates.
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[
    dict | None,
    "The multi-person direct message conversation metadata.",
]:
    """Get the metadata of a multi-person direct message conversation in Slack by the usernames.

    This tool is deprecated. Use the `Slack.GetConversationMetadata` tool instead."""
    return await get_conversation_metadata(context, usernames=usernames)  # type: ignore[no-any-return]
