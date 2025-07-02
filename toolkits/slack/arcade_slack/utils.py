import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT, MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.custom_types import SlackPaginationNextCursor
from arcade_slack.exceptions import (
    PaginationTimeoutError,
    UsernameNotFoundError,
)
from arcade_slack.models import (
    BasicUserInfo,
    ConversationMetadata,
    ConversationType,
    ConversationTypeSlackName,
    Message,
    SlackConversation,
    SlackConversationPurpose,
    SlackMessage,
    SlackUser,
    SlackUserList,
)


def format_users(user_list_response: SlackUserList) -> str:
    """Format a list of Slack users into a CSV string.

    Args:
        userListResponse: The response from the Slack API's users_list method.

    Returns:
        A CSV string with two columns: the users' name and real name, each user in a new line.
        The first line is the header with column names 'name' and 'real_name'.
    """
    csv_string = "name,real_name\n"
    for user in user_list_response["members"]:
        if not user.get("deleted", False):
            name = user.get("name", "")
            profile = user.get("profile", {})
            real_name = "" if not profile else profile.get("real_name", "")
            csv_string += f"{name},{real_name}\n"
    return csv_string.strip()


def format_conversations_as_csv(conversations: dict) -> str:
    """Format a list of Slack conversations into a CSV string.

    Args:
        conversations: The response from the Slack API's conversations_list method.

    Returns:
        A CSV string with the conversations' names.
    """
    csv_string = "All active Slack conversations:\n\nname\n"
    for conversation in conversations["channels"]:
        if not conversation.get("is_archived", False):
            name = conversation.get("name", "")
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


def get_slack_conversation_type_as_str(channel: SlackConversation) -> str:
    """Get the type of conversation from a Slack channel's dictionary.

    Args:
        channel: The Slack channel's dictionary.

    Returns:
        The type of conversation string in Slack naming standard.
    """
    if channel.get("is_channel"):
        return ConversationTypeSlackName.PUBLIC_CHANNEL.value
    if channel.get("is_group"):
        return ConversationTypeSlackName.PRIVATE_CHANNEL.value
    if channel.get("is_im"):
        return ConversationTypeSlackName.IM.value
    if channel.get("is_mpim"):
        return ConversationTypeSlackName.MPIM.value
    raise ValueError(f"Invalid conversation type in channel {channel.get('name')}")


def get_user_by_username(username: str, users_list: list[dict]) -> SlackUser:
    usernames_found = []
    for user in users_list:
        if isinstance(user.get("name"), str):
            usernames_found.append(user["name"])
        username_found = user.get("name") or ""
        if username.lower() == username_found.lower():
            return SlackUser(**user)

    raise UsernameNotFoundError(usernames_found=usernames_found, username_not_found=username)


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


def extract_conversation_metadata(conversation: SlackConversation) -> ConversationMetadata:
    """Extract conversation metadata from a Slack conversation object.

    Args:
        conversation: The Slack conversation dictionary.

    Returns:
        A dictionary with the conversation metadata.
    """
    conversation_type = get_slack_conversation_type_as_str(conversation)

    purpose: SlackConversationPurpose | None = conversation.get("purpose")
    purpose_value = "" if not purpose else purpose.get("value", "")

    metadata = ConversationMetadata(
        id=conversation.get("id"),
        name=conversation.get("name"),
        conversation_type=conversation_type,
        is_private=conversation.get("is_private", True),
        is_archived=conversation.get("is_archived", False),
        is_member=conversation.get("is_member", True),
        purpose=purpose_value,
        num_members=conversation.get("num_members", 0),
    )

    if conversation_type == ConversationTypeSlackName.IM.value:
        metadata["num_members"] = 2
        metadata["user"] = conversation.get("user")
        metadata["is_user_deleted"] = conversation.get("is_user_deleted")
    elif conversation_type == ConversationTypeSlackName.MPIM.value:
        conversation_name = conversation.get("name", "")
        if conversation_name:
            metadata["num_members"] = len(conversation_name.split("--"))
        else:
            metadata["num_members"] = None

    return metadata


