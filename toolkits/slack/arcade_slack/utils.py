import asyncio
from datetime import datetime, timezone
from typing import Callable, Literal, NewType, NotRequired, Optional, TypedDict

from arcade.sdk.errors import RetryableToolError

from arcade_slack.constants import MAX_PAGINATION_SIZE_LIMIT, MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import ConversationType, ConversationTypeSlackName
from arcade_slack.tools.exceptions import PaginationTimeoutError

SlackOffsetSecondsFromUTC = NewType("SlackOffsetSecondsFromUTC", int)  # observe it can be negative
SlackPaginationNextCursor = NewType("SlackPaginationNextCursor", str)
SlackUserFieldId = NewType("SlackUserFieldId", str)
SlackUserId = NewType("SlackUserId", str)
SlackTeamId = NewType("SlackTeamId", str)
SlackTimestampStr = NewType("SlackTimestampStr", str)

"""
About Slack types in general: Slack does not guarantee the presence of all fields for a given
object. It will vary from endpoint to endpoint and even if the field is present, they say it may
contain a None value or an empty string instead of the actual expected value.

Because of that, our TypedDicts ended up having to be mostly total=False and most of the fields'
type hints are Optional. Use Slack dictionary fields with caution. It's advisable to validate the
value before using it, so that we can raise errors that are clear to understand.

See, for example, the 'Common Fields' section of the user type definition at:
https://api.slack.com/types/user#fields (https://archive.is/RUZdL)
"""


class SlackUserFieldData(TypedDict, total=False):
    """Type definition for Slack user field data dictionary.

    Slack type definition: https://api.slack.com/methods/users.profile.set#custom-profile
    """

    value: Optional[str]
    alt: Optional[bool]


class SlackUserField(TypedDict, total=False):
    """Type definition for Slack user field dictionary.

    Slack type definition: https://api.slack.com/methods/users.profile.set#custom-profile

    The field IDs are dynamic alphanumeric strings.
    """

    __annotations__ = {SlackUserFieldId: SlackUserFieldData}


class SlackStatusEmojiDisplayInfo(TypedDict, total=False):
    """Type definition for Slack status emoji display info dictionary."""

    emoji_name: Optional[str]
    display_url: Optional[str]


class SlackUserProfile(TypedDict, total=False):
    """Type definition for Slack user profile dictionary.

    Slack type definition: https://api.slack.com/types/user#profile (https://archive.is/RUZdL)
    """

    title: Optional[str]
    phone: Optional[str]
    skype: Optional[str]
    email: Optional[str]
    real_name: Optional[str]
    real_name_normalized: Optional[str]
    display_name: Optional[str]
    display_name_normalized: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    fields: Optional[list[SlackUserField]]
    image_original: Optional[str]
    is_custom_image: Optional[bool]
    image_24: Optional[str]
    image_32: Optional[str]
    image_48: Optional[str]
    image_72: Optional[str]
    image_192: Optional[str]
    image_512: Optional[str]
    image_1024: Optional[str]
    status_emoji: Optional[str]
    status_emoji_display_info: Optional[list[SlackStatusEmojiDisplayInfo]]
    status_text: Optional[str]
    status_text_canonical: Optional[str]
    status_expiration: Optional[int]
    avatar_hash: Optional[str]
    start_date: Optional[str]
    pronouns: Optional[str]
    huddle_state: Optional[str]
    huddle_state_expiration: Optional[int]
    team: Optional[SlackTeamId]


class SlackUser(TypedDict, total=False):
    """Type definition for Slack user dictionary.

    Slack type definition: https://api.slack.com/types/user (https://archive.is/RUZdL)
    """

    id: SlackUserId
    team_id: SlackTeamId
    name: Optional[str]
    deleted: Optional[bool]
    color: Optional[str]
    real_name: Optional[str]
    tz: Optional[str]
    tz_label: Optional[str]
    tz_offset: Optional[SlackOffsetSecondsFromUTC]
    profile: Optional[SlackUserProfile]
    is_admin: Optional[bool]
    is_owner: Optional[bool]
    is_primary_owner: Optional[bool]
    is_restricted: Optional[bool]
    is_ultra_restricted: Optional[bool]
    is_bot: Optional[bool]
    is_app_user: Optional[bool]
    is_email_confirmed: Optional[bool]
    who_can_share_contact_card: Optional[str]


class SlackUserList(TypedDict, total=False):
    """Type definition for the returned user list dictionary."""

    members: list[SlackUser]


class SlackConversationPurpose(TypedDict, total=False):
    """Type definition for the Slack conversation purpose dictionary."""

    value: Optional[str]


class SlackConversation(TypedDict, total=False):
    """Type definition for the Slack conversation dictionary."""

    id: Optional[str]
    name: Optional[str]
    is_private: Optional[bool]
    is_archived: Optional[bool]
    is_member: Optional[bool]
    is_channel: Optional[bool]
    is_group: Optional[bool]
    is_im: Optional[bool]
    is_mpim: Optional[bool]
    purpose: Optional[SlackConversationPurpose]
    num_members: Optional[int]
    user: Optional[SlackUser]
    is_user_deleted: Optional[bool]


