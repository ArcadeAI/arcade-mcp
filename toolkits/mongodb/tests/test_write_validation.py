import pytest
from arcade_mongodb.tools.mongodb import aggregate_documents, count_documents, find_documents
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
async def test_filter_dict_blocks_set_operation(mock_context) -> None:
    """Test that $set operation in filter_dict is blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"$set": {"status": "modified"}}',  # Write operation
            limit=1,
        )

    error_message = str(exc_info.value)
    assert "Write operation '$set' not allowed in filter_dict" in error_message
    assert "$set" in exc_info.value.developer_message
    assert "Only read operations are allowed" in exc_info.value.developer_message


@pytest.mark.asyncio
async def test_filter_dict_blocks_update_operations(mock_context) -> None:
    """Test that various update operations in filter_dict are blocked."""
    update_ops = ["$inc", "$unset", "$push", "$pull", "$rename", "$currentDate"]

    for op in update_ops:
        with pytest.raises(RetryableToolError) as exc_info:
            await find_documents(
                mock_context,
                database_name="test_database",
                collection_name="users",
                filter_dict=f'{{"{op}": {{"field": "value"}}}}',
                limit=1,
            )

        error_message = str(exc_info.value)
        assert f"Write operation '{op}' not allowed in filter_dict" in error_message


@pytest.mark.asyncio
async def test_projection_blocks_write_operations(mock_context) -> None:
    """Test that write operations in projection are blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            projection='{"$set": {"modified": true}, "name": 1}',  # Write operation in projection
            limit=1,
        )

    error_message = str(exc_info.value)
    assert "Write operation '$set' not allowed in projection" in error_message


@pytest.mark.asyncio
async def test_sort_blocks_write_operations(mock_context) -> None:
    """Test that write operations in sort are blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            sort=['{"field": "name", "direction": 1, "$inc": {"counter": 1}}'],  # Write op in sort
            limit=1,
        )

    error_message = str(exc_info.value)
    assert "Write operation '$inc' not allowed in sort[0]" in error_message


@pytest.mark.asyncio
async def test_count_filter_blocks_write_operations(mock_context) -> None:
    """Test that write operations in count filter are blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await count_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": "active", "$unset": {"password": ""}}',  # Write operation
        )

    error_message = str(exc_info.value)
    assert "Write operation '$unset' not allowed in filter_dict" in error_message


@pytest.mark.asyncio
async def test_aggregation_pipeline_blocks_out_stage(mock_context) -> None:
    """Test that $out stage in aggregation pipeline is blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await aggregate_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            pipeline=[
                '{"$match": {"status": "active"}}',
                '{"$out": "output_collection"}',  # Write stage
            ],
        )

    error_message = str(exc_info.value)
    assert "Write stage '$out' not allowed in pipeline" in error_message


@pytest.mark.asyncio
async def test_aggregation_pipeline_blocks_merge_stage(mock_context) -> None:
    """Test that $merge stage in aggregation pipeline is blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await aggregate_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            pipeline=[
                '{"$match": {"status": "active"}}',
                '{"$merge": {"into": "target_collection"}}',  # Write stage
            ],
        )

    error_message = str(exc_info.value)
    assert "Write stage '$merge' not allowed in pipeline" in error_message


@pytest.mark.asyncio
async def test_where_operator_blocked(mock_context) -> None:
    """Test that $where operator is blocked for security reasons."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"$where": "this.name == \'admin\'"}',  # JavaScript execution
            limit=1,
        )

    error_message = str(exc_info.value)
    assert "JavaScript execution operator '$where' not allowed in filter_dict" in error_message
    assert (
        "JavaScript execution is not allowed for security reasons"
        in exc_info.value.developer_message
    )


@pytest.mark.asyncio
async def test_nested_write_operations_blocked(mock_context) -> None:
    """Test that nested write operations are blocked."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": "active", "nested": {"$set": {"field": "value"}}}',  # Nested write op
            limit=1,
        )

    error_message = str(exc_info.value)
    assert "Write operation '$set' not allowed in filter_dict" in error_message
    assert "nested.$set" in exc_info.value.developer_message  # Should show the path


@pytest.mark.asyncio
async def test_valid_read_operations_allowed(mock_context) -> None:
    """Test that valid read operations are allowed."""
    # These should not raise write operation errors
    try:
        # Test query operators
        result = await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": {"$in": ["active", "inactive"]}, "name": {"$regex": "^A"}}',
            projection='{"name": 1, "email": 1, "_id": 0}',
            sort=['{"field": "name", "direction": 1}'],
            limit=1,
        )
        assert isinstance(result, list)

        # Test aggregation pipeline with read-only stages
        pipeline_result = await aggregate_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            pipeline=[
                '{"$match": {"status": "active"}}',
                '{"$group": {"_id": "$status", "count": {"$sum": 1}}}',
                '{"$sort": {"count": -1}}',
            ],
        )
        assert isinstance(pipeline_result, list)

    except RetryableToolError as e:
        # If we get an error, it should not be about write operations
        error_message = str(e)
        nested_message = str(e.__cause__) if e.__cause__ else ""
        assert "Write operation" not in error_message
        assert "Write stage" not in error_message
        assert "Write operation" not in nested_message
        assert "Write stage" not in nested_message


@pytest.mark.asyncio
async def test_array_write_operations_blocked(mock_context) -> None:
    """Test that array write operations are blocked."""
    array_write_ops = ["$addToSet", "$pop", "$pull", "$push", "$pullAll"]

    for op in array_write_ops:
        with pytest.raises(RetryableToolError) as exc_info:
            await find_documents(
                mock_context,
                database_name="test_database",
                collection_name="users",
                filter_dict=f'{{"{op}": {{"tags": "new_tag"}}}}',
                limit=1,
            )

        error_message = str(exc_info.value)
        assert f"Write operation '{op}' not allowed in filter_dict" in error_message


@pytest.mark.asyncio
async def test_aggregation_stage_content_validated(mock_context) -> None:
    """Test that content within aggregation stages is also validated for write operations."""
    with pytest.raises(RetryableToolError) as exc_info:
        await aggregate_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            pipeline=[
                '{"$match": {"status": "active", "$set": {"modified": true}}}'  # Write op inside $match
            ],
        )

    error_message = str(exc_info.value)
    assert "Write operation '$set' not allowed in pipeline[0].$match" in error_message