def extract_basic_user_info(user_info: SlackUser) -> BasicUserInfo:
    """Extract a user's basic info from a Slack user dictionary.

    Args:
        user_info: The Slack user dictionary.

    Returns:
        A dictionary with the user's basic info.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    profile = user_info.get("profile", {})
    display_name = None if not profile else profile.get("display_name")
    email = None if not profile else profile.get("email")
    return BasicUserInfo(
        id=user_info.get("id"),
        name=user_info.get("name"),
        is_bot=user_info.get("is_bot"),
        email=email,
        display_name=display_name,
        real_name=user_info.get("real_name"),
        timezone=user_info.get("tz"),
    )


async def associate_members_of_multiple_conversations(
    get_members_in_conversation_func: Callable,
    conversations: list[dict],
    context: ToolContext,
) -> list[dict]:
    """Associate members to each conversation, returning the updated list."""
    return await asyncio.gather(*[  # type: ignore[no-any-return]
        associate_members_of_conversation(get_members_in_conversation_func, context, conv)
        for conv in conversations
    ])


async def associate_members_of_conversation(
    get_members_in_conversation_func: Callable,
    context: ToolContext,
    conversation: dict,
) -> dict:
    response = await get_members_in_conversation_func(context, conversation["id"])
    conversation["members"] = response["members"]
    return conversation


async def retrieve_conversations_by_user_ids(
    list_conversations_func: Callable,
    get_members_in_conversation_func: Callable,
    context: ToolContext,
    conversation_types: list[ConversationType],
    user_ids: list[str],
    exact_match: bool = False,
    limit: int | None = None,
    next_cursor: str | None = None,
) -> list[dict]:
    """
    Retrieve conversations filtered by the given user IDs. Includes pagination support
    and optionally limits the number of returned conversations.
    """
    conversations_found: list[dict] = []

    response = await list_conversations_func(
        context=context,
        conversation_types=conversation_types,
        next_cursor=next_cursor,
    )

    # Associate members to each conversation
    conversations_with_members = await associate_members_of_multiple_conversations(
        get_members_in_conversation_func, response["conversations"], context
    )

    conversations_found.extend(
        filter_conversations_by_user_ids(conversations_with_members, user_ids, exact_match)
    )

    return conversations_found[:limit]


def filter_conversations_by_user_ids(
    conversations: list[dict],
    user_ids: list[str],
    exact_match: bool = False,
) -> list[dict]:
    """
    Filter conversations by the members' user IDs.

    Args:
        conversations: The list of conversations to filter.
        user_ids: The user IDs to filter conversations for.
        exact_match: Whether to match the exact number of members in the conversations.

    Returns:
        The list of conversations found.
    """
    matches = []
    for conversation in conversations:
        member_ids = [member["id"] for member in conversation["members"]]
        if exact_match:
            same_length = len(user_ids) == len(member_ids)
            has_all_members = all(user_id in member_ids for user_id in user_ids)
            if same_length and has_all_members:
                matches.append(conversation)
        else:
            if all(user_id in member_ids for user_id in user_ids):
                matches.append(conversation)

    return matches


def is_user_a_bot(user: SlackUser) -> bool:
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


def is_user_deleted(user: SlackUser) -> bool:
    """Check if a Slack user represents a deleted user.

    Args:
        user: The Slack user dictionary.

    Returns:
        True if the user is deleted, False otherwise.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    is_deleted = user.get("deleted")

    return is_deleted if isinstance(is_deleted, bool) else False


async def async_paginate(
    func: Callable,
    response_key: str | None = None,
    limit: int | None = None,
    next_cursor: SlackPaginationNextCursor | None = None,
    max_pagination_timeout_seconds: int = MAX_PAGINATION_TIMEOUT_SECONDS,
    *args: Any,
    **kwargs: Any,
) -> tuple[list, SlackPaginationNextCursor | None]:
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
    results: list[Any] = []

    async def paginate_loop() -> list[Any]:
        nonlocal results, next_cursor
        should_continue = True

        """
        The slack_limit variable makes the Slack API return no more than the appropriate
        amount of items. The loop extends results with the items returned and continues
        iterating if it hasn't reached the limit, and Slack indicates there're more
        items to retrieve.
        """

        while should_continue:
            iteration_limit = limit - len(results) if limit else MAX_PAGINATION_SIZE_LIMIT
            slack_limit = min(iteration_limit, MAX_PAGINATION_SIZE_LIMIT)
            iteration_kwargs = {**kwargs, "limit": slack_limit, "cursor": next_cursor}
            response = await func(*args, **iteration_kwargs)

            try:
                results.extend(dict(response.data) if not response_key else response[response_key])
            except KeyError:
                raise ValueError(f"Response key {response_key} not found in Slack response")

            next_cursor = response.get("response_metadata", {}).get("next_cursor")

            if (limit and len(results) >= limit) or not next_cursor:
                should_continue = False

        return results

    try:
        results = await asyncio.wait_for(paginate_loop(), timeout=max_pagination_timeout_seconds)
    # asyncio.TimeoutError for Python <= 3.10, TimeoutError for Python >= 3.11
    except (TimeoutError, asyncio.TimeoutError):
        raise PaginationTimeoutError(max_pagination_timeout_seconds)
    else:
        return results, next_cursor


def enrich_message_datetime(message: SlackMessage) -> Message:
    """Enrich message metadata with formatted datetime.

    It helps LLMs when they need to display the date/time in human-readable format. Slack
    will only return a unix-formatted timestamp (it's not actually UTC Unix timestamp, but
    the Unix timestamp in the user's timezone - I know, odd, but it is what it is).

    Args:
        message: The Slack message dictionary.

    Returns:
        The enriched message dictionary.
    """
    message = Message(**message)
    ts = message.get("ts")
    if isinstance(ts, str):
        try:
            timestamp = float(ts)
            message["datetime_timestamp"] = datetime.fromtimestamp(timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            pass
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
    current_unix_timestamp: int | None = None,
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
