"""SharePoint toolkit for Arcade.ai

This toolkit provides retrieval-only tools for accessing SharePoint content including:
- Sites and site collections
- Document libraries and drives 
- Files and folders
- Lists and list items
- Comprehensive search functionality

All tools require Microsoft Graph authentication with appropriate SharePoint permissions.
"""

from arcade_sharepoint.tools import sites, drives, documents, search

# Import all individual tool functions for direct access
from arcade_sharepoint.tools import (
    # Sites
    list_sites,
    get_site,
    search_sites,
    get_followed_sites,
    # Drives
    list_site_drives,
    get_site_default_drive,
    get_drive,
    get_user_drives,
    search_drives,
    # Documents
    list_drive_items,
    get_drive_item,
    search_drive_items,
    get_recent_files,
    get_file_versions,
    list_all_drive_items,
    list_all_files,
    # Search
    search_sharepoint,
    search_documents,
    search_by_author,
    search_recent_content,
    comprehensive_document_search,
)

__all__ = [
    # Tool modules
    "sites",
    "drives", 
    "documents",
    "search",
    # Individual tool functions
    # Sites
    "list_sites",
    "get_site",
    "search_sites", 
    "get_followed_sites",
    # Drives
    "list_site_drives",
    "get_site_default_drive",
    "get_drive",
    "get_user_drives",
    "search_drives",
    # Documents
    "list_drive_items",
    "get_drive_item",
    "search_drive_items",
    "get_recent_files",
    "get_file_versions",
    "list_all_drive_items",
    "list_all_files",
    # Search
    "search_sharepoint",
    "search_documents",
    "search_by_author",
    "search_recent_content",
    "comprehensive_document_search",
]
