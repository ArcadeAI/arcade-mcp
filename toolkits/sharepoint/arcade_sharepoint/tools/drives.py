from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from kiota_abstractions.base_request_configuration import RequestConfiguration

from arcade_sharepoint.client import get_client
from arcade_sharepoint.constants import DRIVE_PROPS
from arcade_sharepoint.serializers import serialize_drive
from arcade_sharepoint.utils import build_offset_pagination, is_site_id, is_drive_id


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def list_site_drives(
    context: ToolContext,
    site_id: Annotated[str, "The SharePoint site ID to get drives from."],
    limit: Annotated[
        int,
        "The maximum number of drives to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The document libraries/drives in the SharePoint site."]:
    """Lists all document libraries (drives) in a specific SharePoint site."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    if not is_site_id(site_id):
        return {
            "error": f"Invalid site ID format: {site_id}",
            "drives": [],
            "count": 0,
        }

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "skip": offset,
            "select": ",".join(DRIVE_PROPS),
        }
    )

    try:
        response = await client.sites.by_site_id(site_id).drives.get(request_configuration=config)
        drives = [serialize_drive(drive) for drive in response.value]
        
        # Check if there are more results
        has_more = len(response.value) == limit
        pagination = build_offset_pagination(drives, limit, offset, has_more)

        return {
            "drives": drives,
            "count": len(drives),
            "site_id": site_id,
            "pagination": pagination,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve drives for site {site_id}: {str(e)}",
            "drives": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_site_default_drive(
    context: ToolContext,
    site_id: Annotated[str, "The SharePoint site ID to get the default drive from."],
) -> Annotated[dict, "The default document library/drive for the SharePoint site."]:
    """Gets the default document library (drive) for a SharePoint site."""
    client = get_client(context.get_auth_token_or_empty())

    if not is_site_id(site_id):
        return {
            "error": f"Invalid site ID format: {site_id}",
            "drive": None,
        }

    config = RequestConfiguration(
        query_parameters={
            "select": ",".join(DRIVE_PROPS),
        }
    )

    try:
        drive = await client.sites.by_site_id(site_id).drive.get(request_configuration=config)
        
        return {
            "drive": serialize_drive(drive),
            "site_id": site_id,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve default drive for site {site_id}: {str(e)}",
            "drive": None,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_drive(
    context: ToolContext,
    drive_id: Annotated[str, "The drive ID to retrieve information for."],
) -> Annotated[dict, "The drive/document library information."]:
    """Gets information about a specific drive/document library by its ID."""
    client = get_client(context.get_auth_token_or_empty())

    if not is_drive_id(drive_id):
        return {
            "error": f"Invalid drive ID format: {drive_id}",
            "drive": None,
        }

    config = RequestConfiguration(
        query_parameters={
            "select": ",".join(DRIVE_PROPS),
        }
    )

    try:
        drive = await client.drives.by_drive_id(drive_id).get(request_configuration=config)
        
        return {
            "drive": serialize_drive(drive),
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve drive {drive_id}: {str(e)}",
            "drive": None,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def get_user_drives(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of drives to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The drives accessible to the current user."]:
    """Lists all drives accessible to the current user across all SharePoint sites."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "skip": offset,
            "select": ",".join(DRIVE_PROPS),
        }
    )

    try:
        response = await client.drives.get(request_configuration=config)
        drives = [serialize_drive(drive) for drive in response.value]
        
        # Check if there are more results
        has_more = len(response.value) == limit
        pagination = build_offset_pagination(drives, limit, offset, has_more)

        return {
            "drives": drives,
            "count": len(drives),
            "pagination": pagination,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve user drives: {str(e)}",
            "drives": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_drives(
    context: ToolContext,
    search_term: Annotated[str, "The search term to find drives by name or description."],
    site_id: Annotated[str | None, "Optional site ID to limit search to a specific site."] = None,
    limit: Annotated[
        int,
        "The maximum number of drives to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The drives matching the search criteria."]:
    """Searches for drives/document libraries by name or description."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "select": ",".join(DRIVE_PROPS),
        }
    )

    drives = []
    error_msg = None

    try:
        if site_id and is_site_id(site_id):
            # Search within a specific site
            response = await client.sites.by_site_id(site_id).drives.get(request_configuration=config)
            all_drives = response.value
        else:
            # Search across all accessible drives
            response = await client.drives.get(request_configuration=config)
            all_drives = response.value

        # Filter drives by search term
        for drive in all_drives:
            drive_name = getattr(drive, 'name', '').lower()
            drive_description = getattr(drive, 'description', '').lower()
            search_lower = search_term.lower()
            
            if (search_lower in drive_name or 
                search_lower in drive_description or
                drive_name in search_lower):
                drives.append(serialize_drive(drive))
                
                if len(drives) >= limit:
                    break

    except Exception as e:
        error_msg = f"Failed to search drives: {str(e)}"

    result = {
        "drives": drives,
        "count": len(drives),
        "search_term": search_term,
    }
    
    if site_id:
        result["site_id"] = site_id
        
    if error_msg:
        result["error"] = error_msg

    return result 