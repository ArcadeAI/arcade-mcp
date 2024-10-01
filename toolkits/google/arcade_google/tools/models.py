from enum import Enum


# Utils for Google Drive tools
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

    CREATED_TIME = "createdTime"  # When the file was created (ascending)
    CREATED_TIME_DESC = "createdTime desc"  # When the file was created (descending)
    FOLDER = "folder"  # The folder ID, sorted using alphabetical ordering (ascending)
    FOLDER_DESC = "folder desc"  # The folder ID, sorted using alphabetical ordering (descending)
    MODIFIED_BY_ME_TIME = (
        "modifiedByMeTime"  # The last time the file was modified by the user (ascending)
    )
    MODIFIED_BY_ME_TIME_DESC = (
        "modifiedByMeTime desc"  # The last time the file was modified by the user (descending)
    )
    MODIFIED_TIME = "modifiedTime"  # The last time the file was modified by anyone (ascending)
    MODIFIED_TIME_DESC = (
        "modifiedTime desc"  # The last time the file was modified by anyone (descending)
    )
    NAME = "name"  # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (ascending)
    NAME_DESC = "name desc"  # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (descending)
    NAME_NATURAL = "name_natural"  # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (ascending)
    NAME_NATURAL_DESC = "name_natural desc"  # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (descending)
    QUOTA_BYTES_USED = (
        "quotaBytesUsed"  # The number of storage quota bytes used by the file (ascending)
    )
    QUOTA_BYTES_USED_DESC = (
        "quotaBytesUsed desc"  # The number of storage quota bytes used by the file (descending)
    )
    RECENCY = "recency"  # The most recent timestamp from the file's date-time fields (ascending)
    RECENCY_DESC = (
        "recency desc"  # The most recent timestamp from the file's date-time fields (descending)
    )
    SHARED_WITH_ME_TIME = (
        "sharedWithMeTime"  # When the file was shared with the user, if applicable (ascending)
    )
    SHARED_WITH_ME_TIME_DESC = "sharedWithMeTime desc"  # When the file was shared with the user, if applicable (descending)
    STARRED = "starred"  # Whether the user has starred the file (ascending)
    STARRED_DESC = "starred desc"  # Whether the user has starred the file (descending)
    VIEWED_BY_ME_TIME = (
        "viewedByMeTime"  # The last time the file was viewed by the user (ascending)
    )
    VIEWED_BY_ME_TIME_DESC = (
        "viewedByMeTime desc"  # The last time the file was viewed by the user (descending)
    )
