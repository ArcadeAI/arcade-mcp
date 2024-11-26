import time
from typing import Annotated, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack
from arcade.sdk.errors import RetryableToolError, ToolExecutionError
from arcade_slack.models import ConversationType
from arcade_slack.tools.users import get_user_info_by_id
from arcade_slack.utils import (
    extract_basic_channel_metadata,
    filter_conversations,
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
def send_dm_to_user(
    context: ToolContext,
    user_name: Annotated[
        str,
        "The Slack username of the person you want to message. Slack usernames are ALWAYS lowercase.",
    ],
    message: Annotated[str, "The message you want to send"],
):
    """Send a direct message to a user in Slack."""

    slackClient = WebClient(token=context.authorization.token)

    try:
        # Step 1: Retrieve the user's Slack ID based on their username
        userListResponse = slackClient.users_list()
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
        im_response = slackClient.conversations_open(users=[user_id])
        dm_channel_id = im_response["channel"]["id"]

        # Step 3: Send the message as if it's from you (because we're using a user token)
        slackClient.chat_postMessage(channel=dm_channel_id, text=message)

    except SlackApiError as e:
        error_message = e.response["error"] if "error" in e.response else str(e)
        raise ToolExecutionError(
            "Error sending message",
            developer_message=f"Slack API Error: {error_message}",
        )


@tool(
    requires_auth=Slack(
        scopes=[
            "chat:write",
            "channels:read",
            "groups:read",
        ],
    )
)
def send_message_to_channel(
    context: ToolContext,
    channel_name: Annotated[
        str,
        "The Slack channel name where you want to send the message. Slack channel names are ALWAYS lowercase.",
    ],
    message: Annotated[str, "The message you want to send"],
):
    """Send a message to a channel in Slack."""

    slackClient = WebClient(token=context.authorization.token)

    try:
        # Step 1: Retrieve the list of channels
        channels_response = slackClient.conversations_list()
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
        slackClient.chat_postMessage(channel=channel_id, text=message)

    except SlackApiError as e:
        error_message = e.response["error"] if "error" in e.response else str(e)
        raise ToolExecutionError(
            "Error sending message",
            developer_message=f"Slack API Error: {error_message}",
        )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
def list_conversations_metadata(
    context: ToolContext,
    conversation_types: Annotated[
        Optional[list[ConversationType]], "The type of conversations to list"
    ] = None,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to -1 (no limit)."
    ] = -1,
) -> Annotated[dict, "The conversations metadata"]:
    """List metadata for Slack conversations that the user is a member of given the provided filters."""

    if conversation_types is None:
        types = ",".join(conv_type.value for conv_type in ConversationType)
    else:
        types = ",".join(conv_type.value for conv_type in conversation_types)

    next_page_token = None
    conversations = []

    slackClient = WebClient(token=context.authorization.token)

    while limit == -1 or len(conversations) < limit:
        iteration_limit = (
            200 if limit == -1 else min(limit - len(conversations), 200)
        )  # Slack recommends max 200 results at a time
        response = slackClient.conversations_list(
            types=types,
            exclude_archived=exclude_archived,
            limit=iteration_limit,
            next_page_token=next_page_token,
        )

        channels = [
            extract_basic_channel_metadata(channel) for channel in response.get("channels", [])
        ]
        conversations.extend(channels)
        next_page_token = response.get("next_page_token")

        if not next_page_token:
            break

    conversations = filter_conversations(conversations)

    return {"conversations": conversations}


@tool(
    requires_auth=Slack(
        scopes=["channels:read"],
    )
)
def list_public_channels_metadata(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to -1 (no limit)."
    ] = -1,
) -> Annotated[dict, "The public channels"]:
    """List metadata for public channels in Slack that the user is a member of."""

    return list_conversations_metadata(
        context,
        conversation_types=[ConversationType.PUBLIC_CHANNEL],
        exclude_archived=exclude_archived,
        limit=limit,
    )


# TODO: Exclude archived by default
@tool(
    requires_auth=Slack(
        scopes=["groups:read"],
    )
)
def list_private_channels_metadata(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to -1 (no limit)."
    ] = -1,
) -> Annotated[dict, "The private channels"]:
    """List metadata for private channels in Slack that the user is a member of."""

    return list_conversations_metadata(
        context,
        conversation_types=[ConversationType.PRIVATE_CHANNEL],
        exclude_archived=exclude_archived,
        limit=limit,
    )


# TODO: Exclude archived by default
@tool(
    requires_auth=Slack(
        scopes=["mpim:read"],
    )
)
def list_group_direct_message_channels_metadata(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to -1 (no limit)."
    ] = -1,
) -> Annotated[dict, "The group direct message channels"]:
    """List metadata for group direct message channels in Slack that the user is a member of."""

    return list_conversations_metadata(
        context,
        conversation_types=[ConversationType.MPIM],
        exclude_archived=exclude_archived,
        limit=limit,
    )


