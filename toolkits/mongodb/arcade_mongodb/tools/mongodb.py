import json
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..database_engine import MAX_RECORDS_RETURNED, DatabaseEngine
from .utils import (
    _infer_schema_from_docs,
    _parse_json_list_parameter,
    _parse_json_parameter,
    _serialize_document,
)

# class UserStatus(str, Enum):
#     """User status enumeration."""

#     ACTIVE = "active"
#     INACTIVE = "inactive"
#     BANNED = "banned"


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def discover_databases(
    context: ToolContext,
) -> list[str]:
    """Discover all the databases in the MongoDB instance."""
    client = await DatabaseEngine.get_instance(context.get_secret("MONGODB_CONNECTION_STRING"))
    databases = await client.list_database_names()
    # Filter out admin and config databases by default
    databases = [db for db in databases if db not in ["admin", "config", "local"]]
    return databases


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def discover_collections(
    context: ToolContext,
    database_name: Annotated[str, "The database name to discover collections in"],
) -> list[str]:
    """Discover all the collections in the MongoDB database when the list of collections is not known.

    ALWAYS use this tool before any other tool that requires a collection name.
    """
    async with await DatabaseEngine.get_database(
        context.get_secret("MONGODB_CONNECTION_STRING"), database_name
    ) as db:
        collections = await db.list_collection_names()
    return list(collections)


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def get_collection_schema(
    context: ToolContext,
    database_name: Annotated[str, "The database name to get the collection schema of"],
    collection_name: Annotated[str, "The collection to get the schema of"],
    sample_size: Annotated[
        int,
        f"The number of documents to sample for schema discovery (default: {MAX_RECORDS_RETURNED})",
    ] = MAX_RECORDS_RETURNED,
) -> dict[str, Any]:
    """
    Get the schema/structure of a MongoDB collection by sampling documents.

    Since MongoDB is schema-less, this tool samples a configurable number of documents
    to infer the schema structure and data types.

    This tool should ALWAYS be used before executing any query. All collections in the query must be discovered first using the <discover_collections> tool.
    """
    async with await DatabaseEngine.get_database(
        context.get_secret("MONGODB_CONNECTION_STRING"), database_name
    ) as db:
        collection = db[collection_name]

        # Sample documents at random to infer schema
        # Use MongoDB's $sample aggregation to get random documents
        sample_docs = []
        async for doc in collection.aggregate([{"$sample": {"size": sample_size}}]):
            sample_docs.append(doc)

    if not sample_docs:
        return {"message": "Collection is empty", "schema": {}}

    # Infer schema from sampled documents
    schema = _infer_schema_from_docs(sample_docs)

    return {
        "total_documents_sampled": len(sample_docs),
        "sample_size_requested": sample_size,
        "schema": schema,
    }


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def find_documents(
    context: ToolContext,
    database_name: Annotated[str, "The database name to query"],
    collection_name: Annotated[str, "The collection name to query"],
    filter_dict: Annotated[
        str | None,
        'MongoDB filter/query as JSON string. Leave None for no filter (find all documents). Example: \'{"status": "active", "age": {"$gte": 18}}\'',
    ] = None,
    projection: Annotated[
        str | None,
        'Fields to include/exclude as JSON string. Use 1 to include, 0 to exclude. Example: \'{"name": 1, "email": 1, "_id": 0}\'. Leave None to include all fields.',
    ] = None,
    sort: Annotated[
        list[str] | None,
        'Sort criteria as list of JSON strings, each containing \'field\' and \'direction\' keys. Use 1 for ascending, -1 for descending. Example: [\'{"field": "name", "direction": 1}\', \'{"field": "created_at", "direction": -1}\']',
    ] = None,
    limit: Annotated[
        int,
        f"The maximum number of documents to return. Default: {MAX_RECORDS_RETURNED}.",
    ] = MAX_RECORDS_RETURNED,
    skip: Annotated[int, "The number of documents to skip. Default: 0."] = 0,
) -> list[str]:
    """
    Find documents in a MongoDB collection.

    ONLY use this tool if you have already loaded the schema of the collection you need to query.
    Use the <get_collection_schema> tool to load the schema if not already known.

    Returns a list of JSON strings, where each string represents a document from the collection (tools cannot return complex types).

    When running queries, follow these rules which will help avoid errors:
    * Always specify projection to limit fields returned if you don't need all data.
    * Always sort your results by the most important fields first. If you aren't sure, sort by '_id'.
    * Use appropriate MongoDB query operators for complex filtering ($gte, $lte, $in, $regex, etc.).
    * Be mindful of case sensitivity when querying string fields.
    * Use indexes when possible (typically on _id and commonly queried fields).
    """
    # Initialize variables to avoid UnboundLocalError in exception handler
    parsed_filter = None
    parsed_projection = None
    parsed_sort = None

    try:
        # Parse JSON string inputs
        parsed_filter = _parse_json_parameter(filter_dict, "filter_dict")
        parsed_projection = _parse_json_parameter(projection, "projection")
        parsed_sort = _parse_json_list_parameter(sort, "sort")

        (
            database_name,
            collection_name,
            parsed_filter,
            parsed_projection,
            parsed_sort,
            limit,
            skip,
        ) = DatabaseEngine.sanitize_query_params(
            database_name=database_name,
            collection_name=collection_name,
            filter_dict=parsed_filter,
            projection=parsed_projection,
            sort=parsed_sort,
            limit=limit,
            skip=skip,
        )

        async with await DatabaseEngine.get_database(
            context.get_secret("MONGODB_CONNECTION_STRING"), database_name
        ) as db:
            collection = db[collection_name]

            # Build the query
            cursor = collection.find(parsed_filter, parsed_projection)

            if parsed_sort:
                # Convert list of dicts to list of tuples for MongoDB sort
                sort_tuples = [(str(item["field"]), int(item["direction"])) for item in parsed_sort]
                cursor = cursor.sort(sort_tuples)

            cursor = cursor.skip(skip).limit(limit)

            # Execute query and collect results
            documents = []
            async for doc in cursor:
                # Convert ObjectId and other non-serializable types to strings
                doc = _serialize_document(doc)
                documents.append(json.dumps(doc))

            return documents

    except RetryableToolError:
        # Re-raise RetryableToolError as-is to preserve JSON validation messages
        raise
    except Exception as e:
        raise RetryableToolError(
            f"Query failed: {e}",
            developer_message=f"Query failed with parameters: database_name={database_name}, collection_name={collection_name}, filter_dict={parsed_filter}, projection={parsed_projection}, sort={parsed_sort}, limit={limit}, skip={skip}.",
            additional_prompt_content="Load the collection schema <get_collection_schema> or use the <discover_collections> tool to discover the collections and try again.",
            retry_after_ms=10,
        ) from e


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def count_documents(
    context: ToolContext,
    database_name: Annotated[str, "The database name to query"],
    collection_name: Annotated[str, "The collection name to query"],
    filter_dict: Annotated[
        str | None,
        'MongoDB filter/query as JSON string. Leave None for no filter (count all documents). Example: \'{"status": "active"}\'',
    ] = None,
) -> int:
    """Count documents in a MongoDB collection matching the given filter."""
    parsed_filter = None

    try:
        # Parse JSON string input
        parsed_filter = _parse_json_parameter(filter_dict, "filter_dict") or {}

        async with await DatabaseEngine.get_database(
            context.get_secret("MONGODB_CONNECTION_STRING"), database_name
        ) as db:
            collection = db[collection_name]

            count = await collection.count_documents(parsed_filter)
            return int(count)

    except RetryableToolError:
        # Re-raise RetryableToolError as-is to preserve JSON validation messages
        raise
    except Exception as e:
        raise RetryableToolError(
            f"Count query failed: {e}",
            developer_message=f"Count query failed with parameters: database_name={database_name}, collection_name={collection_name}, filter_dict={parsed_filter}.",
            additional_prompt_content="Check the collection name and filter criteria and try again.",
            retry_after_ms=10,
        ) from e


@tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
async def aggregate_documents(
    context: ToolContext,
    database_name: Annotated[str, "The database name to query"],
    collection_name: Annotated[str, "The collection name to query"],
    pipeline: Annotated[
        list[str],
        'MongoDB aggregation pipeline as a list of JSON strings, each representing a stage. Example: [\'{"$match": {"status": "active"}}\', \'{"$group": {"_id": "$category", "count": {"$sum": 1}}}\']',
    ],
    limit: Annotated[
        int,
        f"The maximum number of results to return from the aggregation. Default: {MAX_RECORDS_RETURNED}.",
    ] = MAX_RECORDS_RETURNED,
) -> list[str]:
    """
    Execute a MongoDB aggregation pipeline on a collection.

    ONLY use this tool if you have already loaded the schema of the collection you need to query.
    Use the <get_collection_schema> tool to load the schema if not already known.

    Returns a list of JSON strings, where each string represents a result document from the aggregation (tools cannot return complex types).

    Aggregation pipelines allow for complex data processing including:
    * $match - filter documents
    * $group - group documents and perform calculations
    * $project - reshape documents
    * $sort - sort documents
    * $limit - limit results
    * $lookup - join with other collections
    * And many more stages
    """
    parsed_pipeline = None

    try:
        # Parse JSON string inputs
        parsed_pipeline = _parse_json_list_parameter(pipeline, "pipeline")

        if parsed_pipeline is None:
            raise RetryableToolError(  # noqa: TRY301
                "Pipeline cannot be empty",
                developer_message="The pipeline parameter is required and cannot be None",
            )

        async with await DatabaseEngine.get_database(
            context.get_secret("MONGODB_CONNECTION_STRING"), database_name
        ) as db:
            collection = db[collection_name]

            # Add limit to pipeline if not already present
            pipeline_with_limit = parsed_pipeline.copy()
            has_limit = any("$limit" in stage for stage in pipeline_with_limit)
            if not has_limit:
                pipeline_with_limit.append({"$limit": limit})

            # Execute aggregation
            cursor = collection.aggregate(pipeline_with_limit)

            documents = []
            async for doc in cursor:
                # Convert ObjectId and other non-serializable types to strings
                doc = _serialize_document(doc)
                documents.append(json.dumps(doc))

            return documents

    except RetryableToolError:
        # Re-raise RetryableToolError as-is to preserve JSON validation messages
        raise
    except Exception as e:
        raise RetryableToolError(
            f"Aggregation query failed: {e}",
            developer_message=f"Aggregation query failed with parameters: database_name={database_name}, collection_name={collection_name}, pipeline={parsed_pipeline}, limit={limit}.",
            additional_prompt_content="Check the aggregation pipeline syntax and collection schema, then try again.",
            retry_after_ms=10,
        ) from e


