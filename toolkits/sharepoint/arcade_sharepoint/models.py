from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class SharePointMatchType(Enum):
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"


class SharePointEntityType(Enum):
    SITE = "site"
    DRIVE = "drive"
    DRIVE_ITEM = "driveItem"
    LIST = "list" 
    LIST_ITEM = "listItem"


class DriveItemMatchType(Enum):
    BY_NAME = "by_name"
    BY_PATH = "by_path"
    BY_ID = "by_id"


class SiteMatchType(Enum):
    BY_URL = "by_url"
    BY_NAME = "by_name"
    BY_ID = "by_id"


class PaginationSentinel(ABC):
    """Base class for pagination sentinel classes."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    @abstractmethod
    def __call__(self, last_result: Any) -> bool | tuple[bool, list[Any]]:
        """Determine if the pagination should stop."""
        raise NotImplementedError


class FindSiteByNameSentinel(PaginationSentinel):
    def __init__(self, site_name: str, match_type: SharePointMatchType = SharePointMatchType.EXACT_MATCH):
        self.site_name = site_name.lower()
        self.match_type = match_type
        self.matches = []

    def __call__(self, last_result: Any) -> bool:
        for site in last_result:
            site_display_name = getattr(site, 'display_name', '').lower()
            site_name = getattr(site, 'name', '').lower()
            
            if self.match_type == SharePointMatchType.EXACT_MATCH:
                if self.site_name in [site_display_name, site_name]:
                    self.matches.append(site)
                    return True
            else:  # PARTIAL_MATCH
                if (self.site_name in site_display_name or 
                    self.site_name in site_name or
                    site_display_name in self.site_name or
                    site_name in self.site_name):
                    self.matches.append(site)

        return len(self.matches) > 0 and self.match_type == SharePointMatchType.EXACT_MATCH


class FindDriveItemSentinel(PaginationSentinel):
    def __init__(self, item_name: str, match_type: DriveItemMatchType = DriveItemMatchType.BY_NAME):
        self.item_name = item_name.lower()
        self.match_type = match_type
        self.matches = []

    def __call__(self, last_result: Any) -> bool:
        for item in last_result:
            item_name = getattr(item, 'name', '').lower()
            
            if self.match_type == DriveItemMatchType.BY_NAME:
                if self.item_name == item_name or self.item_name in item_name:
                    self.matches.append(item)
            elif self.match_type == DriveItemMatchType.BY_PATH:
                # For path matching, we'd need to check parent reference
                parent_ref = getattr(item, 'parent_reference', None)
                if parent_ref and hasattr(parent_ref, 'path'):
                    full_path = f"{parent_ref.path}/{item_name}".lower()
                    if self.item_name in full_path:
                        self.matches.append(item)

        return len(self.matches) > 0 