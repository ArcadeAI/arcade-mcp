from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from kiota_abstractions.base_request_configuration import RequestConfiguration

from arcade_sharepoint.client import get_client
from arcade_sharepoint.constants import DRIVE_ITEM_PROPS
from arcade_sharepoint.serializers import serialize_drive_item
from arcade_sharepoint.utils import build_offset_pagination, is_drive_id, validate_datetime_range


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def list_drive_items(
    context: ToolContext,
    drive_id: Annotated[str, "The drive ID to list items from."],
    folder_path: Annotated[str, "The folder path within the drive. Use '/' or 'root' for root folder."] = "root",
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
    item_type: Annotated[str | None, "Filter by item type: 'file', 'folder', or None for both."] = None,
) -> Annotated[dict, "The files and folders in the specified drive location."]:
    """Lists files and folders in a SharePoint drive/document library."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    if not is_drive_id(drive_id):
        return {
            "error": f"Invalid drive ID format: {drive_id}",
            "items": [],
            "count": 0,
        }

    # Clean up folder path
    if folder_path in ["/", "", "root"]:
        folder_path = "root"
    elif folder_path.startswith("/"):
        folder_path = folder_path[1:]

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "skip": offset,
            "select": ",".join(DRIVE_ITEM_PROPS),
            "orderby": "lastModifiedDateTime desc",
        }
    )

    try:
        if folder_path == "root":
            response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").children.get(request_configuration=config)
        else:
            response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(folder_path).children.get(request_configuration=config)
        
        items = []
        for item in response.value:
            # Filter by item type if specified
            if item_type:
                has_file = hasattr(item, 'file') and getattr(item, 'file', None) is not None
                has_folder = hasattr(item, 'folder') and getattr(item, 'folder', None) is not None
                
                if item_type.lower() == "file" and not has_file:
                    continue
                elif item_type.lower() == "folder" and not has_folder:
                    continue
            
            items.append(serialize_drive_item(item))
        
        # Check if there are more results
        has_more = len(response.value) == limit
        pagination = build_offset_pagination(items, limit, offset, has_more)

        return {
            "items": items,
            "count": len(items),
            "drive_id": drive_id,
            "folder_path": folder_path,
            "pagination": pagination,
        }
    except Exception as e:
        return {
            "error": f"Failed to list items in drive {drive_id}: {str(e)}",
            "items": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_drive_item(
    context: ToolContext,
    drive_id: Annotated[str, "The drive ID containing the item."],
    item_id_or_path: Annotated[str, "The item ID or path within the drive."],
) -> Annotated[dict, "The file or folder information."]:
    """Gets information about a specific file or folder in a SharePoint drive."""
    client = get_client(context.get_auth_token_or_empty())

    if not is_drive_id(drive_id):
        return {
            "error": f"Invalid drive ID format: {drive_id}",
            "item": None,
        }

    config = RequestConfiguration(
        query_parameters={
            "select": ",".join(DRIVE_ITEM_PROPS),
        }
    )

    try:
        # Try as item ID first, then as path
        try:
            item = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(item_id_or_path).get(request_configuration=config)
        except Exception:
            # If ID lookup fails, try as path
            if item_id_or_path.startswith("/"):
                item_id_or_path = item_id_or_path[1:]
            
            item = await client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").get_item_with_path(item_id_or_path).get(request_configuration=config)
        
        return {
            "item": serialize_drive_item(item),
            "drive_id": drive_id,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve item {item_id_or_path} from drive {drive_id}: {str(e)}",
            "item": None,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_drive_items(
    context: ToolContext,
    drive_id: Annotated[str, "The drive ID to search within."],
    search_term: Annotated[str, "The search term to find files and folders."],
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 25, max is 50.",
    ] = 25,
    item_type: Annotated[str | None, "Filter by item type: 'file', 'folder', or None for both."] = None,
) -> Annotated[dict, "The files and folders matching the search criteria."]:
    """Searches for files and folders within a specific SharePoint drive."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    if not is_drive_id(drive_id):
        return {
            "error": f"Invalid drive ID format: {drive_id}",
            "items": [],
            "count": 0,
        }

    config = RequestConfiguration(
        query_parameters={
            "q": search_term,
            "top": limit,
            "select": ",".join(DRIVE_ITEM_PROPS),
        }
    )

    try:
        response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").search_with_q(search_term).get(request_configuration=config)
        
        items = []
        for item in response.value:
            # Filter by item type if specified
            if item_type:
                has_file = hasattr(item, 'file') and getattr(item, 'file', None) is not None
                has_folder = hasattr(item, 'folder') and getattr(item, 'folder', None) is not None
                
                if item_type.lower() == "file" and not has_file:
                    continue
                elif item_type.lower() == "folder" and not has_folder:
                    continue
            
            items.append(serialize_drive_item(item))

        return {
            "items": items,
            "count": len(items),
            "drive_id": drive_id,
            "search_term": search_term,
        }
    except Exception as e:
        return {
            "error": f"Failed to search items in drive {drive_id}: {str(e)}",
            "items": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_recent_files(
    context: ToolContext,
    drive_id: Annotated[str | None, "Optional drive ID to limit to a specific drive."] = None,
    limit: Annotated[
        int,
        "The maximum number of files to return. Defaults to 25, max is 50.",
    ] = 25,
    days: Annotated[int, "Number of days back to look for recent files. Defaults to 7."] = 7,
) -> Annotated[dict, "The recently modified files."]:
    """Gets recently modified files from SharePoint drives."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    # Calculate the date threshold
    from datetime import datetime, timedelta, timezone
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    threshold_str = threshold_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "select": ",".join(DRIVE_ITEM_PROPS),
            "orderby": "lastModifiedDateTime desc",
            "filter": f"lastModifiedDateTime gt {threshold_str}",
        }
    )

    try:
        if drive_id and is_drive_id(drive_id):
            # Get recent files from specific drive
            response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").children.get(request_configuration=config)
            context_info = {"drive_id": drive_id}
        else:
            # Get recent files from user's default drive
            response = await client.me.drive.items.by_drive_item_id("root").children.get(request_configuration=config)
            context_info = {}

        items = []
        for item in response.value:
            # Only include files, not folders
            if hasattr(item, 'file') and getattr(item, 'file', None) is not None:
                items.append(serialize_drive_item(item))

        result = {
            "items": items,
            "count": len(items),
            "days": days,
        }
        result.update(context_info)
        
        return result
    except Exception as e:
        return {
            "error": f"Failed to retrieve recent files: {str(e)}",
            "items": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_file_versions(
    context: ToolContext,
    drive_id: Annotated[str, "The drive ID containing the file."],
    file_id: Annotated[str, "The file ID to get versions for."],
    limit: Annotated[
        int,
        "The maximum number of versions to return. Defaults to 10, max is 25.",
    ] = 10,
) -> Annotated[dict, "The file version history."]:
    """Gets version history for a specific file in SharePoint."""
    limit = min(25, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    if not is_drive_id(drive_id):
        return {
            "error": f"Invalid drive ID format: {drive_id}",
            "versions": [],
            "count": 0,
        }

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "orderby": "lastModifiedDateTime desc",
        }
    )

    try:
        response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(file_id).versions.get(request_configuration=config)
        
        versions = []
        for version in response.value:
            version_info = {
                "id": getattr(version, 'id', None),
                "last_modified_date_time": str(getattr(version, 'last_modified_date_time', None)) if getattr(version, 'last_modified_date_time', None) else None,
                "last_modified_by": getattr(version, 'last_modified_by', None),
                "size": getattr(version, 'size', 0),
            }
            versions.append(version_info)

        return {
            "versions": versions,
            "count": len(versions),
            "drive_id": drive_id,
            "file_id": file_id,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve versions for file {file_id}: {str(e)}",
            "versions": [],
            "count": 0,
        } 

@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def list_all_drive_items(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of items to return per drive. Defaults to 10, max is 25.",
    ] = 10,
    item_type: Annotated[str | None, "Filter by item type: 'file', 'folder', or None for both."] = None,
    include_empty_drives: Annotated[bool, "Whether to include drives that have no items."] = False,
) -> Annotated[dict, "Files and folders from all accessible SharePoint drives."]:
    """Lists files and folders from all accessible SharePoint drives/document libraries."""
    limit = min(25, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())
    
    import logging
    logger = logging.getLogger(__name__)
    
    all_items = []
    drive_info = []
    total_files_found = 0
    
    try:
        # First, get all accessible drives
        drives_response = await client.drives.get()
        accessible_drives = drives_response.value if drives_response.value else []
        
        logger.info(f"Found {len(accessible_drives)} accessible drives")
        
        for drive in accessible_drives:
            drive_id = getattr(drive, 'id', None)
            drive_name = getattr(drive, 'name', 'Unknown Drive')
            drive_type = getattr(drive, 'drive_type', 'Unknown')
            
            if not drive_id:
                continue
                
            logger.info(f"Processing drive: {drive_name} (ID: {drive_id}, Type: {drive_type})")
            
            # Get items from this drive
            config = RequestConfiguration(
                query_parameters={
                    "top": limit,
                    "select": ",".join(DRIVE_ITEM_PROPS),
                    "orderby": "lastModifiedDateTime desc",
                }
            )
            
            try:
                # List items from the root of this drive
                items_response = await client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").children.get(request_configuration=config)
                
                drive_items = []
                if items_response.value:
                    for item in items_response.value:
                        # Filter by item type if specified
                        if item_type:
                            has_file = hasattr(item, 'file') and getattr(item, 'file', None) is not None
                            has_folder = hasattr(item, 'folder') and getattr(item, 'folder', None) is not None
                            
                            if item_type.lower() == "file" and not has_file:
                                continue
                            elif item_type.lower() == "folder" and not has_folder:
                                continue
                        
                        serialized_item = serialize_drive_item(item)
                        # Add drive context to each item
                        serialized_item["drive_info"] = {
                            "drive_id": drive_id,
                            "drive_name": drive_name,
                            "drive_type": drive_type
                        }
                        drive_items.append(serialized_item)
                
                # Add drive info
                drive_summary = {
                    "drive_id": drive_id,
                    "drive_name": drive_name,
                    "drive_type": drive_type,
                    "item_count": len(drive_items),
                    "items": drive_items
                }
                
                if drive_items or include_empty_drives:
                    drive_info.append(drive_summary)
                    all_items.extend(drive_items)
                    total_files_found += len(drive_items)
                    
                logger.info(f"  Found {len(drive_items)} items in {drive_name}")
                    
            except Exception as drive_error:
                logger.warning(f"Failed to access drive {drive_name}: {str(drive_error)}")
                # Add drive info even if we can't access it
                if include_empty_drives:
                    drive_info.append({
                        "drive_id": drive_id,
                        "drive_name": drive_name,
                        "drive_type": drive_type,
                        "item_count": 0,
                        "items": [],
                        "error": f"Access denied or error: {str(drive_error)}"
                    })
        
        return {
            "all_items": all_items,
            "total_items": total_files_found,
            "drives_checked": len(accessible_drives),
            "drives_with_items": len([d for d in drive_info if d.get("item_count", 0) > 0]),
            "drive_details": drive_info,
            "filter_applied": item_type,
            "limit_per_drive": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to list items from all drives: {str(e)}")
        return {
            "error": f"Failed to list items from all drives: {str(e)}",
            "all_items": [],
            "total_items": 0,
            "drives_checked": 0,
            "drives_with_items": 0,
            "drive_details": []
        } 

@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def list_all_files(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of files to return per drive. Defaults to 10, max is 25.",
    ] = 10,
    file_extensions: Annotated[
        str | None, 
        "Filter by file extensions (comma-separated, e.g., 'docx,pdf,txt'). Optional."
    ] = None,
) -> Annotated[dict, "All files from accessible SharePoint drives (excludes folders)."]:
    """Lists all files from all accessible SharePoint drives, excluding folders."""
    
    # Use the list_all_drive_items function but filter for files only
    result = await list_all_drive_items(
        context=context,
        limit=limit,
        item_type="file",
        include_empty_drives=False
    )
    
    if "error" in result:
        return result
    
    all_files = result.get("all_items", [])
    
    # Apply file extension filter if provided
    if file_extensions:
        extensions = [ext.strip().lower() for ext in file_extensions.split(",")]
        filtered_files = []
        
        for file_item in all_files:
            file_name = file_item.get("name", "").lower()
            if any(file_name.endswith(f".{ext}") for ext in extensions):
                filtered_files.append(file_item)
        
        all_files = filtered_files
    
    # Sort by last modified date (most recent first)
    all_files.sort(key=lambda x: x.get("last_modified_date_time", ""), reverse=True)
    
    # Extract just the essential info for each file
    simplified_files = []
    for file_item in all_files:
        drive_info = file_item.get("drive_info", {})
        simplified_files.append({
            "name": file_item.get("name"),
            "size": file_item.get("size_formatted", "Unknown"),
            "last_modified": file_item.get("last_modified_date_time"),
            "web_url": file_item.get("web_url"),
            "drive_name": drive_info.get("drive_name"),
            "drive_type": drive_info.get("drive_type"),
            "file_type": file_item.get("file", {}).get("mime_type") if file_item.get("file") else None
        })
    
    return {
        "files": simplified_files,
        "total_files": len(all_files),
        "drives_checked": result.get("drives_checked", 0),
        "drives_with_files": result.get("drives_with_items", 0),
        "file_extension_filter": file_extensions,
        "limit_per_drive": limit
    } 