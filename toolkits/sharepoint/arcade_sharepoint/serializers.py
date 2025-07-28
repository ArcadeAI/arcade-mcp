from typing import Any

from arcade_sharepoint.utils import format_file_size


def serialize_site(site: Any) -> dict[str, Any]:
    """Serialize a SharePoint site object."""
    return {
        "id": getattr(site, 'id', None),
        "name": getattr(site, 'name', None),
        "display_name": getattr(site, 'display_name', None),
        "description": getattr(site, 'description', None),
        "web_url": getattr(site, 'web_url', None),
        "created_date_time": str(getattr(site, 'created_date_time', None)) if getattr(site, 'created_date_time', None) else None,
        "last_modified_date_time": str(getattr(site, 'last_modified_date_time', None)) if getattr(site, 'last_modified_date_time', None) else None,
        "site_collection": serialize_site_collection(getattr(site, 'site_collection', None)) if getattr(site, 'site_collection', None) else None,
    }


def serialize_site_collection(site_collection: Any) -> dict[str, Any]:
    """Serialize a SharePoint site collection object."""
    if not site_collection:
        return None
    
    return {
        "hostname": getattr(site_collection, 'hostname', None),
        "data_location_code": getattr(site_collection, 'data_location_code', None),
        "root": serialize_root_info(getattr(site_collection, 'root', None)),
    }


def serialize_root_info(root: Any) -> dict[str, Any]:
    """Serialize root information."""
    if not root:
        return None
    
    return {
        "id": getattr(root, 'id', None),
        "web_url": getattr(root, 'web_url', None),
    }


def serialize_drive(drive: Any) -> dict[str, Any]:
    """Serialize a SharePoint drive object."""
    quota = getattr(drive, 'quota', None)
    
    return {
        "id": getattr(drive, 'id', None),
        "name": getattr(drive, 'name', None),
        "description": getattr(drive, 'description', None),
        "drive_type": getattr(drive, 'drive_type', None),
        "web_url": getattr(drive, 'web_url', None),
        "created_date_time": str(getattr(drive, 'created_date_time', None)) if getattr(drive, 'created_date_time', None) else None,
        "last_modified_date_time": str(getattr(drive, 'last_modified_date_time', None)) if getattr(drive, 'last_modified_date_time', None) else None,
        "quota": serialize_quota(quota) if quota else None,
        "owner": serialize_identity_set(getattr(drive, 'owner', None)),
    }


def serialize_quota(quota: Any) -> dict[str, Any]:
    """Serialize drive quota information."""
    if not quota:
        return None
    
    total = getattr(quota, 'total', 0)
    used = getattr(quota, 'used', 0)
    remaining = getattr(quota, 'remaining', 0)
    
    return {
        "total": total,
        "used": used,
        "remaining": remaining,
        "total_formatted": format_file_size(total) if total else "0 B",
        "used_formatted": format_file_size(used) if used else "0 B", 
        "remaining_formatted": format_file_size(remaining) if remaining else "0 B",
        "deleted": getattr(quota, 'deleted', 0),
        "state": getattr(quota, 'state', None),
    }


def serialize_drive_item(item: Any, include_content: bool = False) -> dict[str, Any]:
    """Serialize a SharePoint drive item (file or folder)."""
    size = getattr(item, 'size', 0)
    
    result = {
        "id": getattr(item, 'id', None),
        "name": getattr(item, 'name', None),
        "size": size,
        "size_formatted": format_file_size(size) if size else "0 B",
        "web_url": getattr(item, 'web_url', None),
        "created_date_time": str(getattr(item, 'created_date_time', None)) if getattr(item, 'created_date_time', None) else None,
        "last_modified_date_time": str(getattr(item, 'last_modified_date_time', None)) if getattr(item, 'last_modified_date_time', None) else None,
        "created_by": serialize_identity_set(getattr(item, 'created_by', None)),
        "last_modified_by": serialize_identity_set(getattr(item, 'last_modified_by', None)),
        "parent_reference": serialize_item_reference(getattr(item, 'parent_reference', None)),
        "file": serialize_file_facet(getattr(item, 'file', None)),
        "folder": serialize_folder_facet(getattr(item, 'folder', None)),
        "package": serialize_package_facet(getattr(item, 'package', None)),
    }
    
    # Add download URL if it's a file
    if hasattr(item, 'odata_additional_data') and '@microsoft.graph.downloadUrl' in getattr(item, 'odata_additional_data', {}):
        result["download_url"] = item.odata_additional_data['@microsoft.graph.downloadUrl']
    
    return result


def serialize_identity_set(identity_set: Any) -> dict[str, Any]:
    """Serialize an identity set (user information)."""
    if not identity_set:
        return None
    
    user = getattr(identity_set, 'user', None)
    application = getattr(identity_set, 'application', None)
    
    result = {}
    if user:
        result["user"] = {
            "id": getattr(user, 'id', None),
            "display_name": getattr(user, 'display_name', None),
            "email": getattr(user, 'email', None),
        }
    if application:
        result["application"] = {
            "id": getattr(application, 'id', None),
            "display_name": getattr(application, 'display_name', None),
        }
    
    return result if result else None


