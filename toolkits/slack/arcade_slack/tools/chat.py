import time
from typing import Annotated
from arcade.core.errors import ToolExecutionError, RetryableToolError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import SlackUser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


@tool(
    requires_auth=SlackUser(
        scope=["chat:write", "im:write", "users.profile:read", "users:read"],
    )
)
def send_dm_to_user(
    context: ToolContext,
    user_name: Annotated[str, "The Slack username of the person you want to message"],
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
            # does this end up as a developerMessage?
            # does it end up in the LLM context?
            # provide the dev an Error type that controls what ends up in the LLM context

            # TODO make the sleep configurable and sent to the engine
            time.sleep(0.5)  # Wait for half a second
            raise RetryableToolError(
                "User not found",
                developer_message=f"User with username '{user_name}' not found.",
                additional_prompt_content=format_users(userListResponse),
            )

        # Step 2: Retrieve the DM channel ID with the user
        im_response = slackClient.conversations_open(users=[user_id])
        dm_channel_id = im_response["channel"]["id"]

        # Step 3: Send the message as if it's from you (because we're using a user token)
        slackClient.chat_postMessage(channel=dm_channel_id, text=message)

    except SlackApiError as e:
        raise ToolExecutionError(
            f"Error sending message: {e.response['error']}",
            developer_message="Error sending message",
        )


def format_users(userListResponse: dict) -> str:
    csv_string = "All active Slack users:\n\nid,name,real_name\n"
    for user in userListResponse["members"]:
        if not user.get("deleted", False):
            user_id = user.get("id", "")
            name = user.get("name", "")
            real_name = user.get("profile", {}).get("real_name", "")
            csv_string += f"{user_id},{name},{real_name}\n"
    return csv_string.strip()


@tool(
    requires_auth=SlackUser(
        scope=["chat:write", "channels:read", "groups:read"],
    )
)
def send_message_to_channel(
    context: ToolContext,
    channel_name: Annotated[
        str, "The Slack channel name where you want to send the message"
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
            time.sleep(0.5)  # Wait for half a second
            raise RetryableToolError(
                "Channel not found",
                developer_message=f"Channel with name '{channel_name}' not found.",
                additional_prompt_content=format_channels(channels_response),
            )

        # Step 2: Send the message to the channel
        slackClient.chat_postMessage(channel=channel_id, text=message)

    except SlackApiError as e:
        raise ToolExecutionError(
            f"Error sending message: {e.response['error']}",
            developer_message="Error sending message",
        )


def format_channels(channels_response: dict) -> str:
    csv_string = "All active Slack channels:\n\nid,name\n"
    for channel in channels_response["channels"]:
        if not channel.get("is_archived", False):
            channel_id = channel.get("id", "")
            name = channel.get("name", "")
            csv_string += f"{channel_id},{name}\n"
    return csv_string.strip()
