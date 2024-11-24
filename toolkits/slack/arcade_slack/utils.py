from arcade_slack.models import ConversationType


def format_users(userListResponse: dict) -> str:
    csv_string = "All active Slack users:\n\nname,real_name\n"
    for user in userListResponse["members"]:
        if not user.get("deleted", False):
            name = user.get("name", "")
            real_name = user.get("profile", {}).get("real_name", "")
            csv_string += f"{name},{real_name}\n"
    return csv_string.strip()


def format_channels(channels_response: dict) -> str:
    csv_string = "All active Slack channels:\n\nname\n"
    for channel in channels_response["channels"]:
        if not channel.get("is_archived", False):
            name = channel.get("name", "")
            csv_string += f"{name}\n"
    return csv_string.strip()


def remove_none_values(params: dict) -> dict:
    """
    Remove key/value pairs from a dictionary where the value is None.
    """
    return {k: v for k, v in params.items() if v is not None}


def get_conversation_type(channel: dict) -> ConversationType:
    """
    Get the type of conversation from a Slack channel's metadata.
    """
    return (
        ConversationType.PUBLIC_CHANNEL.value
        if channel.get("is_channel")
        else ConversationType.PRIVATE_CHANNEL.value
        if channel.get("is_group")
        else ConversationType.IM.value
        if channel.get("is_im")
        else ConversationType.MPIM.value
        if channel.get("is_mpim")
        else None
    )


def extract_basic_channel_metadata(channel: dict) -> dict:
    return {
        "id": channel.get("id"),
        "name": channel.get("name"),
        "conversation_type": get_conversation_type(channel),
        "is_private": channel.get("is_private"),
        "is_archived": channel.get("is_archived"),
        "is_member": channel.get("is_member"),
        "num_members": channel.get("num_members"),
        "purpose": channel.get("purpose", {}).get("value"),
    }


def extract_basic_user_info(user_info: dict) -> dict:
    """Extract a user's basic info from a Slack user object.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return {
        "id": user_info.get("id"),
        "name": user_info.get("name"),
        "is_bot": user_info.get("is_bot"),
        "email": user_info.get("profile", {}).get("email"),
        "display_name": user_info.get("profile", {}).get("display_name"),
        "real_name": user_info.get("real_name"),
        "timezone": user_info.get("tz"),
    }


def is_user_a_bot(user: dict) -> bool:
    """Check if a Slack user object represents a bot.

    Bots are users with the "is_bot" flag set to true.
    USLACKBOT is the user object for the Slack bot itself and is a special case.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return user.get("is_bot") or user.get("id") == "USLACKBOT"


def is_user_deleted(user: dict) -> bool:
    """Check if a Slack user object represents a deleted user.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return user.get("deleted", False)
