from enum import Enum


class SubredditListingType(str, Enum):
    HOT = "hot"
    NEW = "new"
    RISING = "rising"
    TOP = "top"  # time-based
    CONTROVERSIAL = "controversial"  # time-based

    def is_time_based(self) -> bool:
        return self in [SubredditListingType.TOP, SubredditListingType.CONTROVERSIAL]


class RedditTimeFilter(str, Enum):
    NOW = "NOW"
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    THIS_YEAR = "THIS_YEAR"
    ALL_TIME = "ALL_TIME"

    def to_api_value(self) -> str:
        _map = {
            RedditTimeFilter.NOW: "hour",
            RedditTimeFilter.TODAY: "day",
            RedditTimeFilter.THIS_WEEK: "week",
            RedditTimeFilter.THIS_MONTH: "month",
            RedditTimeFilter.THIS_YEAR: "year",
            RedditTimeFilter.ALL_TIME: "all",
        }
        return _map[self]


class RedditThingType(str, Enum):
    """The type of a Reddit 'thing'.

    Typically used as a prefix for fullnames, e.g. t1_1234567890
    is the fullname of a comment with id 1234567890
    """

    COMMENT = "t1"
    ACCOUNT = "t2"
    LINK = "t3"
    MESSAGE = "t4"
    SUBREDDIT = "t5"
    AWARD = "t6"
