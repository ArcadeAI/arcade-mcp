from datetime import datetime, timezone
from typing import Callable, Optional

from arcade.sdk.errors import RetryableToolError

from arcade_slack.constants import MAX_PAGINATION_LIMIT
from arcade_slack.models import ConversationType, ConversationTypeSlackName


def format_users(userListResponse: dict) -> str:
    """Format a list of Slack users into a CSV string.

    Args:
        userListResponse: The response from the Slack API's users_list method.

    Returns:
        A CSV string with the users' names and real names.
    """
    csv_string = "All active Slack users:\n\nname,real_name\n"
    for user in userListResponse["members"]:
        if not user.get("deleted", False):
            name = user.get("name", "")
            real_name = user.get("profile", {}).get("real_name", "")
            csv_string += f"{name},{real_name}\n"
    return csv_string.strip()


def format_channels(channels_response: dict) -> str:
    """Format a list of Slack channels into a CSV string.

    Args:
        channels_response: The response from the Slack API's conversations_list method.

    Returns:
        A CSV string with the channels' names.
    """
    csv_string = "All active Slack channels:\n\nname\n"
    for channel in channels_response["channels"]:
        if not channel.get("is_archived", False):
            name = channel.get("name", "")
            csv_string += f"{name}\n"
    return csv_string.strip()


def remove_none_values(params: dict) -> dict:
    """Remove key/value pairs from a dictionary where the value is None.

    Args:
        params: The dictionary to remove None values from.

    Returns:
        A dictionary with None values removed.
    """
    return {k: v for k, v in params.items() if v is not None}


def get_conversation_type(channel: dict) -> ConversationTypeSlackName:
    """Get the type of conversation from a Slack channel's metadata.

    Args:
        channel: The Slack channel's metadata dictionary.

    Returns:
        The type of conversation.
    """
    return (
        ConversationTypeSlackName.PUBLIC_CHANNEL.value
        if channel.get("is_channel")
        else ConversationTypeSlackName.PRIVATE_CHANNEL.value
        if channel.get("is_group")
        else ConversationTypeSlackName.IM.value
        if channel.get("is_im")
        else ConversationTypeSlackName.MPIM.value
        if channel.get("is_mpim")
        else None
    )


def convert_conversation_type_to_slack_name(
    conversation_type: ConversationType,
) -> ConversationTypeSlackName:
    """Convert a conversation type to another using Slack naming standard.

    Args:
        conversation_type: The conversation type enum value.

    Returns:
        The corresponding conversation type enum value using Slack naming standard.
    """
    mapping = {
        ConversationType.PUBLIC_CHANNEL: ConversationTypeSlackName.PUBLIC_CHANNEL,
        ConversationType.PRIVATE_CHANNEL: ConversationTypeSlackName.PRIVATE_CHANNEL,
        ConversationType.MULTI_PERSON_DIRECT_MESSAGE: ConversationTypeSlackName.MPIM,
        ConversationType.DIRECT_MESSAGE: ConversationTypeSlackName.IM,
    }
    return mapping[conversation_type]


def extract_conversation_metadata(conversation: dict) -> dict:
    """Extract conversation metadata from a Slack conversation object.

    Args:
        conversation: The Slack conversation dictionary.

    Returns:
        A dictionary with the conversation metadata.
    """
    conversation_type = get_conversation_type(conversation)

    metadata = {
        "id": conversation.get("id"),
        "name": conversation.get("name"),
        "conversation_type": conversation_type,
        "is_private": conversation.get("is_private", True),
        "is_archived": conversation.get("is_archived", False),
        "is_member": conversation.get("is_member", True),
        "purpose": conversation.get("purpose", {}).get("value", ""),
        "num_members": conversation.get("num_members", 0),
    }

    if conversation_type == ConversationTypeSlackName.IM.value:
        metadata["num_members"] = 2
        metadata["user"] = conversation.get("user")
        metadata["is_user_deleted"] = conversation.get("is_user_deleted")
    elif conversation_type == ConversationTypeSlackName.MPIM.value:
        metadata["num_members"] = len(conversation.get("name", "").split("--"))

    return metadata


