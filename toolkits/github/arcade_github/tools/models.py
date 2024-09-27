from enum import Enum


class RepoType(Enum):
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


class RepoSortDirection(str, Enum):
    """
    The order to sort by when listing organization repositories.
    Default is asc.
    """

    ASC = "asc"
    DESC = "desc"
