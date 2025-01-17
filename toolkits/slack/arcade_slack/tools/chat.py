import asyncio
import datetime
import time
from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack
from arcade.sdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_LIMIT
from arcade_slack.models import ConversationType, ConversationTypeUserFriendly
from arcade_slack.tools.users import get_user_info_by_id
from arcade_slack.utils import (
    async_paginate,
    convert_user_friendly_conversation_type,
    extract_conversation_metadata,
    format_channels,
    format_users,
)


@tool(
    requires_auth=Slack(
        scopes=[
            "chat:write",
            "im:write",
            "users.profile:read",
            "users:read",
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
    """Send a direct message to a user in Slack."""

    slackClient = AsyncWebClient(token=context.authorization.token)

    try:
        # Step 1: Retrieve the user's Slack ID based on their username
        userListResponse = await slackClient.users_list()
        user_id = None
        for user in userListResponse["members"]:
            if user["name"].lower() == user_name.lower():
                user_id = user["id"]
                break

        if not user_id:
            raise RetryableToolError(
                "User not found",
                developer_message=f"User with username '{user_name}' not found.",
                additional_prompt_content=format_users(userListResponse),
                retry_after_ms=500,  # Play nice with Slack API rate limits
            )

        # Step 2: Retrieve the DM channel ID with the user
        im_response = await slackClient.conversations_open(users=[user_id])
        dm_channel_id = im_response["channel"]["id"]

        # Step 3: Send the message as if it's from you (because we're using a user token)
        response = await slackClient.chat_postMessage(channel=dm_channel_id, text=message)

    except SlackApiError as e:
        error_message = e.response["error"] if "error" in e.response else str(e)
        raise ToolExecutionError(
            "Error sending message",
            developer_message=f"Slack API Error: {error_message}",
        )
    else:
        return {"response": response.data}


@tool(
    requires_auth=Slack(
        scopes=[
            "chat:write",
            "channels:read",
            "groups:read",
        ],
    )
)
async def send_message_to_channel(
    context: ToolContext,
    channel_name: Annotated[str, "The Slack channel name where you want to send the message. "],
    message: Annotated[str, "The message you want to send"],
) -> Annotated[dict, "The response from the Slack API"]:
    """Send a message to a channel in Slack."""

    try:
        slackClient = AsyncWebClient(
            token=context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        )

        # Step 1: Retrieve the list of channels
        channels_response = await slackClient.conversations_list()
        channel_id = None
        for channel in channels_response["channels"]:
            if channel["name"].lower() == channel_name.lower():
                channel_id = channel["id"]
                break

        if not channel_id:
            raise RetryableToolError(
                "Channel not found",
                developer_message=f"Channel with name '{channel_name}' not found.",
                additional_prompt_content=format_channels(channels_response),
                retry_after_ms=500,  # Play nice with Slack API rate limits
            )

        # Step 2: Send the message to the channel
        response = await slackClient.chat_postMessage(channel=channel_id, text=message)

    except SlackApiError as e:
        error_message = e.response["error"] if "error" in e.response else str(e)
        raise ToolExecutionError(
            "Error sending message",
            developer_message=f"Slack API Error: {error_message}",
        )
    else:
        return {"response": response.data}


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def list_conversations_metadata(
    context: ToolContext,
    conversation_types: Annotated[
        Optional[list[ConversationTypeUserFriendly]],
        "The type(s) of conversations to list. Defaults to all types.",
    ] = None,
    limit: Annotated[
        Optional[int], "The maximum number of conversations to list."
    ] = MAX_PAGINATION_LIMIT,
    next_cursor: Annotated[Optional[str], "The cursor to use for pagination."] = None,
) -> Annotated[
    dict,
    (
        "The conversations metadata list and a pagination 'next_cursor', if there are more "
        "conversations to retrieve."
    ),
]:
    """
    List metadata for Slack conversations (channels and/or direct messages) that the user
    is a member of.
    """
    if isinstance(conversation_types, ConversationType):
        conversation_types = [conversation_types]

    conversation_types_filter = ",".join(
        convert_user_friendly_conversation_type(conv_type).value
        for conv_type in conversation_types or ConversationTypeUserFriendly
    )

    slackClient = AsyncWebClient(token=context.authorization.token)

    results, next_cursor = await async_paginate(
        slackClient.conversations_list,
        "channels",
        limit=limit,
        next_cursor=next_cursor,
        types=conversation_types_filter,
        exclude_archived=True,
    )

    return {
        "conversations": [
            extract_conversation_metadata(conversation)
            for conversation in results
            if conversation.get("is_member")
        ],
        "next_cursor": next_cursor,
    }


@tool(
    requires_auth=Slack(
        scopes=["channels:read"],
    )
)
async def list_public_channels_metadata(
    context: ToolContext,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list."
    ] = MAX_PAGINATION_LIMIT,
) -> Annotated[dict, "The public channels"]:
    """List metadata for public channels in Slack that the user is a member of."""

    return await list_conversations_metadata(
        context,
        conversation_types=[ConversationTypeUserFriendly.PUBLIC_CHANNEL],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["groups:read"],
    )
)
async def list_private_channels_metadata(
    context: ToolContext,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list."
    ] = MAX_PAGINATION_LIMIT,
) -> Annotated[dict, "The private channels"]:
    """List metadata for private channels in Slack that the user is a member of."""

    return await list_conversations_metadata(
        context,
        conversation_types=[ConversationTypeUserFriendly.PRIVATE_CHANNEL],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["mpim:read"],
    )
)
async def list_group_direct_message_channels_metadata(
    context: ToolContext,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list."
    ] = MAX_PAGINATION_LIMIT,
) -> Annotated[dict, "The group direct message channels"]:
    """List metadata for group direct message channels in Slack that the user is a member of."""

    return await list_conversations_metadata(
        context,
        conversation_types=[ConversationTypeUserFriendly.MULTI_PERSON_DIRECT_MESSAGE],
        limit=limit,
    )