def serialize_item_reference(reference: Any) -> dict[str, Any]:
    """Serialize an item reference."""
    if not reference:
        return None
    
    return {
        "drive_id": getattr(reference, 'drive_id', None),
        "drive_type": getattr(reference, 'drive_type', None),
        "id": getattr(reference, 'id', None),
        "name": getattr(reference, 'name', None),
        "path": getattr(reference, 'path', None),
        "site_id": getattr(reference, 'site_id', None),
    }


def serialize_file_facet(file_facet: Any) -> dict[str, Any]:
    """Serialize file-specific information."""
    if not file_facet:
        return None
    
    return {
        "mime_type": getattr(file_facet, 'mime_type', None),
        "hashes": serialize_hashes(getattr(file_facet, 'hashes', None)),
    }


def serialize_folder_facet(folder_facet: Any) -> dict[str, Any]:
    """Serialize folder-specific information."""
    if not folder_facet:
        return None
    
    return {
        "child_count": getattr(folder_facet, 'child_count', 0),
    }


def serialize_package_facet(package_facet: Any) -> dict[str, Any]:
    """Serialize package-specific information."""
    if not package_facet:
        return None
    
    return {
        "type": getattr(package_facet, 'type', None),
    }


def serialize_hashes(hashes: Any) -> dict[str, Any]:
    """Serialize file hashes."""
    if not hashes:
        return None
    
    return {
        "crc32_hash": getattr(hashes, 'crc32_hash', None),
        "sha1_hash": getattr(hashes, 'sha1_hash', None),
        "sha256_hash": getattr(hashes, 'sha256_hash', None),
        "quick_xor_hash": getattr(hashes, 'quick_xor_hash', None),
    }


def serialize_list(sharepoint_list: Any) -> dict[str, Any]:
    """Serialize a SharePoint list."""
    return {
        "id": getattr(sharepoint_list, 'id', None),
        "name": getattr(sharepoint_list, 'name', None),
        "display_name": getattr(sharepoint_list, 'display_name', None),
        "description": getattr(sharepoint_list, 'description', None),
        "web_url": getattr(sharepoint_list, 'web_url', None),
        "created_date_time": str(getattr(sharepoint_list, 'created_date_time', None)) if getattr(sharepoint_list, 'created_date_time', None) else None,
        "last_modified_date_time": str(getattr(sharepoint_list, 'last_modified_date_time', None)) if getattr(sharepoint_list, 'last_modified_date_time', None) else None,
        "list": serialize_list_info(getattr(sharepoint_list, 'list', None)),
    }


def serialize_list_info(list_info: Any) -> dict[str, Any]:
    """Serialize SharePoint list information."""
    if not list_info:
        return None
    
    return {
        "hidden": getattr(list_info, 'hidden', None),
        "template": getattr(list_info, 'template', None),
    }


def serialize_list_item(item: Any) -> dict[str, Any]:
    """Serialize a SharePoint list item."""
    return {
        "id": getattr(item, 'id', None),
        "web_url": getattr(item, 'web_url', None),
        "created_date_time": str(getattr(item, 'created_date_time', None)) if getattr(item, 'created_date_time', None) else None,
        "last_modified_date_time": str(getattr(item, 'last_modified_date_time', None)) if getattr(item, 'last_modified_date_time', None) else None,
        "created_by": serialize_identity_set(getattr(item, 'created_by', None)),
        "last_modified_by": serialize_identity_set(getattr(item, 'last_modified_by', None)),
        "parent_reference": serialize_item_reference(getattr(item, 'parent_reference', None)),
        "fields": serialize_fields(getattr(item, 'fields', None)),
    }


def serialize_fields(fields: Any) -> dict[str, Any]:
    """Serialize SharePoint list item fields."""
    if not fields:
        return None
    
    # Fields contain dynamic properties, so we'll serialize the additional data
    if hasattr(fields, 'additional_data'):
        return getattr(fields, 'additional_data', {})
    elif hasattr(fields, 'odata_additional_data'):
        return getattr(fields, 'odata_additional_data', {})
    
    return {}


def serialize_search_hit(hit: Any) -> dict[str, Any]:
    """Serialize a search result hit."""
    resource = getattr(hit, 'resource', None)
    
    result = {
        "hit_id": getattr(hit, 'hit_id', None),
        "rank": getattr(hit, 'rank', None),
        "summary": getattr(hit, 'summary', None),
    }
    
    if resource:
        # Determine resource type and serialize accordingly
        odata_type = getattr(resource, 'odata_type', '')
        
        if 'driveItem' in odata_type:
            result["resource"] = serialize_drive_item(resource)
            result["resource_type"] = "driveItem"
        elif 'listItem' in odata_type:
            result["resource"] = serialize_list_item(resource)
            result["resource_type"] = "listItem"
        elif 'site' in odata_type:
            result["resource"] = serialize_site(resource)
            result["resource_type"] = "site"
        else:
            # Generic resource serialization
            result["resource"] = {
                "id": getattr(resource, 'id', None),
                "name": getattr(resource, 'name', None),
                "web_url": getattr(resource, 'web_url', None),
            }
            result["resource_type"] = "unknown"
    
    return result


def short_version(item: dict) -> dict:
    """Return a shortened version of an item with key information only."""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "web_url": item.get("web_url"),
        "last_modified": item.get("last_modified_date_time"),
    } 