# Note: Bots are included in the results.
# Note: Direct messages with no conversation history are included in the results.
@tool(
    requires_auth=Slack(
        scopes=["im:read"],
    )
)
def list_direct_message_channels_metadata(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to -1 (no limit)."
    ] = -1,
) -> Annotated[dict, "The direct message channels metadata"]:
    """List metadata for direct message channels in Slack that the user is a member of."""

    return list_conversations_metadata(
        context,
        conversation_types=[ConversationType.IM],
        exclude_archived=exclude_archived,
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
def get_conversation_metadata_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack."""

    slackClient = WebClient(token=context.authorization.token)
    try:
        response = slackClient.conversations_info(channel=conversation_id, include_num_members=True)
        return extract_basic_channel_metadata(response["channel"])

    except SlackApiError as e:
        if e.response["error"] == "channel_not_found":
            conversations = list_conversations_metadata(context, limit=-1)
            conversation_ids = ", ".join(
                conversation["id"] for conversation in conversations["conversations"]
            )

            raise RetryableToolError(
                "Conversation not found",
                developer_message=f"Conversation with ID '{conversation_id}' not found.",
                additional_prompt_content=f"Available conversation IDs: {conversation_ids}",
                retry_after_ms=500,
            )
        raise


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
def get_conversation_metadata_by_name(
    context: ToolContext,
    conversation_name: Annotated[str, "The name of the conversation to get metadata for"],
) -> Annotated[dict, "The conversation metadata"]:
    """Get the metadata of a conversation in Slack."""
    conversations = list_conversations_metadata(context, limit=-1)

    for conversation in conversations["conversations"]:
        # Check if the conversation has a 'name' attribute and it's not None
        if conversation.get("name") and conversation["name"].lower() == conversation_name.lower():
            return conversation

    conversation_names = ", ".join(
        conversation["name"]
        for conversation in conversations["conversations"]
        if conversation.get("name")
    )

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
def get_members_from_conversation_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get members for"],
    limit: Annotated[
        Optional[int], "The maximum number of members to return. Defaults to -1 (no limit)"
    ] = -1,
) -> Annotated[dict, "Information about each member in the conversation"]:
    """Get information about the members in a conversation in Slack."""

    slackClient = WebClient(token=context.authorization.token)
    member_ids = []
    next_page_token = None

    # Get the member ids
    while limit == -1 or len(member_ids) < limit:
        iteration_limit = (
            200 if limit == -1 else min(limit - len(member_ids), 200)
        )  # Slack recommends max 200 results at a time
        response = slackClient.conversations_members(
            channel=conversation_id, cursor=next_page_token, limit=iteration_limit
        )
        member_ids.extend(response["members"])
        next_page_token = response.get("response_metadata", {}).get("next_cursor")

        if not next_page_token:
            break

    # Get the members' info
    # TODO: This will probably hit rate limits. We should probably call list_users() and then filter the results instead.
    members = [get_user_info_by_id(context, member_id) for member_id in member_ids]

    return {"members": members}


@tool(
    requires_auth=Slack(
        scopes=["channels:read", "groups:read", "im:read", "mpim:read"],
    )
)
def get_members_from_conversation_name(
    context: ToolContext,
    conversation_name: Annotated[str, "The name of the conversation to get members for"],
    limit: Annotated[
        Optional[int], "The maximum number of members to return. Defaults to -1 (no limit)"
    ] = -1,
) -> Annotated[dict, "The conversation members' IDs and Names"]:
    """Get the members of a conversation in Slack by the conversation's name."""

    conversations = list_conversations_metadata(context, limit=-1)

    conversation_id = None
    for conversation in conversations["conversations"]:
        if conversation.get("name") and conversation["name"].lower() == conversation_name.lower():
            conversation_id = conversation["id"]
            break

    if not conversation_id:
        conversation_names = ", ".join(
            conversation["name"]
            for conversation in conversations["conversations"]
            if conversation.get("name")
        )
        raise RetryableToolError(
            "Conversation not found",
            developer_message=f"Conversation with name '{conversation_name}' not found.",
            additional_prompt_content=f"Available conversation names: {conversation_names}",
            retry_after_ms=500,
        )

    # Use the existing function to get members by conversation ID
    return get_members_from_conversation_id(context, conversation_id, limit)


# TODO: Add pagination
# TODO: Add support for unix timestamps
@tool(
    requires_auth=Slack(
        scopes=["channels:history", "groups:history", "im:history", "mpim:history"],
    )
)
def get_conversation_history_by_id(
    context: ToolContext,
    conversation_id: Annotated[str, "The ID of the conversation to get history for"],
    oldest_relative: Annotated[
        Optional[str],
        "The oldest message to include in the results, specified as a time offset from the current time in the format 'DD:HH:MM'",
    ] = "00:00:00",
    latest_relative: Annotated[
        Optional[str],
        "The latest message to include in the results, specified as a time offset from the current time in the format 'DD:HH:MM'",
    ] = "00:00:00",
    limit: Annotated[
        Optional[int], "The maximum number of messages to return. Defaults to 20."
    ] = 20,
) -> Annotated[dict, "The conversation history"]:
    """Get the history of a conversation in Slack."""
    days, hours, minutes = map(int, latest_relative.split(":"))
    latest_seconds = days * 86400 + hours * 3600 + minutes * 60
    current_unix_timestamp = int(time.time())
    latest_unix_timestamp = current_unix_timestamp - latest_seconds

    days, hours, minutes = map(int, oldest_relative.split(":"))
    oldest_seconds = days * 86400 + hours * 3600 + minutes * 60
    oldest_unix_timestamp = current_unix_timestamp - oldest_seconds

    slackClient = WebClient(token=context.authorization.token)
    response = slackClient.conversations_history(
        channel=conversation_id,
        limit=limit,
        include_all_metadata=True,
        oldest=oldest_unix_timestamp,
        latest=latest_unix_timestamp,
    )
    messages = response.get("messages", [])
    return {"messages": messages}
