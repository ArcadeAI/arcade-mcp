import json

import pytest
from arcade_mongodb.database_engine import DatabaseEngine
from arcade_mongodb.tools.mongodb import (
    # UserStatus,
    aggregate_documents,
    count_documents,
    discover_collections,
    discover_databases,
    find_documents,
    get_collection_schema,
    # update_user_status,
)
from arcade_tdk import ToolContext, ToolSecretItem
from arcade_tdk.errors import RetryableToolError

from .conftest import TEST_MONGODB_CONNECTION_STRING


@pytest.fixture
def mock_context():
    context = ToolContext()
    context.secrets = []
    context.secrets.append(
        ToolSecretItem(key="MONGODB_CONNECTION_STRING", value=TEST_MONGODB_CONNECTION_STRING)
    )
    return context


@pytest.mark.asyncio
async def test_discover_databases(mock_context) -> None:
    databases = await discover_databases(mock_context)
    assert isinstance(databases, list)
    # Should not include system databases like admin, config, local
    for db in databases:
        assert db not in ["admin", "config", "local"]


@pytest.mark.asyncio
async def test_discover_collections(mock_context) -> None:
    collections = await discover_collections(mock_context, "test_database")
    assert "users" in collections
    assert "messages" in collections


@pytest.mark.asyncio
async def test_get_collection_schema(mock_context) -> None:
    schema_result = await get_collection_schema(
        mock_context, "test_database", "users", sample_size=10
    )

    assert "schema" in schema_result
    assert "total_documents_sampled" in schema_result
    assert schema_result["total_documents_sampled"] == 10  # We have 10 users

    schema = schema_result["schema"]
    assert "_id" in schema
    assert "name" in schema
    assert "email" in schema
    assert "password_hash" in schema
    assert "status" in schema
    assert "created_at" in schema
    assert "updated_at" in schema


@pytest.mark.asyncio
async def test_find_documents_basic(mock_context) -> None:
    # Find all users
    result = await find_documents(
        mock_context, database_name="test_database", collection_name="users", limit=10
    )

    assert len(result) == 10
    # Parse JSON strings to check contents
    docs = [json.loads(doc_str) for doc_str in result]
    assert all("name" in doc for doc in docs)
    assert all("email" in doc for doc in docs)


@pytest.mark.asyncio
async def test_find_documents_with_filter(mock_context) -> None:
    # Find active users
    result = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        filter_dict='{"status": "active"}',
        limit=10,
    )

    assert len(result) == 10  # All users in dump are active
    docs = [json.loads(doc_str) for doc_str in result]
    assert all(doc["status"] == "active" for doc in docs)


@pytest.mark.asyncio
async def test_find_documents_with_projection(mock_context) -> None:
    # Find users with only name and email
    result = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        projection='{"name": 1, "email": 1, "_id": 0}',
        limit=10,
    )

    assert len(result) == 10
    docs = [json.loads(doc_str) for doc_str in result]
    for doc in docs:
        assert "name" in doc
        assert "email" in doc
        assert "_id" not in doc
        assert "password_hash" not in doc


@pytest.mark.asyncio
async def test_find_documents_with_sort(mock_context) -> None:
    # Find users sorted by _id descending
    result = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        sort=['{"field": "_id", "direction": -1}'],
        limit=3,
    )

    assert len(result) == 3
    docs = [json.loads(doc_str) for doc_str in result]
    ids = [doc["_id"] for doc in docs]
    assert ids == [10, 9, 8]  # Descending order


@pytest.mark.asyncio
async def test_count_documents(mock_context) -> None:
    # Count all users
    count = await count_documents(
        mock_context, database_name="test_database", collection_name="users"
    )
    assert count == 10

    # Count active users
    active_count = await count_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        filter_dict='{"status": "active"}',
    )
    assert active_count == 10


