from enum import Enum
from typing import Optional

from typing_extensions import Literal, NotRequired, TypedDict

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

    value: Optional[str]
    alt: Optional[bool]


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
    fields: Optional[list[dict[SlackUserFieldId, SlackUserFieldData]]]
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


class ConversationMetadata(TypedDict, total=True):
    """Type definition for the conversation metadata dictionary."""

    id: Optional[str]
    name: Optional[str]
    conversation_type: Optional[str]
    is_private: Optional[bool]
    is_archived: Optional[bool]
    is_member: Optional[bool]
    purpose: Optional[str]
    num_members: NotRequired[Optional[int]]
    user: NotRequired[Optional[SlackUser]]
    is_user_deleted: NotRequired[Optional[bool]]


class BasicUserInfo(TypedDict, total=False):
    """Type definition for the returned basic user info dictionary."""

    id: Optional[str]
    name: Optional[str]
    is_bot: Optional[bool]
    email: Optional[str]
    display_name: Optional[str]
    real_name: Optional[str]
    timezone: Optional[str]


class SlackConversationsToolResponse(TypedDict, total=True):
    """Type definition for the Slack conversations tool response dictionary."""

    conversations: list[ConversationMetadata]
    next_cursor: SlackPaginationNextCursor | None