def extract_basic_user_info(user_info: dict) -> dict:
    """Extract a user's basic info from a Slack user dictionary.

    Args:
        user_info: The Slack user dictionary.

    Returns:
        A dictionary with the user's basic info.

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
    """Check if a Slack user represents a bot.

    Args:
        user: The Slack user dictionary.

    Returns:
        True if the user is a bot, False otherwise.

    Bots are users with the "is_bot" flag set to true.
    USLACKBOT is the user object for the Slack bot itself and is a special case.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return user.get("is_bot") or user.get("id") == "USLACKBOT"


def is_user_deleted(user: dict) -> bool:
    """Check if a Slack user represents a deleted user.

    Args:
        user: The Slack user dictionary.

    Returns:
        True if the user is deleted, False otherwise.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return user.get("deleted", False)


async def async_paginate(
    func: Callable,
    response_key: Optional[str] = None,
    limit: Optional[int] = MAX_PAGINATION_LIMIT,
    next_cursor: Optional[str] = None,
    *args,
    **kwargs,
) -> tuple[list, Optional[str]]:
    """Paginate a Slack AsyncWebClient's method results.

    The purpose is to abstract the pagination work and make it easier for the LLM to retrieve the
    amount of items requested by the user, regardless of limits imposed by the Slack API. We still
    return the next cursor, if needed to paginate further.

    Args:
        func: The Slack AsyncWebClient's method to paginate.
        response_key: The key in the response dictionary to extract the items from (optional). If
            not provided, the entire response dictionary is used.
        limit: The maximum number of items to retrieve (defaults to Slack's suggested limit).
        next_cursor: The cursor to use for pagination (optional).
        *args: Positional arguments to pass to the Slack method.
        **kwargs: Keyword arguments to pass to the Slack method.

    Returns:
        A tuple containing the list of items and the next cursor, if needed to paginate further.
    """
    results = []
    while len(results) < limit:
        slack_limit = min(limit - len(results), MAX_PAGINATION_LIMIT)
        response = await func(*args, **{**kwargs, "limit": slack_limit, "cursor": next_cursor})

        try:
            results.extend(dict(response.data) if not response_key else response[response_key])
        except KeyError:
            raise ValueError(f"Response key {response_key} not found in Slack response")

        next_cursor = response.get("response_metadata", {}).get("next_cursor")

        if not next_cursor:
            break

    return results, next_cursor


def enrich_message_datetime(message: dict) -> dict:
    """Enrich message metadata with formatted datetime.

    It helps LLMs when they need to display the date/time in human-readable format. Slack
    will only return a unix-formatted timestamp (it's not actually unix timestamp (UTC), but
    the unix timestamp in the user's timezone - I know, odd, but it is what it is).

    Args:
        message: The Slack message dictionary.

    Returns:
        The enriched message dictionary.
    """
    ts = message.get("ts")
    if ts:
        message["datetime_timestamp"] = datetime.fromtimestamp(float(ts)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    return message


def convert_datetime_to_unix_timestamp(datetime_str: str) -> int:
    """Convert a datetime string to a unix timestamp.

    Args:
        datetime_str: The datetime string ('YYYY-MM-DD HH:MM:SS') to convert to a unix timestamp.

    Returns:
        The unix timestamp integer.
    """
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        raise RetryableToolError(
            "Invalid datetime format",
            developer_message=f"The datetime '{datetime_str}' is invalid. "
            "Please provide a datetime string in the format 'YYYY-MM-DD HH:MM:SS'.",
            retry_after_ms=500,
        )


def convert_relative_datetime_to_unix_timestamp(
    relative_datetime: str,
    current_unix_timestamp: Optional[int] = None,
) -> int:
    """Convert a relative datetime string in the format 'DD:HH:MM' to unix timestamp.

    Args:
        relative_datetime: The relative datetime string ('DD:HH:MM') to convert to a unix timestamp.
        current_unix_timestamp: The current unix timestamp (optional). If not provided, the
            current unix timestamp from datetime.now is used.

    Returns:
        The unix timestamp integer.
    """
    if not current_unix_timestamp:
        current_unix_timestamp = int(datetime.now(timezone.utc).timestamp())

    days, hours, minutes = map(int, relative_datetime.split(":"))
    seconds = days * 86400 + hours * 3600 + minutes * 60
    return int(current_unix_timestamp - seconds)
