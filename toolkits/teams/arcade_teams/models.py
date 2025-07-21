from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from msgraph.generated.models.chat import Chat
from msgraph.generated.models.conversation_member import ConversationMember

from arcade_teams.exceptions import MatchHumansByNameRetryableError


class HumanNameMatchType(Enum):
    EXACT = "exact"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"


class ChatMembershipMatchType(Enum):
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"


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
        self.matches: dict[ChatMembershipMatchType, list[Chat]] = {
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
        if isinstance(chat.members, list) and len(chat.members) != self.expected_member_count:
            return None

        members = cast(list[ConversationMember], chat.members)

        members_by_id = {member.id: member for member in members}

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
                if not isinstance(member.display_name, str):
                    continue

                if member.display_name.casefold() == user_name.casefold():
                    del members_by_id[member.id]
                    break
                elif user_name.casefold() in member.display_name.casefold():
                    has_partial_match = True
                    del members_by_id[member.id]
                    break

        # If there are any members left in the list, it's not a match
        if members_by_id:
            return None

        return (
            ChatMembershipMatchType.PARTIAL_MATCH
            if has_partial_match
            else ChatMembershipMatchType.EXACT_MATCH
        )


@dataclass
class HumanNameMatch:
    human: dict
    match_type: HumanNameMatchType


class MatchHumansByName:
    def __init__(self, names: list[str], users: list[dict], people: list[dict]):
        self.matches_by_name: dict[str, list[HumanNameMatch]] = {}
        self.names = names
        self.users = users
        self.people = people
        self._human_id_matched: dict[str, set[str]] = {name: set() for name in names}

    def _human_name(self, human: dict) -> str:
        if human["name"].get("display"):
            return human["name"]["display"].casefold()
        elif human["name"].get("first") and human["name"].get("last"):
            return f"{human['name']['first']} {human['name']['last']}".casefold()
        else:
            return ""

    def run(self) -> None:
        for name in self.names:
            name_lower = name.casefold()
            self.matches_by_name[name] = []
            for user in self.users:
                user_name = self._human_name(user)
                if name_lower == user_name:
                    self.add_exact_match(name, user)
                elif name_lower in user_name:
                    self.add_partial_match(name, user)

            for person in self.people:
                person_name = self._human_name(person)
                if name_lower == person_name:
                    self.add_exact_match(name, person)
                elif name_lower in person_name:
                    self.add_partial_match(name, person)

    def add_exact_match(self, name: str, human: dict) -> None:
        if human["id"] in self._human_id_matched[name]:
            return

        human_match = HumanNameMatch(human=human, match_type=HumanNameMatchType.EXACT)
        self.matches_by_name[name].append(human_match)
        self._human_id_matched[name].add(human["id"])

    def add_partial_match(self, name: str, human: dict) -> None:
        if human["id"] in self._human_id_matched[name]:
            return

        human_match = HumanNameMatch(human=human, match_type=HumanNameMatchType.PARTIAL)
        self.matches_by_name[name].append(human_match)
        self._human_id_matched[name].add(human["id"])

    def get_unique_exact_matches(self, max_matches_per_name: int = 10) -> list[dict]:
        unique_exact_matches = []
        match_errors = []

        for name, matches in self.matches_by_name.items():
            exact_matches = []
            partial_matches = []
            human_ids_matched = set()
            for human_match in matches:
                if human_match.human["id"] in human_ids_matched:
                    continue

                if human_match.match_type == HumanNameMatchType.EXACT:
                    exact_matches.append(human_match.human)
                    # If we already found an exact match with this human id, we skip other matches
                    human_ids_matched.add(human_match.human["id"])
                else:
                    partial_matches.append(human_match.human)

            # If there is a single exact match, we ignore partial matches, if any
            if len(exact_matches) == 1:
                unique_exact_matches.append(exact_matches[0])

            # If there are none or multiple exact matches, we add this name to match errors
            else:
                # If multiple exact matches, we can ignore the partial ones
                final_matches = exact_matches or partial_matches
                match_error = {
                    "name": name,
                    "matches": final_matches[:max_matches_per_name],
                }
                if len(final_matches) > max_matches_per_name:
                    match_error["message"] = (
                        f"Too many matches found for '{name}'. "
                        f"Truncated to the first {max_matches_per_name} matches."
                    )
                match_errors.append(match_error)

        if match_errors:
            raise MatchHumansByNameRetryableError(match_errors)

        return unique_exact_matches
