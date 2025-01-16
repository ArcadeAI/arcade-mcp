from typing import Callable, Optional

from slack_sdk.errors import SlackApiError

from arcade_slack.constants import MAX_PAGINATION_LIMIT
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


def extract_conversation_metadata(conversation: dict) -> dict:
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

    if conversation_type == ConversationType.IM.value:
        metadata["num_members"] = 2
        metadata["user"] = conversation.get("user")
        metadata["is_user_deleted"] = conversation.get("is_user_deleted")
    elif conversation_type == ConversationType.MPIM.value:
        metadata["num_members"] = len(conversation.get("name", "").split("--"))

    return metadata


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


async def async_paginate(
    func: Callable,
    response_key: Optional[str] = None,
    limit: Optional[int] = MAX_PAGINATION_LIMIT,
    next_cursor: Optional[str] = None,
    *args,
    **kwargs,
) -> tuple[list, Optional[str]]:
    """Paginate a Slack AsyncWebClient's function results.

    The purpose is to abstract the pagination work and make it easier for the LLM to retrieve the
    amount of items requested by the user, regardless of limits imposed by the Slack API. We still
    return the next cursor, if needed to paginate further.
    """
    results = []
    while len(results) < limit:
        slack_limit = min(limit - len(results), MAX_PAGINATION_LIMIT)
        response = await func(*args, **{**kwargs, "limit": slack_limit, "cursor": next_cursor})

        if not response.get("ok"):
            raise SlackApiError(response.get("error", "Unknown error"), response)

        try:
            results.extend(response if not response_key else response[response_key])
        except KeyError:
            raise ValueError(f"Response key {response_key} not found in Slack response")

        next_cursor = response.get("response_metadata", {}).get("next_cursor")

        if not next_cursor:
            break

    return results, next_cursor
