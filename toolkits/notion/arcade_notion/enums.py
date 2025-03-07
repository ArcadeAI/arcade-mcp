from enum import Enum


class SortDirection(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class ObjectType(str, Enum):
    PAGE = "page"
    DATABASE = "database"
