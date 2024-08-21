from typing import Annotated
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

    client = WebClient(token=context.authorization.token)

    try:
        # Step 1: Retrieve the user's Slack ID based on their username
        response = client.users_list()
        user_id = None
        for user in response["members"]:
            if user["name"].lower() == user_name.lower():
                user_id = user["id"]
                break

        if not user_id:
            raise ValueError(f"User with username '{user_name}' not found.")

        # Step 2: Retrieve the DM channel ID with the user
        im_response = client.conversations_open(users=[user_id])
        dm_channel_id = im_response["channel"]["id"]

        # Step 3: Send the message as if it's from you (because we're using a user token)
        client.chat_postMessage(channel=dm_channel_id, text=message)

    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
