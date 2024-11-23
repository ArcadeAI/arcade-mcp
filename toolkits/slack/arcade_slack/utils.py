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


def format_channel_metadata(channel: dict) -> dict:
    return {
        "id": channel.get("id"),
        "name": channel.get("name"),
        "conversation_type": get_conversation_type(channel),
        "is_private": channel.get("is_private"),
        "is_archived": channel.get("is_archived"),
        "is_member": channel.get("is_member"),
        "purpose": channel.get("purpose", {}).get("value"),
    }
