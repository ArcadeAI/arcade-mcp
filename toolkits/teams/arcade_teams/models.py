from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from msgraph.generated.models.chat import Chat


class ChatMembershipMatchType(Enum):
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"


class TeamMembershipType(Enum):
    DIRECT_MEMBER = "direct_member_of_the_team"
    MEMBER_OF_SHARED_CHANNEL = "member_of_a_shared_channel_in_another_team"


class PaginationSentinel(ABC):
    """Base class for pagination sentinel classes."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    @abstractmethod
    def __call__(self, last_result: Any) -> bool | tuple[bool, list[Any]]:
        """Determine if the pagination should stop."""
        raise NotImplementedError


class FindChatByMembersSentinel(PaginationSentinel):
    def __init__(self, user_ids: list[str] | None = None, user_names: list[str] | None = None):
        self.user_ids = user_ids or []
        self.user_names = user_names or []
        self.expected_member_count = len(self.user_ids) + len(self.user_names)
        self.matches = {
            ChatMembershipMatchType.EXACT_MATCH: [],
            ChatMembershipMatchType.PARTIAL_MATCH: [],
        }

    @property
    def exact_matches(self) -> list[Chat]:
        return self.matches[ChatMembershipMatchType.EXACT_MATCH]

    @property
    def partial_matches(self) -> list[Chat]:
        return self.matches[ChatMembershipMatchType.PARTIAL_MATCH]

    def __call__(self, last_result: Any) -> bool:
        if len(self.matches[ChatMembershipMatchType.EXACT_MATCH]) > 0:
            return True

        for chat in last_result:
            match_type = self.chat_members_match(chat)
            if match_type:
                self.matches[match_type].append(chat)

        return len(self.matches[ChatMembershipMatchType.EXACT_MATCH]) > 0

    def chat_members_match(self, chat: Chat) -> ChatMembershipMatchType | None:
        # First we check if the member list length matches
        if len(chat.members) != self.expected_member_count:
            return None

        members_by_id = {member.user_id: member for member in chat.members}

        # Check the user_ids
        member_user_ids = set(members_by_id.keys())
        for user_id in self.user_ids:
            if user_id in member_user_ids:
                del members_by_id[user_id]
            # If the user_id is not in the member list, it's not a match
            else:
                return None

        has_partial_match = False

        # Check the user_names
        for user_name in self.user_names:
            for member in members_by_id.values():
                if member.display_name.casefold() == user_name.casefold():
                    del members_by_id[member.user_id]
                    break
                elif user_name.casefold() in member.display_name.casefold():
                    has_partial_match = True
                    del members_by_id[member.user_id]
                    break

        # If there are any members left in the list, it's not a match
        if members_by_id:
            return None

        return (
            ChatMembershipMatchType.PARTIAL_MATCH
            if has_partial_match
            else ChatMembershipMatchType.EXACT_MATCH
        )
