from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from msgraph_beta.generated.models.entity_type import EntityType
from msgraph_beta.generated.models.search_query import SearchQuery
from msgraph_beta.generated.models.search_request import SearchRequest
from msgraph_beta.generated.search.query.query_post_request_body import QueryPostRequestBody

from arcade_sharepoint.client import get_client
from arcade_sharepoint.serializers import serialize_search_hit
from arcade_sharepoint.utils import build_offset_pagination


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_sharepoint(
    context: ToolContext,
    search_term: Annotated[str, "The search term to find content across SharePoint."],
    entity_types: Annotated[
        list[str] | None, 
        "Types of content to search: 'driveItem', 'listItem', 'site', 'list'. Default is all types."
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of results to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The search results from SharePoint."]:
    """Searches for content across all SharePoint sites, documents, and lists."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    # Map string entity types to EntityType enums
    entity_type_mapping = {
        "driveitem": EntityType.DriveItem,
        "listitem": EntityType.ListItem,
        "site": EntityType.Site,
        "list": EntityType.List_,
    }

    # Default to all supported types if none specified
    if not entity_types:
        search_entity_types = [EntityType.DriveItem, EntityType.ListItem, EntityType.Site, EntityType.List_]
    else:
        search_entity_types = []
        for entity_type in entity_types:
            normalized_type = entity_type.lower()
            if normalized_type in entity_type_mapping:
                search_entity_types.append(entity_type_mapping[normalized_type])

    if not search_entity_types:
        return {
            "error": "No valid entity types provided. Use: 'driveItem', 'listItem', 'site', 'list'",
            "results": [],
            "count": 0,
        }

    request_body = QueryPostRequestBody(
        requests=[
            SearchRequest(
                entity_types=search_entity_types,
                query=SearchQuery(query_string=search_term),
                from_=offset,
                size=limit,
            )
        ]
    )

    try:
        response = await client.search.query.post(request_body)
        
        if not response.value or not response.value[0].hits_containers:
            return {
                "results": [],
                "count": 0,
                "search_term": search_term,
                "entity_types": entity_types or ["all"],
            }

        search_hits = response.value[0].hits_containers[0].hits
        results = [serialize_search_hit(hit) for hit in search_hits]
        more_results = response.value[0].hits_containers[0].more_results_available
        pagination = build_offset_pagination(results, limit, offset, more_results)

        return {
            "results": results,
            "count": len(results),
            "search_term": search_term,
            "entity_types": entity_types or ["all"],
            "pagination": pagination,
        }
    except Exception as e:
        return {
            "error": f"Failed to search SharePoint: {str(e)}",
            "results": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_documents(
    context: ToolContext,
    search_term: Annotated[str, "The search term to find documents and files."],
    file_type: Annotated[str | None, "Filter by file type (e.g., 'pdf', 'docx', 'xlsx'). Optional."] = None,
    limit: Annotated[
        int,
        "The maximum number of documents to return. Defaults to 25, max is 50.",
    ] = 25,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The documents matching the search criteria."]:
    """Searches specifically for documents and files across SharePoint."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    # Build query string with file type filter if provided
    query_string = search_term
    if file_type:
        query_string += f" filetype:{file_type.lower()}"

    # Add debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Searching for documents with query: '{query_string}', limit: {limit}, offset: {offset}")

    request_body = QueryPostRequestBody(
        requests=[
            SearchRequest(
                entity_types=[EntityType.DriveItem],
                query=SearchQuery(query_string=query_string),
                from_=offset,
                size=limit,
            )
        ]
    )

    try:
        response = await client.search.query.post(request_body)
        
        # Debug logging
        logger.info(f"Search response received: {response}")
        
        if not response.value or not response.value[0].hits_containers:
            logger.warning("No hits containers found in search response")
            return {
                "documents": [],
                "count": 0,
                "search_term": search_term,
                "file_type": file_type,
                "debug_info": {
                    "query_string": query_string,
                    "response_structure": "No hits containers"
                }
            }

        hits_container = response.value[0].hits_containers[0]
        logger.info(f"Hits container found with {len(hits_container.hits) if hits_container.hits else 0} hits")
        
        if not hits_container.hits:
            logger.warning("No hits found in hits container")
            return {
                "documents": [],
                "count": 0,
                "search_term": search_term,
                "file_type": file_type,
                "debug_info": {
                    "query_string": query_string,
                    "hits_container_found": True,
                    "hits_count": 0
                }
            }

        search_hits = hits_container.hits
        
        # Filter for files only (not folders) and log details
        documents = []
        for i, hit in enumerate(search_hits):
            logger.info(f"Processing hit {i}: {hit}")
            result = serialize_search_hit(hit)
            logger.info(f"Serialized result {i}: {result}")
            
            # More permissive filtering - include if it looks like a document
            should_include = False
            
            if result.get("resource_type") == "driveItem":
                resource = result.get("resource", {})
                name = resource.get("name", "").lower()
                
                # Include if it has a file facet OR if the name suggests it's a document
                if resource.get("file"):
                    should_include = True
                    logger.info(f"Hit {i} included - has file facet")
                elif any(ext in name for ext in [".doc", ".pdf", ".txt", ".ppt", ".xls", ".odt", ".rtf"]):
                    should_include = True  
                    logger.info(f"Hit {i} included - has document extension")
                elif not resource.get("folder"):  # Not explicitly a folder
                    should_include = True
                    logger.info(f"Hit {i} included - not a folder")
                else:
                    logger.info(f"Hit {i} skipped - appears to be a folder")
                    
            elif result.get("resource_type") == "listItem":
                # Include list items that might be documents
                should_include = True
                logger.info(f"Hit {i} included - is a listItem")
                
            else:
                # Include other types that might be documents
                should_include = True
                logger.info(f"Hit {i} included - unknown resource type, being permissive")
            
            if should_include:
                documents.append(result)
                logger.info(f"Added document {i} to results")

        more_results = hits_container.more_results_available
        pagination = build_offset_pagination(documents, limit, offset, more_results)

        return {
            "documents": documents,
            "count": len(documents),
            "search_term": search_term,
            "file_type": file_type,
            "pagination": pagination,
            "debug_info": {
                "query_string": query_string,
                "total_hits": len(search_hits),
                "filtered_documents": len(documents),
                "more_results_available": more_results
            }
        }
    except Exception as e:
        logger.error(f"Search failed with error: {str(e)}")
        return {
            "error": f"Failed to search documents: {str(e)}",
            "documents": [],
            "count": 0,
            "debug_info": {
                "query_string": query_string,
                "error_details": str(e)
            }
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_by_author(
    context: ToolContext,
    author_name: Annotated[str, "The name of the author/creator to search for."],
    content_type: Annotated[str, "Type of content to search: 'documents', 'lists', or 'all'."] = "all",
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The content created or modified by the specified author."]:
    """Searches for SharePoint content created or modified by a specific author."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    # Build query string for author search
    query_string = f'author:"{author_name}" OR createdby:"{author_name}" OR modifiedby:"{author_name}"'

    # Determine entity types based on content_type
    if content_type.lower() == "documents":
        entity_types = [EntityType.DriveItem]
    elif content_type.lower() == "lists":
        entity_types = [EntityType.ListItem, EntityType.List]
    else:  # all
        entity_types = [EntityType.DriveItem, EntityType.ListItem, EntityType.List]

    request_body = QueryPostRequestBody(
        requests=[
            SearchRequest(
                entity_types=entity_types,
                query=SearchQuery(query_string=query_string),
                from_=0,
                size=limit,
            )
        ]
    )

    try:
        response = await client.search.query.post(request_body)
        
        if not response.value or not response.value[0].hits_containers:
            return {
                "results": [],
                "count": 0,
                "author_name": author_name,
                "content_type": content_type,
            }

        search_hits = response.value[0].hits_containers[0].hits
        results = [serialize_search_hit(hit) for hit in search_hits]

        return {
            "results": results,
            "count": len(results),
            "author_name": author_name,
            "content_type": content_type,
        }
    except Exception as e:
        return {
            "error": f"Failed to search by author: {str(e)}",
            "results": [],
            "count": 0,
        }


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def search_recent_content(
    context: ToolContext,
    days: Annotated[int, "Number of days back to search for recent content. Defaults to 7."] = 7,
    content_type: Annotated[str, "Type of content to search: 'documents', 'lists', or 'all'."] = "all",
    limit: Annotated[
        int,
        "The maximum number of items to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The recently created or modified content in SharePoint."]:
    """Searches for recently created or modified content in SharePoint."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    # Build query string for recent content
    query_string = f"lastmodifiedtime>={days}DaysAgo OR created>={days}DaysAgo"

    # Determine entity types based on content_type
    if content_type.lower() == "documents":
        entity_types = [EntityType.DriveItem]
    elif content_type.lower() == "lists":
        entity_types = [EntityType.ListItem, EntityType.List_]
    else:  # all
        entity_types = [EntityType.DriveItem, EntityType.ListItem, EntityType.List_]

    request_body = QueryPostRequestBody(
        requests=[
            SearchRequest(
                entity_types=entity_types,
                query=SearchQuery(query_string=query_string),
                from_=0,
                size=limit,
            )
        ]
    )

    try:
        response = await client.search.query.post(request_body)
        
        if not response.value or not response.value[0].hits_containers:
            return {
                "results": [],
                "count": 0,
                "days": days,
                "content_type": content_type,
            }

        search_hits = response.value[0].hits_containers[0].hits
        results = [serialize_search_hit(hit) for hit in search_hits]

        return {
            "results": results,
            "count": len(results),
            "days": days,
            "content_type": content_type,
        }
    except Exception as e:
        return {
            "error": f"Failed to search recent content: {str(e)}",
            "results": [],
            "count": 0,
        } 


@tool(requires_auth=OAuth2(id="madrigal-microsoft", scopes=["Sites.Read.All", "Files.Read.All"]))
async def comprehensive_document_search(
    context: ToolContext,
    search_term: Annotated[str, "The search term to find documents and files."],
    file_type: Annotated[str | None, "Filter by file type (e.g., 'pdf', 'docx', 'xlsx'). Optional."] = None,
    limit: Annotated[
        int,
        "The maximum number of documents to return. Defaults to 25, max is 50.",
    ] = 25,
) -> Annotated[dict, "The documents matching the search criteria using multiple search strategies."]:
    """Performs a comprehensive search for documents using multiple strategies to maximize results."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())
    
    import logging
    logger = logging.getLogger(__name__)
    
    all_documents = []
    search_strategies = []
    
    # Strategy 1: Original search approach
    query_string_1 = search_term
    if file_type:
        query_string_1 += f" filetype:{file_type.lower()}"
    
    strategy_1 = {
        "name": "DriveItem Search",
        "query": query_string_1,
        "entity_types": [EntityType.DriveItem]
    }
    search_strategies.append(strategy_1)
    
    # Strategy 2: Search all entity types
    strategy_2 = {
        "name": "All Entity Types Search", 
        "query": search_term,
        "entity_types": [EntityType.DriveItem, EntityType.ListItem, EntityType.Site, EntityType.List_]
    }
    search_strategies.append(strategy_2)
    
    # Strategy 3: Broader search with wildcards
    strategy_3 = {
        "name": "Wildcard Search",
        "query": f"*{search_term}*",
        "entity_types": [EntityType.DriveItem]
    }
    search_strategies.append(strategy_3)
    
    # Strategy 4: Title-specific search
    strategy_4 = {
        "name": "Title Search",
        "query": f"title:{search_term}",
        "entity_types": [EntityType.DriveItem]
    }
    search_strategies.append(strategy_4)
    
    for strategy in search_strategies:
        logger.info(f"Trying search strategy: {strategy['name']} with query: '{strategy['query']}'")
        
        request_body = QueryPostRequestBody(
            requests=[
                SearchRequest(
                    entity_types=strategy["entity_types"],
                    query=SearchQuery(query_string=strategy["query"]),
                    from_=0,
                    size=limit,
                )
            ]
        )
        
        try:
            response = await client.search.query.post(request_body)
            
            if response.value and response.value[0].hits_containers and response.value[0].hits_containers[0].hits:
                hits = response.value[0].hits_containers[0].hits
                logger.info(f"Strategy '{strategy['name']}' found {len(hits)} hits")
                
                for hit in hits:
                    result = serialize_search_hit(hit)
                    
                    # For all strategies, include both files and items that might be documents
                    if result.get("resource_type") == "driveItem":
                        resource = result.get("resource", {})
                        # Include if it has a file facet OR if it has a name that might be a document
                        if (resource.get("file") or 
                            (resource.get("name", "").lower().find(search_term.lower()) >= 0)):
                            
                            # Add strategy info to result
                            result["found_by_strategy"] = strategy["name"]
                            
                            # Avoid duplicates by checking if we already have this item
                            item_id = resource.get("id")
                            if item_id and not any(doc.get("resource", {}).get("id") == item_id for doc in all_documents):
                                all_documents.append(result)
                                
                    elif result.get("resource_type") == "listItem":
                        # Include list items that might be documents
                        resource = result.get("resource", {})
                        result["found_by_strategy"] = strategy["name"]
                        
                        # Avoid duplicates
                        item_id = resource.get("id")
                        if item_id and not any(doc.get("resource", {}).get("id") == item_id for doc in all_documents):
                            all_documents.append(result)
                
                # If we found documents with this strategy, log success
                if all_documents:
                    logger.info(f"Strategy '{strategy['name']}' contributed documents. Total found so far: {len(all_documents)}")
                    
            else:
                logger.info(f"Strategy '{strategy['name']}' found no results")
                
        except Exception as e:
            logger.warning(f"Strategy '{strategy['name']}' failed with error: {str(e)}")
            continue
    
    # Filter by file type if specified and not already filtered
    if file_type and all_documents:
        file_type_lower = file_type.lower()
        filtered_documents = []
        for doc in all_documents:
            resource = doc.get("resource", {})
            file_info = resource.get("file", {})
            name = resource.get("name", "").lower()
            
            # Check file extension or mime type
            if (name.endswith(f".{file_type_lower}") or 
                file_type_lower in name or
                file_type_lower in str(file_info.get("mimeType", "")).lower()):
                filtered_documents.append(doc)
        
        all_documents = filtered_documents
    
    # Limit results
    final_documents = all_documents[:limit]
    
    return {
        "documents": final_documents,
        "count": len(final_documents),
        "search_term": search_term,
        "file_type": file_type,
        "strategies_used": [s["name"] for s in search_strategies],
        "total_found_before_limit": len(all_documents),
        "debug_info": {
            "strategies_attempted": len(search_strategies),
            "final_document_count": len(final_documents)
        }
    } 