class SlackMessage(TypedDict, total=True):
    """Type definition for the Slack message dictionary."""

    type: Literal["message"] = "message"
    user: SlackUser
    text: str
    ts: SlackTimestampStr  # Slack timestamp as a string (e.g. "1234567890.123456")


class Message(SlackMessage, total=False):
    """Type definition for the message dictionary.

    Having a human-readable datetime string is useful for LLMs when they need to display the
    date/time for the user. If not, they'll try to convert the unix timestamp to a human-readable
    date/time,which they don't usually do accurately.
    """

    datetime_timestamp: str  # Human-readable datetime string (e.g. "2025-01-22 12:00:00")


class ConversationMetadata(TypedDict, total=True):
    """Type definition for the conversation metadata dictionary."""

    id: Optional[str]
    name: Optional[str]
    conversation_type: Optional[ConversationTypeSlackName]
    is_private: Optional[bool]
    is_archived: Optional[bool]
    is_member: Optional[bool]
    purpose: Optional[str]
    num_members: NotRequired[int]
    user: NotRequired[SlackUser]
    is_user_deleted: NotRequired[bool]


class BasicUserInfo(TypedDict, total=False):
    """Type definition for the returned basic user info dictionary."""

    id: Optional[str]
    name: Optional[str]
    is_bot: Optional[bool]
    email: Optional[str]
    display_name: Optional[str]
    real_name: Optional[str]
    timezone: Optional[str]


def format_users(user_list_response: SlackUserList) -> str:
    """Format a list of Slack users into a CSV string.

    Args:
        userListResponse: The response from the Slack API's users_list method.

    Returns:
        A CSV string with two columns: the users' name and real name, each user in a new line.
    """
    csv_string = "All active Slack users:\n\nname,real_name\n"
    for user in user_list_response["members"]:
        if not user.get("deleted", False):
            name = user.get("name", "")
            real_name = user.get("profile", {}).get("real_name", "")
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


def get_conversation_type(channel: SlackConversation) -> ConversationTypeSlackName:
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
    conversation_type = get_conversation_type(conversation)

    metadata = ConversationMetadata(
        id=conversation.get("id"),
        name=conversation.get("name"),
        conversation_type=conversation_type,
        is_private=conversation.get("is_private", True),
        is_archived=conversation.get("is_archived", False),
        is_member=conversation.get("is_member", True),
        purpose=conversation.get("purpose", {}).get("value", ""),
        num_members=conversation.get("num_members", 0),
    )

    if conversation_type == ConversationTypeSlackName.IM.value:
        metadata["num_members"] = 2
        metadata["user"] = conversation.get("user")
        metadata["is_user_deleted"] = conversation.get("is_user_deleted")
    elif conversation_type == ConversationTypeSlackName.MPIM.value:
        metadata["num_members"] = len(conversation.get("name", "").split("--"))

    return metadata


def extract_basic_user_info(user_info: SlackUser) -> BasicUserInfo:
    """Extract a user's basic info from a Slack user dictionary.

    Args:
        user_info: The Slack user dictionary.

    Returns:
        A dictionary with the user's basic info.

    See https://api.slack.com/types/user for the structure of the user object.
    """
    return BasicUserInfo(
        id=user_info.get("id"),
        name=user_info.get("name"),
        is_bot=user_info.get("is_bot"),
        email=user_info.get("profile", {}).get("email"),
        display_name=user_info.get("profile", {}).get("display_name"),
        real_name=user_info.get("real_name"),
        timezone=user_info.get("tz"),
    )


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
    return user.get("deleted", False)


async def async_paginate(
    func: Callable,
    response_key: Optional[str] = None,
    limit: Optional[int] = MAX_PAGINATION_SIZE_LIMIT,
    next_cursor: Optional[SlackPaginationNextCursor] = None,
    max_pagination_timeout_seconds: Optional[int] = MAX_PAGINATION_TIMEOUT_SECONDS,
    *args,
    **kwargs,
) -> tuple[list, Optional[SlackPaginationNextCursor]]:
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
    should_continue = True

    try:
        async with asyncio.timeout(max_pagination_timeout_seconds):
            while should_continue:
                # The slack_limit variable makes the Slack API return no more than the appropriate
                # amount of items. The loop extends results with the items returned and continues
                # iterating if it hasn't reached the limit, and Slack indicates there're more
                # items to retrieve.
                slack_limit = min(limit - len(results), MAX_PAGINATION_SIZE_LIMIT)
                response = await func(
                    *args, **{**kwargs, "limit": slack_limit, "cursor": next_cursor}
                )

                try:
                    results.extend(
                        dict(response.data) if not response_key else response[response_key]
                    )
                except KeyError:
                    raise ValueError(f"Response key {response_key} not found in Slack response")

                next_cursor = response.get("response_metadata", {}).get("next_cursor")

                if len(results) >= limit or not next_cursor:
                    should_continue = False
    except asyncio.TimeoutError:
        raise PaginationTimeoutError(max_pagination_timeout_seconds)

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
    ts = message.get("ts")
    if ts:
        try:
            ts = float(ts)
        except ValueError:
            raise RetryableToolError(
                "Invalid datetime format",
                developer_message=f"The datetime '{ts}' is invalid. "
                "Please provide a datetime string in the format 'YYYY-MM-DD HH:MM:SS'.",
                retry_after_ms=500,
            )
        message["datetime_timestamp"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
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
