import enum


class FilterCondition(enum.Enum):
    OR = "or"
    AND = "and"


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


class DatetimeField(enum.Enum):
    LAST_MODIFIED = "lastModifiedDateTime"
    CREATED = "createdDateTime"

    @property
    def order_by_clause(self) -> str:
        return "lastModifiedDateTime desc" if self == self.LAST_MODIFIED else "createdDateTime desc"


CHANNEL_PROPS = [
    "id",
    "displayName",
    "description",
    "createdDateTime",
    "isArchived",
    "membershipType",
    "webUrl",
]