# @tool(requires_secrets=["MONGODB_CONNECTION_STRING"])
# async def update_user_status(
#     context: ToolContext,
#     database_name: Annotated[str, "The database name containing the users collection"],
#     collection_name: Annotated[str, "The collection name containing user documents"],
#     user_id: Annotated[str, "The _id of the user to update"],
#     status: Annotated[UserStatus, "The new status for the user"],
# ) -> dict[str, Any]:
#     """
#     [CUSTOM TOOL]
#     Update the status of a user in the MongoDB collection.

#     This tool updates a user document by setting the status field to the specified value.
#     The status must be one of: active, inactive, or banned.

#     Returns information about the update operation including the number of documents modified.
#     """

#     try:
#         async with await DatabaseEngine.get_database(
#             context.get_secret("MONGODB_CONNECTION_STRING"), database_name
#         ) as db:
#             collection = db[collection_name]

#             # cast the user_id to int if it looks like an integer
#             if isinstance(user_id, str) and user_id.isdigit():
#                 user_id = int(user_id)

#             result = await collection.update_one(
#                 {"_id": user_id}, {"$set": {"status": status.value}}
#             )

#             print(result)

#             if result.matched_count == 0:
#                 return {
#                     "success": False,
#                     "message": f"No user found with _id: {user_id}",
#                     "matched_count": 0,
#                     "modified_count": 0,
#                 }

#             return {
#                 "success": True,
#                 "message": f"User status updated to '{status.value}'",
#                 "user_id": user_id,
#                 "new_status": status.value,
#                 "matched_count": result.matched_count,
#                 "modified_count": result.modified_count,
#             }

#     except Exception as e:
#         raise RetryableToolError(
#             f"Failed to update user status: {e}",
#             developer_message=f"Update operation failed with parameters: database_name={database_name}, collection_name={collection_name}, user_id={user_id}, status={status}.",
#             additional_prompt_content="Check the database name, collection name, and user ID, then try again.",
#             retry_after_ms=10,
#         ) from e
