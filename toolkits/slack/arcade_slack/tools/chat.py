from typing import Annotated, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack
from arcade.sdk.errors import RetryableToolError, ToolExecutionError
from arcade_slack.models import ConversationType
from arcade_slack.utils import (
    format_channel_metadata,
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
def list_conversations(
    context: ToolContext,
    conversation_types: Annotated[
        Optional[list[ConversationType]], "The type of conversations to list"
    ] = None,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to 100."
    ] = 100,
) -> Annotated[dict, "The conversations"]:
    """List Slack conversations that the user has access to given the provided filters."""

    if conversation_types is None:
        types = ",".join(conv_type.value for conv_type in ConversationType)
    else:
        types = ",".join(conv_type.value for conv_type in conversation_types)

    next_page_token = None
    conversations = []

    slackClient = WebClient(token=context.authorization.token)

    while len(conversations) < limit:
        iteration_limit = min(limit - len(conversations), 1000)
        response = slackClient.conversations_list(
            types=types,
            exclude_archived=exclude_archived,
            limit=iteration_limit,
            next_page_token=next_page_token,
        )

        channels = [format_channel_metadata(channel) for channel in response.get("channels", [])]
        conversations.extend(channels)
        next_page_token = response.get("next_page_token")

        if not next_page_token:
            break

    return {"conversations": conversations, "num_conversations": len(conversations)}


@tool(
    requires_auth=Slack(
        scopes=["channels:read"],
    )
)
def list_public_channels(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to 100."
    ] = 100,
) -> Annotated[dict, "The public channels"]:
    """List all channels in Slack."""

    return list_conversations(
        context,
        conversation_types=[ConversationType.PUBLIC_CHANNEL],
        exclude_archived=exclude_archived,
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["groups:read"],
    )
)
def list_private_channels(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to 100."
    ] = 100,
) -> Annotated[dict, "The private channels"]:
    """List all private channels in Slack."""

    return list_conversations(
        context,
        conversation_types=[ConversationType.PRIVATE_CHANNEL],
        exclude_archived=exclude_archived,
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["mpim:read"],
    )
)
def list_group_direct_message_channels(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to 100."
    ] = 100,
) -> Annotated[dict, "The group direct message channels"]:
    """List all group direct message channels in Slack."""

    return list_conversations(
        context,
        conversation_types=[ConversationType.MPIM],
        exclude_archived=exclude_archived,
        limit=limit,
    )


@tool(
    requires_auth=Slack(
        scopes=["im:read"],
    )
)
def list_direct_message_channels(
    context: ToolContext,
    exclude_archived: Annotated[Optional[bool], "Whether to exclude archived conversations"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of channels to list. Defaults to 100."
    ] = 100,
) -> Annotated[dict, "The direct message channels"]:
    """List all direct message channels in Slack."""

    return list_conversations(
        context,
        conversation_types=[ConversationType.IM],
        exclude_archived=exclude_archived,
        limit=limit,
    )
