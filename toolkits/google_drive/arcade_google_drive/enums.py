from enum import Enum


class Corpora(str, Enum):
    """
    Bodies of items (files/documents) to which the query applies.
    Prefer 'user' or 'drive' to 'allDrives' for efficiency.
    By default, corpora is set to 'user'.
    """

    USER = "user"
    DOMAIN = "domain"
    DRIVE = "drive"
    ALL_DRIVES = "allDrives"


class OrderBy(str, Enum):
    """
    Sort keys for ordering files in Google Drive.
    Each key has both ascending and descending options.
    """

    CREATED_TIME = (
        # When the file was created (ascending)
        "createdTime"
    )
    CREATED_TIME_DESC = (
        # When the file was created (descending)
        "createdTime desc"
    )
    FOLDER = (
        # The folder ID, sorted using alphabetical ordering (ascending)
        "folder"
    )
    FOLDER_DESC = (
        # The folder ID, sorted using alphabetical ordering (descending)
        "folder desc"
    )
    MODIFIED_BY_ME_TIME = (
        # The last time the file was modified by the user (ascending)
        "modifiedByMeTime"
    )
    MODIFIED_BY_ME_TIME_DESC = (
        # The last time the file was modified by the user (descending)
        "modifiedByMeTime desc"
    )
    MODIFIED_TIME = (
        # The last time the file was modified by anyone (ascending)
        "modifiedTime"
    )
    MODIFIED_TIME_DESC = (
        # The last time the file was modified by anyone (descending)
        "modifiedTime desc"
    )
    NAME = (
        # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (ascending)
        "name"
    )
    NAME_DESC = (
        # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (descending)
        "name desc"
    )
    NAME_NATURAL = (
        # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (ascending)
        "name_natural"
    )
    NAME_NATURAL_DESC = (
        # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (descending)
        "name_natural desc"
    )
    QUOTA_BYTES_USED = (
        # The number of storage quota bytes used by the file (ascending)
        "quotaBytesUsed"
    )
    QUOTA_BYTES_USED_DESC = (
        # The number of storage quota bytes used by the file (descending)
        "quotaBytesUsed desc"
    )
    RECENCY = (
        # The most recent timestamp from the file's date-time fields (ascending)
        "recency"
    )
    RECENCY_DESC = (
        # The most recent timestamp from the file's date-time fields (descending)
        "recency desc"
    )
    SHARED_WITH_ME_TIME = (
        # When the file was shared with the user, if applicable (ascending)
        "sharedWithMeTime"
    )
    SHARED_WITH_ME_TIME_DESC = (
        # When the file was shared with the user, if applicable (descending)
        "sharedWithMeTime desc"
    )
    STARRED = (
        # Whether the user has starred the file (ascending)
        "starred"
    )
    STARRED_DESC = (
        # Whether the user has starred the file (descending)
        "starred desc"
    )
    VIEWED_BY_ME_TIME = (
        # The last time the file was viewed by the user (ascending)
        "viewedByMeTime"
    )
    VIEWED_BY_ME_TIME_DESC = (
        # The last time the file was viewed by the user (descending)
        "viewedByMeTime desc"
    )


class DocumentFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    GOOGLE_API_JSON = "google_api_json"
