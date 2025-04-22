from enum import Enum
from typing import Literal, TypedDict

from arcade_slack.custom_types import (
    SlackOffsetSecondsFromUTC,
    SlackPaginationNextCursor,
    SlackTeamId,
    SlackTimestampStr,
    SlackUserFieldId,
    SlackUserId,
)


class ConversationTypeSlackName(str, Enum):
    PUBLIC_CHANNEL = "public_channel"  # Public channels are visible to all users in the workspace
    PRIVATE_CHANNEL = "private_channel"  # Private channels are visible to only specific users
    MPIM = "mpim"  # Multi-person direct message conversation
    IM = "im"  # Two person direct message conversation


class ConversationType(str, Enum):
    PUBLIC_CHANNEL = "public_channel"
    PRIVATE_CHANNEL = "private_channel"
    MULTI_PERSON_DIRECT_MESSAGE = "multi_person_direct_message"
    DIRECT_MESSAGE = "direct_message"


"""
About Slack dictionaries: Slack does not guarantee the presence of all fields for a given
object. It will vary from endpoint to endpoint and even if the field is present, they say it may
contain a None value or an empty string instead of the actual expected value.

See, for example, the 'Common Fields' section of the user type definition at:
https://api.slack.com/types/user#fields (https://archive.is/RUZdL)

Because of that, our TypedDicts ended up having to be mostly total=False and most of the fields'
type hints are Optional. Use Slack dictionary fields with caution. It's advisable to validate the
value before using it and raise errors that are clear to understand, when appropriate.
"""


class SlackUserFieldData(TypedDict, total=False):
    """Type definition for Slack user field data dictionary.

    Slack type definition: https://api.slack.com/methods/users.profile.set#custom-profile
    """

    value: str | None
    alt: bool | None


class SlackStatusEmojiDisplayInfo(TypedDict, total=False):
    """Type definition for Slack status emoji display info dictionary."""

    emoji_name: str | None
    display_url: str | None


class SlackUserProfile(TypedDict, total=False):
    """Type definition for Slack user profile dictionary.

    Slack type definition: https://api.slack.com/types/user#profile (https://archive.is/RUZdL)
    """

    title: str | None
    phone: str | None
    skype: str | None
    email: str | None
    real_name: str | None
    real_name_normalized: str | None
    display_name: str | None
    display_name_normalized: str | None
    first_name: str | None
    last_name: str | None
    fields: list[dict[SlackUserFieldId, SlackUserFieldData]] | None
    image_original: str | None
    is_custom_image: bool | None
    image_24: str | None
    image_32: str | None
    image_48: str | None
    image_72: str | None
    image_192: str | None
    image_512: str | None
    image_1024: str | None
    status_emoji: str | None
    status_emoji_display_info: list[SlackStatusEmojiDisplayInfo] | None
    status_text: str | None
    status_text_canonical: str | None
    status_expiration: int | None
    avatar_hash: str | None
    start_date: str | None
    pronouns: str | None
    huddle_state: str | None
    huddle_state_expiration: int | None
    team: SlackTeamId | None


class SlackUser(TypedDict, total=False):
    """Type definition for Slack user dictionary.

    Slack type definition: https://api.slack.com/types/user (https://archive.is/RUZdL)
    """

    id: SlackUserId
    team_id: SlackTeamId
    name: str | None
    deleted: bool | None
    color: str | None
    real_name: str | None
    tz: str | None
    tz_label: str | None
    tz_offset: SlackOffsetSecondsFromUTC | None
    profile: SlackUserProfile | None
    is_admin: bool | None
    is_owner: bool | None
    is_primary_owner: bool | None
    is_restricted: bool | None
    is_ultra_restricted: bool | None
    is_bot: bool | None
    is_app_user: bool | None
    is_email_confirmed: bool | None
    who_can_share_contact_card: str | None


class SlackUserList(TypedDict, total=False):
    """Type definition for the returned user list dictionary."""

    members: list[SlackUser]


class SlackConversationPurpose(TypedDict, total=False):
    """Type definition for the Slack conversation purpose dictionary."""

    value: str | None


class SlackConversation(TypedDict, total=False):
    """Type definition for the Slack conversation dictionary."""

    id: str | None
    name: str | None
    is_private: bool | None
    is_archived: bool | None
    is_member: bool | None
    is_channel: bool | None
    is_group: bool | None
    is_im: bool | None
    is_mpim: bool | None
    purpose: SlackConversationPurpose | None
    num_members: int | None
    user: SlackUser | None
    is_user_deleted: bool | None


class SlackMessage(TypedDict, total=True):
    """Type definition for the Slack message dictionary."""

    type: Literal["message"]
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


class ConversationMetadata(TypedDict, total=False):
    """Type definition for the conversation metadata dictionary."""

    id: str | None
    name: str | None
    conversation_type: str | None
    is_private: bool | None
    is_archived: bool | None
    is_member: bool | None
    purpose: str | None
    num_members: int | None
    user: SlackUser | None
    is_user_deleted: bool | None


class BasicUserInfo(TypedDict, total=False):
    """Type definition for the returned basic user info dictionary."""

    id: str | None
    name: str | None
    is_bot: bool | None
    email: str | None
    display_name: str | None
    real_name: str | None
    timezone: str | None


class SlackConversationsToolResponse(TypedDict, total=True):
    """Type definition for the Slack conversations tool response dictionary."""

    conversations: list[ConversationMetadata]
    next_cursor: SlackPaginationNextCursor | None