# Note: Bots are included in the results.
# Note: Direct messages with no conversation history are included in the results.
@tool(
    requires_auth=Slack(
        scopes=["im:read"],
    )
)
async def list_direct_message_channels_metadata(
    context: ToolContext,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list."
    ] = MAX_PAGINATION_LIMIT,
) -> Annotated[dict, "The direct message channels metadata"]:
    """List metadata for direct message channels in Slack that the user is a member of."""

    return await list_conversations_metadata(
        context,
        conversation_types=[ConversationTypeUserFriendly.DIRECT_MESSAGE],
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def get_conversation_metadata_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack."""
    slackClient = AsyncWebClient(token=context.authorization.token)

    try:
        response = await slackClient.conversations_info(
            channel=conversation_id,
            include_locale=True,
            include_num_members=True,
        )

        return extract_conversation_metadata(response["channel"])

    except SlackApiError as e:
        if e.response["error"] == "channel_not_found":
            conversations = await list_conversations_metadata(context, limit=-1)
            available_conversations = ", ".join(
                f"{conversation['id']} ({conversation['name']})"
                for conversation in conversations["conversations"]
            )

            raise RetryableToolError(
                "Conversation not found",
                developer_message=f"Conversation with ID '{conversation_id}' not found.",
                additional_prompt_content=f"Available conversations: {available_conversations}",
                retry_after_ms=500,
            )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def get_conversation_metadata_by_name(
    context: ToolContext,
    conversation_name: Annotated[str, "The name of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack."""
    next_cursor = None
    conversation_names = []

    while True:
        response = await list_conversations_metadata(context, next_cursor=next_cursor)
        next_cursor = response["next_cursor"]

        for conversation in response["conversations"]:
            if conversation["name"].lower() == conversation_name.lower():
                return conversation
            conversation_names.append(conversation["name"])

        if not next_cursor:
            break

    raise RetryableToolError(
        "Conversation not found",
        developer_message=f"Conversation with name '{conversation_name}' not found.",
        additional_prompt_content=f"Available conversation names: {conversation_names}",
        retry_after_ms=500,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def get_members_from_conversation_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get members for"],
    limit: Annotated[
        Optional[int], "The maximum number of members to return."
    ] = MAX_PAGINATION_LIMIT,
    next_cursor: Annotated[Optional[str], "The cursor to use for pagination."] = None,
) -> Annotated[dict, "Information about each member in the conversation"]:
    """Get the members of a conversation in Slack by the conversation's ID."""
    slackClient = AsyncWebClient(token=context.authorization.token)

    try:
        member_ids, next_cursor = await async_paginate(
            slackClient.conversations_members,
            "members",
            limit=limit,
            next_cursor=next_cursor,
            channel=conversation_id,
        )
    except SlackApiError as e:
        if e.response["error"] == "channel_not_found":
            conversations = await list_conversations_metadata(context)
            available_conversations = ", ".join(
                f"{conversation['id']} ({conversation['name']})"
                for conversation in conversations["conversations"]
            )

            raise RetryableToolError(
                "Conversation not found",
                developer_message=f"Conversation with ID '{conversation_id}' not found.",
                additional_prompt_content=f"Available conversations: {available_conversations}",
                retry_after_ms=500,
            )

    # Get the members' info
    # TODO: This will probably hit rate limits. We should probably call list_users() and
    # then filter the results instead.
    members = await asyncio.gather(*[
        get_user_info_by_id(context, member_id) for member_id in member_ids
    ])

    return {"members": members, "next_cursor": next_cursor}


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
async def get_members_from_conversation_by_name(
    context: ToolContext,
    conversation_name: Annotated[str, "The name of the conversation to get members for"],
    limit: Annotated[
        Optional[int], "The maximum number of members to return."
    ] = MAX_PAGINATION_LIMIT,
    next_cursor: Annotated[Optional[str], "The cursor to use for pagination."] = None,
) -> Annotated[dict, "The conversation members' IDs and Names"]:
    """Get the members of a conversation in Slack by the conversation's name."""
    conversation_names = []
    conversation_next_cursor = None

    while True:
        response = await list_conversations_metadata(context, next_cursor=conversation_next_cursor)

        conversation_next_cursor = response["next_cursor"]

        for conversation in response["conversations"]:
            conversation_names.append(conversation["name"])
            if conversation["name"].lower() == conversation_name.lower():
                conversation_id = conversation["id"]
                break

        if not conversation_next_cursor:
            break

    if not conversation_id:
        raise RetryableToolError(
            "Conversation not found",
            developer_message=f"Conversation with name '{conversation_name}' not found.",
            additional_prompt_content=f"Available conversation names: {conversation_names}",
            retry_after_ms=500,
        )

    return await get_members_from_conversation_by_id(
        context=context,
        conversation_id=conversation_id,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:history", "groups:history", "im:history", "mpim:history"],
    )
)
async def get_conversation_history_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get history for"],
    oldest_relative: Annotated[
        Optional[str],
        (
            "The oldest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    latest_relative: Annotated[
        Optional[str],
        (
            "The latest message to include in the results, specified as a time offset from the "
            "current time in the format 'DD:HH:MM'"
        ),
    ] = None,
    oldest_datetime: Annotated[
        Optional[str],
        (
            "The oldest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    latest_datetime: Annotated[
        Optional[str],
        (
            "The latest message to include in the results, specified as a datetime object in the "
            "format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ] = None,
    limit: Annotated[
        Optional[int], "The maximum number of messages to return. Defaults to 20."
    ] = 20,
    cursor: Annotated[Optional[str], "The cursor to use for pagination. Defaults to None."] = None,
) -> Annotated[
    dict,
    (
        "The conversation history and next cursor for paginating results (when there are "
        "additional messages to retrieve)."
    ),
]:
    """Get the history of a conversation in Slack."""
    # This is super ugly I know, I'm sorry, we are soon implementing a better solution
    # for date-range filtering that will be standardized across all tools.
    error_message = None
    if oldest_datetime and oldest_relative:
        error_message = "Cannot specify both 'oldest_datetime' and 'oldest_relative'."

    if latest_datetime and latest_relative:
        error_message = "Cannot specify both 'latest_datetime' and 'latest_relative'."

    if error_message:
        raise ToolExecutionError(error_message, developer_message=error_message)

    current_unix_timestamp = int(time.time())

    if latest_relative:
        days, hours, minutes = map(int, latest_relative.split(":"))
        latest_seconds = days * 86400 + hours * 3600 + minutes * 60
        latest_unix_timestamp = current_unix_timestamp - latest_seconds
    elif latest_datetime:
        latest_unix_timestamp = int(
            datetime.datetime.strptime(latest_datetime, "%Y-%m-%d %H:%M:%S").timestamp()
        )
    else:
        latest_unix_timestamp = current_unix_timestamp  # This is the default on Slack API

    if oldest_relative:
        days, hours, minutes = map(int, oldest_relative.split(":"))
        oldest_seconds = days * 86400 + hours * 3600 + minutes * 60
        oldest_unix_timestamp = current_unix_timestamp - oldest_seconds
    elif oldest_datetime:
        oldest_unix_timestamp = int(
            datetime.datetime.strptime(oldest_datetime, "%Y-%m-%d %H:%M:%S").timestamp()
        )
    else:
        oldest_unix_timestamp = 0  # This is the default on Slack API

    slackClient = AsyncWebClient(token=context.authorization.token)
    response = await slackClient.conversations_history(
        channel=conversation_id,
        limit=limit,
        include_all_metadata=True,
        oldest=oldest_unix_timestamp,
        latest=latest_unix_timestamp,
        cursor=cursor,
    )
    messages = response.get("messages", [])
    next_cursor = response.get("response_metadata", {}).get("next_cursor")
    return {"messages": messages, "next_cursor": next_cursor}