@pytest.mark.asyncio
async def test_aggregate_documents(mock_context) -> None:
    # Aggregate to count users by status
    pipeline = ['{"$group": {"_id": "$status", "count": {"$sum": 1}}}', '{"$sort": {"count": -1}}']

    result = await aggregate_documents(
        mock_context, database_name="test_database", collection_name="users", pipeline=pipeline
    )

    assert len(result) == 1  # Only active users
    # Should be sorted by count descending
    doc = json.loads(result[0])
    assert doc["_id"] == "active"
    assert doc["count"] == 10


@pytest.mark.asyncio
async def test_find_documents_with_skip_and_limit(mock_context) -> None:
    # Test pagination
    result1 = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        sort=['{"field": "name", "direction": 1}'],
        limit=2,
        skip=0,
    )

    result2 = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="users",
        sort=['{"field": "name", "direction": 1}'],
        limit=2,
        skip=2,
    )

    assert len(result1) == 2
    assert len(result2) == 2

    docs1 = [json.loads(doc_str) for doc_str in result1]
    docs2 = [json.loads(doc_str) for doc_str in result2]

    assert docs1[0]["name"] == "Alice"
    assert docs1[1]["name"] == "Bob"
    assert docs2[0]["name"] == "Charlie"
    assert docs2[1]["name"] == "Diana"


@pytest.mark.asyncio
async def test_error_handling_invalid_database(mock_context) -> None:
    # Test with non-existent database - should not error but return empty results
    collections = await discover_collections(mock_context, "nonexistent_database")
    assert collections == []


@pytest.mark.asyncio
async def test_error_handling_invalid_collection(mock_context) -> None:
    # Test with non-existent collection
    result = await find_documents(
        mock_context,
        database_name="test_database",
        collection_name="nonexistent_collection",
        limit=10,
    )
    assert result == []


@pytest.mark.asyncio
async def test_sanitize_query_params() -> None:
    # Test parameter validation
    with pytest.raises(RetryableToolError) as e:
        DatabaseEngine.sanitize_query_params("", "users", {}, None, None, 10, 0)
    assert "Database name is required" in str(e.value)

    with pytest.raises(RetryableToolError) as e:
        DatabaseEngine.sanitize_query_params("test_db", "", {}, None, None, 10, 0)
    assert "Collection name is required" in str(e.value)

    with pytest.raises(RetryableToolError) as e:
        DatabaseEngine.sanitize_query_params(
            "test_db", "users", {}, None, None, 2000, 0
        )  # Too high limit
    assert "Limit is too high" in str(e.value)


# @pytest.mark.asyncio
# async def test_update_user_status_success(mock_context) -> None:
#     """Test successful user status update."""
#     # First, find a user to update
#     users = await find_documents(
#         mock_context, database_name="test_database", collection_name="users", limit=1
#     )
#     assert len(users) > 0

#     user_doc = json.loads(users[0])
#     user_id = user_doc["_id"]

#     # Update user status to inactive
#     result = await update_user_status(
#         mock_context,
#         database_name="test_database",
#         collection_name="users",
#         user_id=user_id,
#         status=UserStatus.INACTIVE,
#     )

#     assert result["success"] is True
#     assert result["user_id"] == user_id
#     assert result["new_status"] == "inactive"
#     assert result["matched_count"] == 1
#     assert result["modified_count"] == 1

#     # Verify the update by finding the user again
#     # Convert user_id to int since the test data uses integer IDs
#     user_id_int = int(user_id)
#     updated_users = await find_documents(
#         mock_context,
#         database_name="test_database",
#         collection_name="users",
#         filter_dict=f'{{"_id": {user_id_int}}}',
#         limit=1,
#     )
#     assert len(updated_users) == 1
#     updated_user = json.loads(updated_users[0])
#     assert updated_user["status"] == "inactive"


# @pytest.mark.asyncio
# async def test_update_user_status_user_not_found(mock_context) -> None:
#     """Test updating status for non-existent user."""
#     result = await update_user_status(
#         mock_context,
#         database_name="test_database",
#         collection_name="users",
#         user_id="nonexistent_user_id",
#         status=UserStatus.BANNED,
#     )

#     assert result["success"] is False
#     assert "No user found with _id" in result["message"]
#     assert result["matched_count"] == 0
#     assert result["modified_count"] == 0
