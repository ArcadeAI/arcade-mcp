import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import suppress
from enum import Enum
from typing import Any, Literal, TypedDict

from arcade_tdk.errors import ToolExecutionError
from slack_sdk.errors import SlackApiError

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

    def to_slack_name_str(self) -> str:
        mapping = {
            ConversationType.PUBLIC_CHANNEL: ConversationTypeSlackName.PUBLIC_CHANNEL.value,
            ConversationType.PRIVATE_CHANNEL: ConversationTypeSlackName.PRIVATE_CHANNEL.value,
            ConversationType.MULTI_PERSON_DIRECT_MESSAGE: ConversationTypeSlackName.MPIM.value,
            ConversationType.DIRECT_MESSAGE: ConversationTypeSlackName.IM.value,
        }

        return mapping[self]


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


class PaginationSentinel(ABC):
    """Base class for pagination sentinel classes."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    @abstractmethod
    def __call__(self, last_result: Any) -> bool:
        """Determine if the pagination should stop."""
        raise NotImplementedError


class FindUserByUsernameSentinel(PaginationSentinel):
    """Sentinel class for finding a user by username."""

    def __call__(self, last_result: Any) -> bool:
        for user in last_result:
            if not isinstance(user.get("name"), str):
                continue
            if user.get("name").casefold() == self.kwargs["username"].casefold():
                return True
        return False


class FindMultipleUsersByUsernameSentinel(PaginationSentinel):
    """Sentinel class for finding multiple users by username."""

    def __init__(self, usernames: list[str]) -> None:
        if not usernames:
            raise ValueError("usernames must be a non-empty list of strings")
        super().__init__(usernames=usernames)
        self.usernames_pending = {username.casefold() for username in usernames}

    def _flag_username_found(self, username: str) -> None:
        with suppress(KeyError):
            self.usernames_pending.remove(username.casefold())

    def _all_usernames_found(self) -> bool:
        return not self.usernames_pending

    def __call__(self, last_result: Any) -> bool:
        if not self.usernames_pending:
            return True
        for user in last_result:
            username = user.get("name")
            if not isinstance(username, str):
                continue
            if username.casefold() in self.usernames_pending:
                self._flag_username_found(username)
                if self._all_usernames_found():
                    return True
        return False


class FindMultipleUsersByIdSentinel(PaginationSentinel):
    """Sentinel class for finding multiple users by ID."""

    def __init__(self, user_ids: list[str]) -> None:
        if not user_ids:
            raise ValueError("user_ids must be a non-empty list of strings")
        super().__init__(user_ids=user_ids)
        self.user_ids_pending = set(user_ids)

    def _flag_user_id_found(self, user_id: str) -> None:
        with suppress(KeyError):
            self.user_ids_pending.remove(user_id.casefold())

    def _all_user_ids_found(self) -> bool:
        return not self.user_ids_pending

    def __call__(self, last_result: Any) -> bool:
        if not self.user_ids_pending:
            return True
        for user in last_result:
            user_id = user.get("id")
            if user_id in self.user_ids_pending:
                self._flag_user_id_found(user_id)
                if self._all_user_ids_found():
                    return True
        return False


class FindChannelByNameSentinel(PaginationSentinel):
    """Sentinel class for finding a channel by name."""

    def __init__(self, channel_name: str) -> None:
        super().__init__(channel_name=channel_name)
        self.channel_name_casefold = channel_name.casefold()

    def __call__(self, last_result: Any) -> bool:
        for channel in last_result:
            channel_name = channel.get("name")
            if not isinstance(channel_name, str):
                continue
            if channel_name.casefold() == self.channel_name_casefold:
                return True
        return False


class AbstractConcurrencySafeCoroutineCaller(ABC):
    """Abstract base class for concurrency-safe coroutine callers."""

    def __init__(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    async def __call__(self, semaphore: asyncio.Semaphore) -> Any:
        """Call a coroutine with a semaphore."""
        raise NotImplementedError


class ConcurrencySafeCoroutineCaller(AbstractConcurrencySafeCoroutineCaller):
    """Calls a coroutine with an asyncio semaphore."""

    async def __call__(self, semaphore: asyncio.Semaphore) -> Any:
        async with semaphore:
            return await self.func(*self.args, **self.kwargs)


class GetUserByEmailCaller(AbstractConcurrencySafeCoroutineCaller):
    """Call Slack's lookupByEmail method with an asyncio semaphore while handling API errors."""

    def __init__(
        self,
        func: Callable[..., Awaitable[Any]],
        email: str,
    ) -> None:
        super().__init__(func)
        self.email = email

    async def __call__(self, semaphore: asyncio.Semaphore) -> dict[str, Any]:
        async with semaphore:
            try:
                user = await self.func(email=self.email)
                return {"user": user["user"], "email": self.email}
            except SlackApiError as e:
                if e.response.get("error") in ["user_not_found", "users_not_found"]:
                    return {"user": None, "email": self.email}
                else:
                    raise ToolExecutionError(
                        message="Error getting user by email",
                        developer_message=f"Error getting user by email: {e.response.get('error')}",
                    )
