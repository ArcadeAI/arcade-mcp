import asyncio
from datetime import datetime, timezone
from typing import Annotated, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.exceptions import (
    ItemNotFoundError,
    UsernameNotFoundError,
)
from arcade_slack.models import (
    ConversationType,
    SlackUserList,
)
from arcade_slack.tools.users import get_user_info_by_id, list_users
from arcade_slack.utils import (
    async_paginate,
    convert_conversation_type_to_slack_name,
    convert_datetime_to_unix_timestamp,
    convert_relative_datetime_to_unix_timestamp,
    enrich_message_datetime,
    extract_conversation_metadata,
    format_users,
    get_user_by_username,
    retrieve_conversations_by_user_ids,
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

    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

    try:
        # Step 1: Retrieve the user's Slack ID based on their username
        user_list_response = await slackClient.users_list()
        user_id = None
        for user in user_list_response["members"]:
            response_user_name = (
                "" if not isinstance(user.get("name"), str) else user["name"].lower()
            )
            if response_user_name == user_name.lower():
                user_id = user["id"]
                break

        if not user_id:
            raise RetryableToolError(
                "User not found",
                developer_message=f"User with username '{user_name}' not found.",
                additional_prompt_content=format_users(cast(SlackUserList, user_list_response)),
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

        channel = await get_channel_metadata_by_name(context=context, channel_name=channel_name)
        channel_id = channel["id"]

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
    """Get the members of a conversation in Slack by the conversation's ID."""
    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

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

    return {
        "members": [member for member in members if not member.get("is_bot")],
        "next_cursor": next_cursor,
    }


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
    """Get the members of a conversation in Slack by the conversation's name."""
    channel = await get_channel_metadata_by_name(context=context, channel_name=channel_name)

    return await get_members_in_conversation_by_id(  # type: ignore[no-any-return]
        context=context,
        conversation_id=channel["id"],
        limit=limit,
        next_cursor=next_cursor,
    )


# TODO: make the function accept a current unix timestamp argument to allow testing without
# mocking. Have to wait until arcade.core.annotations.Inferrable is implemented, so that we
# can avoid exposing this arg to the LLM.
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
    error_message = None
    if oldest_datetime and oldest_relative:
        error_message = "Cannot specify both 'oldest_datetime' and 'oldest_relative'."

    if latest_datetime and latest_relative:
        error_message = "Cannot specify both 'latest_datetime' and 'latest_relative'."

    if error_message:
        raise ToolExecutionError(error_message, developer_message=error_message)

    current_unix_timestamp = int(datetime.now(timezone.utc).timestamp())

    if latest_relative:
        latest_timestamp = convert_relative_datetime_to_unix_timestamp(
            latest_relative, current_unix_timestamp
        )
    elif latest_datetime:
        latest_timestamp = convert_datetime_to_unix_timestamp(latest_datetime)
    else:
        latest_timestamp = None

    if oldest_relative:
        oldest_timestamp = convert_relative_datetime_to_unix_timestamp(
            oldest_relative, current_unix_timestamp
        )
    elif oldest_datetime:
        oldest_timestamp = convert_datetime_to_unix_timestamp(oldest_datetime)
    else:
        oldest_timestamp = None

    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

    datetime_args = {}
    if oldest_timestamp:
        datetime_args["oldest"] = oldest_timestamp
    if latest_timestamp:
        datetime_args["latest"] = latest_timestamp

    response, next_cursor = await async_paginate(
        slackClient.conversations_history,
        "messages",
        limit=limit,
        next_cursor=next_cursor,
        channel=conversation_id,
        include_all_metadata=True,
        inclusive=True,  # Include messages at the start and end of the time range
        **datetime_args,
    )

    messages = [enrich_message_datetime(message) for message in response]

    return {"messages": messages, "next_cursor": next_cursor}


# TODO: make the function accept a current unix timestamp argument to allow testing without
# mocking. Have to wait until arcade.core.annotations.Inferrable is implemented, so that we
# can avoid exposing this arg to the LLM.
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
    channel = await get_channel_metadata_by_name(context=context, channel_name=channel_name)

    return await get_messages_in_conversation_by_id(  # type: ignore[no-any-return]
        context=context,
        conversation_id=channel["id"],
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(requires_auth=Slack(scopes=["im:history", "im:read"]))
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
    direct_conversation = await get_direct_message_conversation_metadata_by_username(
        context=context, username=username
    )

    return await get_messages_in_conversation_by_id(  # type: ignore[no-any-return]
        context=context,
        conversation_id=direct_conversation["id"],
        oldest_relative=oldest_relative,
        latest_relative=latest_relative,
        oldest_datetime=oldest_datetime,
        latest_datetime=latest_datetime,
        limit=limit,
        next_cursor=next_cursor,
    )


@tool(requires_auth=Slack(scopes=["im:history", "im:read"]))
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
    direct_conversation = await get_multi_person_dm_conversation_metadata_by_usernames(
        context=context, usernames=usernames
    )

    return await get_messages_in_conversation_by_id(  # type: ignore[no-any-return]
        context=context,
        conversation_id=direct_conversation["id"],
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
async def get_conversation_metadata_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack searching by its ID.

    This tool does not return the messages in a conversation. To get the messages, use the
    `get_messages_in_conversation_by_id` tool."""
    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

    try:
        response = await slackClient.conversations_info(
            channel=conversation_id,
            include_locale=True,
            include_num_members=True,
        )

    except SlackApiError as e:
        if e.response.get("error") == "channel_not_found":
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

        raise

    return dict(**extract_conversation_metadata(response["channel"]))


@tool(requires_auth=Slack(scopes=["channels:read", "groups:read"]))
async def get_channel_metadata_by_name(
    context: ToolContext,
    channel_name: Annotated[str, "The name of the channel to get metadata for"],
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[dict, "The channel metadata"]:
    """Get the metadata of a channel in Slack searching by its name.

    This tool does not return the messages in a channel. To get the messages, use the
    `get_messages_in_channel_by_name` tool."""
    channel_names: list[str] = []

    async def find_channel() -> dict:
        nonlocal channel_names, channel_name, next_cursor
        should_continue = True

        while should_continue:
            response = await list_conversations_metadata(
                context=context,
                conversation_types=[
                    ConversationType.PUBLIC_CHANNEL,
                    ConversationType.PRIVATE_CHANNEL,
                ],
                next_cursor=next_cursor,
            )
            next_cursor = response.get("next_cursor")

            for channel in response["conversations"]:
                response_channel_name = (
                    "" if not isinstance(channel.get("name"), str) else channel["name"].lower()
                )
                if response_channel_name == channel_name.lower():
                    return channel  # type: ignore[no-any-return]
                channel_names.append(channel["name"])

            if not next_cursor:
                should_continue = False

        raise ItemNotFoundError()

    try:
        return await asyncio.wait_for(find_channel(), timeout=MAX_PAGINATION_TIMEOUT_SECONDS)
    except ItemNotFoundError:
        raise RetryableToolError(
            "Channel not found",
            developer_message=f"Channel with name '{channel_name}' not found.",
            additional_prompt_content=f"Available channel names: {channel_names}",
            retry_after_ms=500,
        )
    except TimeoutError:
        raise RetryableToolError(
            "Channel not found, search timed out.",
            developer_message=(
                f"Channel with name '{channel_name}' not found. "
                f"Search timed out after {MAX_PAGINATION_TIMEOUT_SECONDS} seconds."
            ),
            additional_prompt_content=(
                f"Other channel names found are: {channel_names}. "
                "The list is potentially non-exhaustive, since the search process timed out. "
                f"Use the '{list_conversations_metadata.__tool_name__}' tool to get"
                "a comprehensive list of channels."
            ),
            retry_after_ms=500,
        )


@tool(requires_auth=Slack(scopes=["im:read"]))
async def get_direct_message_conversation_metadata_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the user/person to get messages with"],
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[
    dict | None,
    "The direct message conversation metadata.",
]:
    """Get the metadata of a direct message conversation in Slack by the username.

    This tool does not return the messages in a conversation. To get the messages, use the
    `get_messages_in_direct_message_conversation_by_username` tool."""
    try:
        token = (
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        )
        slack_client = AsyncWebClient(token=token)

        current_user, list_users_response = await asyncio.gather(
            slack_client.auth_test(), list_users(context)
        )

        other_user = get_user_by_username(username, list_users_response["users"])

        conversations_found = await retrieve_conversations_by_user_ids(
            list_conversations_func=list_conversations_metadata,
            get_members_in_conversation_func=get_members_in_conversation_by_id,
            context=context,
            conversation_types=[ConversationType.DIRECT_MESSAGE],
            user_ids=[current_user["user_id"], other_user["id"]],
            exact_match=True,
            limit=1,
            next_cursor=next_cursor,
        )

        return None if not conversations_found else conversations_found[0]

    except UsernameNotFoundError as e:
        raise RetryableToolError(
            f"Username '{e.username_not_found}' not found",
            developer_message=f"User with username '{e.username_not_found}' not found.",
            additional_prompt_content=f"Available users: {e.usernames_found}",
            retry_after_ms=500,
        )


@tool(requires_auth=Slack(scopes=["im:read"]))
async def get_multi_person_dm_conversation_metadata_by_usernames(
    context: ToolContext,
    usernames: Annotated[list[str], "The usernames of the users/people to get messages with"],
    next_cursor: Annotated[
        str | None,
        "The cursor to use for pagination, if continuing from a previous search.",
    ] = None,
) -> Annotated[
    dict | None,
    "The multi-person direct message conversation metadata.",
]:
    """Get the metadata of a multi-person direct message conversation in Slack by the usernames.

    This tool does not return the messages in a conversation. To get the messages, use the
    `get_messages_in_multi_person_dm_conversation_by_usernames` tool.
    """
    try:
        token = (
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        )
        slack_client = AsyncWebClient(token=token)

        current_user, list_users_response = await asyncio.gather(
            slack_client.auth_test(), list_users(context)
        )

        other_users = [
            get_user_by_username(username, list_users_response["users"]) for username in usernames
        ]

        conversations_found = await retrieve_conversations_by_user_ids(
            list_conversations_func=list_conversations_metadata,
            get_members_in_conversation_func=get_members_in_conversation_by_id,
            context=context,
            conversation_types=[ConversationType.MULTI_PERSON_DIRECT_MESSAGE],
            user_ids=[
                current_user["user_id"],
                *[user["id"] for user in other_users if user["id"] != current_user["user_id"]],
            ],
            exact_match=True,
            limit=1,
            next_cursor=next_cursor,
        )

        if not conversations_found:
            raise RetryableToolError(
                "Conversation not found with the usernames provided",
                developer_message="Conversation not found with the usernames provided",
                retry_after_ms=500,
            )

        return conversations_found[0]

    except UsernameNotFoundError as e:
        raise RetryableToolError(
            f"Username '{e.username_not_found}' not found",
            developer_message=f"User with username '{e.username_not_found}' not found.",
            additional_prompt_content=f"Available users: {e.usernames_found}",
            retry_after_ms=500,
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
        "The type(s) of conversations to list. Defaults to all types.",
    ] = None,
    limit: Annotated[int | None, "The maximum number of conversations to list."] = None,
    next_cursor: Annotated[str | None, "The cursor to use for pagination."] = None,
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
        convert_conversation_type_to_slack_name(conv_type).value
        for conv_type in conversation_types or ConversationType
    )

    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

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
            dict(**extract_conversation_metadata(conversation))
            for conversation in results
            if conversation.get("is_im") or conversation.get("is_member")
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
    limit: Annotated[int | None, "The maximum number of channels to list."] = None,
) -> Annotated[dict, "The public channels"]:
    """List metadata for public channels in Slack that the user is a member of."""

    return await list_conversations_metadata(  # type: ignore[no-any-return]
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
    """List metadata for private channels in Slack that the user is a member of."""

    return await list_conversations_metadata(  # type: ignore[no-any-return]
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
    """List metadata for group direct message conversations that the user is a member of."""

    return await list_conversations_metadata(  # type: ignore[no-any-return]
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
    """List metadata for direct message conversations in Slack that the user is a member of."""

    response = await list_conversations_metadata(
        context,
        conversation_types=[ConversationType.DIRECT_MESSAGE],
        limit=limit,
    )

    return response  # type: ignore[no-any-return]
