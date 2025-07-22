import enum
import os
from collections.abc import Callable
from typing import Any


def enforce_greater_than_zero_int(key: str, value: str) -> int:
    if value.isdigit():
        int_value = int(value)
        if int_value > 0:
            return int_value
    error = f"Environment variable {key} must have a positive integer value greater than zero"
    raise ValueError(error)


def load_env_var(key: str, default: str | None = None, transform: Callable | None = None) -> Any:
    if key not in os.environ:
        if not default:
            return None
        if transform:
            return transform(key, default)
        else:
            return default

    value = os.getenv(key, default)
    if not value:
        error = f"Environment variable {key} is not set"
        raise ValueError(error)

    if transform:
        value = transform(key, value)

    return value


ENV_VARS = {
    "TEAMS_MAX_CONCURRENCY": load_env_var(
        "TEAMS_MAX_CONCURRENCY", "3", enforce_greater_than_zero_int
    ),
    "TEAMS_PAGINATION_TIMEOUT": load_env_var(
        "TEAMS_PAGINATION_TIMEOUT", "30", enforce_greater_than_zero_int
    ),
}


class FilterCondition(enum.Enum):
    OR = "OR"
    AND = "AND"


class MatchType(enum.Enum):
    EXACT = "exact_match"
    PARTIAL_ALL = "partial_match_all_keywords"
    PARTIAL_ANY = "partial_match_any_of_the_keywords"

    def to_filter_condition(self) -> FilterCondition:
        if self == MatchType.PARTIAL_ALL:
            return FilterCondition.AND
        elif self == MatchType.PARTIAL_ANY:
            return FilterCondition.OR
        return FilterCondition.AND


class PartialMatchType(enum.Enum):
    PARTIAL_ALL = "match_all_keywords"
    PARTIAL_ANY = "match_any_of_the_keywords"

    def to_filter_condition(self) -> FilterCondition:
        _map = {
            PartialMatchType.PARTIAL_ALL: FilterCondition.AND,
            PartialMatchType.PARTIAL_ANY: FilterCondition.OR,
        }
        return _map[self]


class DatetimeField(enum.Enum):
    LAST_MODIFIED = "lastModifiedDateTime"
    CREATED = "createdDateTime"

    @property
    def order_by_clause(self) -> str:
        return "lastModifiedDateTime desc" if self == self.LAST_MODIFIED else "createdDateTime desc"


class TeamMembershipType(enum.Enum):
    DIRECT_MEMBER = "direct_member_of_the_team"
    MEMBER_OF_SHARED_CHANNEL = "member_of_a_shared_channel_in_another_team"


CHANNEL_PROPS = [
    "id",
    "displayName",
    "description",
    "createdDateTime",
    "isArchived",
    "membershipType",
    "webUrl",
    "members",
]
