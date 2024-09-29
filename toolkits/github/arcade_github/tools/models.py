from enum import Enum


# Pull Request specific
class PRSortProperty(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    POPULARITY = "popularity"
    LONG_RUNNING = "long-running"


class ReviewCommentSortProperty(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    CREATED_AT = "created_at"


# Repo specific
class RepoType(str, Enum):
    """
    The types of repositories you want returned when listing organization repositories.
    Default is all repositories.
    """

    ALL = "all"
    PUBLIC = "public"
    PRIVATE = "private"
    FORKS = "forks"
    SOURCES = "sources"
    MEMBER = "member"


class RepoSortProperty(str, Enum):
    """
    The property to sort the results by when listing organization repositories.
    Default is created.
    """

    CREATED = "created"
    UPDATED = "updated"
    PUSHED = "pushed"
    FULL_NAME = "full_name"


class SortDirection(str, Enum):
    """
    The order to sort by when listing organization repositories.
    Default is asc.
    """

    ASC = "asc"
    DESC = "desc"


class RepoTimePeriod(str, Enum):
    """
    The time period to filter by when listing repository activities.
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class ActivityType(str, Enum):
    """
    The activity type to filter by when listing repository activities.
    """

    PUSH = "push"
    FORCE_PUSH = "force_push"
    BRANCH_CREATION = "branch_creation"
    BRANCH_DELETION = "branch_deletion"
    PR_MERGE = "pr_merge"
    MERGE_QUEUE_MERGE = "merge_queue_merge"
