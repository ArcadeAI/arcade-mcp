from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from kiota_abstractions.base_request_configuration import RequestConfiguration

from arcade_sharepoint.client import get_client
from arcade_sharepoint.constants import SITE_PROPS
from arcade_sharepoint.serializers import serialize_site
from arcade_sharepoint.utils import build_offset_pagination, is_site_id, is_sharepoint_url, extract_site_info_from_url


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Sites.ReadWrite.All"]))
async def list_sites(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of sites to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The SharePoint sites available to the user."]:
    """Lists SharePoint sites available to the current user."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "skip": offset,
            "select": ",".join(SITE_PROPS),
            "orderby": "lastModifiedDateTime desc",
        }
    )

    response = await client.sites.get(request_configuration=config)
    sites = [serialize_site(site) for site in response.value]
    
    # Check if there are more results
    has_more = len(response.value) == limit
    pagination = build_offset_pagination(sites, limit, offset, has_more)

    return {
        "sites": sites,
        "count": len(sites),
        "pagination": pagination,
    }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Sites.ReadWrite.All"]))
async def get_site(
    context: ToolContext,
    site_identifier: Annotated[str, "Site ID, SharePoint URL, or site name to search for."],
) -> Annotated[dict, "The SharePoint site information."]:
    """Gets information about a specific SharePoint site by ID, URL, or name."""
    client = get_client(context.get_auth_token_or_empty())
    
    config = RequestConfiguration(
        query_parameters={
            "select": ",".join(SITE_PROPS),
        }
    )

    # Try different approaches based on the identifier type
    site = None
    
    if is_site_id(site_identifier):
        # Direct site ID lookup
        try:
            site = await client.sites.by_site_id(site_identifier).get(request_configuration=config)
        except Exception:
            pass
    
    elif is_sharepoint_url(site_identifier):
        # URL-based lookup
        try:
            site_info = extract_site_info_from_url(site_identifier)
            hostname = site_info.get('host', '')
            site_path = site_info.get('relative_path', '')
            
            if hostname and 'site_collection' in site_info:
                site_collection = site_info['site_collection']
                site = await client.sites.by_hostname_with_site_path(hostname, f"/sites/{site_collection}").get(request_configuration=config)
        except Exception:
            pass
    
    # If direct lookup failed or identifier is a name, try searching
    if not site:
        search_config = RequestConfiguration(
            query_parameters={
                "search": f'"{site_identifier}"',
                "select": ",".join(SITE_PROPS),
                "top": 10,
            }
        )
        
        try:
            search_response = await client.sites.get(request_configuration=search_config)
            
            if search_response.value:
                # Return the first match (most relevant)
                site = search_response.value[0]
        except Exception:
            pass
    
    if not site:
        return {
            "error": f"No site found with identifier: {site_identifier}",
            "site": None,
        }

    return {
        "site": serialize_site(site),
    }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Sites.ReadWrite.All"]))
async def search_sites(
    context: ToolContext,
    search_term: Annotated[str, "The search term to find sites by name or description."],
    limit: Annotated[
        int,
        "The maximum number of sites to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The SharePoint sites matching the search criteria."]:
    """Searches for SharePoint sites by name or description."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    config = RequestConfiguration(
        query_parameters={
            "search": f'"{search_term}"',
            "select": ",".join(SITE_PROPS),
            "top": limit,
            "orderby": "lastModifiedDateTime desc",
        }
    )

    response = await client.sites.get(request_configuration=config)
    sites = [serialize_site(site) for site in response.value]

    return {
        "sites": sites,
        "count": len(sites),
        "search_term": search_term,
    }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Sites.ReadWrite.All"]))
async def get_followed_sites(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of sites to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The SharePoint sites followed by the current user."]:
    """Gets SharePoint sites that are followed by the current user."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    config = RequestConfiguration(
        query_parameters={
            "top": limit,
            "select": ",".join(SITE_PROPS),
            "orderby": "lastModifiedDateTime desc",
        }
    )

    try:
        response = await client.me.followed_sites.get(request_configuration=config)
        sites = [serialize_site(site) for site in response.value]

        return {
            "sites": sites,
            "count": len(sites),
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve followed sites: {str(e)}",
            "sites": [],
            "count": 0,
        } 