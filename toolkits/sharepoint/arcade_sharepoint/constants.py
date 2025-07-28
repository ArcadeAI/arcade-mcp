import enum
import os
from collections.abc import Callable


def enforce_greater_than_zero_int(key: str, value: str) -> int:
    if value.isdigit():
        int_value = int(value)
        if int_value > 0:
            return int_value
    error = f"Environment variable {key} must have a positive integer value greater than zero"
    raise ValueError(error)


def load_env_var(key: str, default: str | None = None, transform: Callable | None = None) -> str:
    if key not in os.environ:
        return default

    value = os.getenv(key, default)
    if not value:
        error = f"Environment variable {key} is not set"
        raise ValueError(error)

    if transform:
        value = transform(key, value)

    return value


ENV_VARS = {
    "SHAREPOINT_MAX_CONCURRENCY": load_env_var(
        "SHAREPOINT_MAX_CONCURRENCY", 3, enforce_greater_than_zero_int
    ),
    "SHAREPOINT_PAGINATION_TIMEOUT": load_env_var(
        "SHAREPOINT_PAGINATION_TIMEOUT", 30, enforce_greater_than_zero_int
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


class DatetimeField(enum.Enum):
    LAST_MODIFIED = "lastModifiedDateTime"
    CREATED = "createdDateTime"

    @property
    def order_by_clause(self) -> str:
        return "lastModifiedDateTime desc" if self == self.LAST_MODIFIED else "createdDateTime desc"


class DriveItemType(enum.Enum):
    FILE = "file"
    FOLDER = "folder"


class DocumentLibraryType(enum.Enum):
    DOCUMENT_LIBRARY = "documentLibrary"
    SITE_PAGES = "sitePages" 
    SITE_ASSETS = "siteAssets"


# SharePoint-specific properties to select
SITE_PROPS = [
    "id",
    "displayName", 
    "name",
    "webUrl",
    "description",
    "createdDateTime",
    "lastModifiedDateTime",
    "siteCollection",
]

DRIVE_PROPS = [
    "id",
    "name",
    "description", 
    "driveType",
    "webUrl",
    "createdDateTime",
    "lastModifiedDateTime",
    "quota",
]

DRIVE_ITEM_PROPS = [
    "id",
    "name",
    "size",
    "webUrl",
    "createdDateTime", 
    "lastModifiedDateTime",
    "createdBy",
    "lastModifiedBy",
    "parentReference",
    "file",
    "folder",
    "package",
]

LIST_PROPS = [
    "id",
    "name",
    "displayName",
    "description",
    "webUrl",
    "createdDateTime",
    "lastModifiedDateTime",
    "list",
]

LIST_ITEM_PROPS = [
    "id",
    "webUrl",
    "createdDateTime",
    "lastModifiedDateTime", 
    "createdBy",
    "lastModifiedBy",
    "parentReference",
    "fields",
] 