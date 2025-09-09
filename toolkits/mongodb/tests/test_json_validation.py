import pytest
from arcade_core.errors import ToolExecutionError
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
async def test_invalid_json_in_filter_dict(mock_context) -> None:
    """Test that invalid JSON in filter_dict returns a reasonable error message."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": "active",}',  # Invalid JSON - trailing comma
            limit=1,
        )

    # Check that this is a JSON validation error
    error_message = str(exc_info.value)
    assert "Invalid JSON in filter_dict" in error_message

    # Check that the developer message contains helpful information
    assert "filter_dict" in exc_info.value.developer_message
    assert "JSON" in exc_info.value.additional_prompt_content

    # Check that the original JSON error is in the cause chain
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_invalid_json_in_projection(mock_context) -> None:
    """Test that invalid JSON in projection returns a reasonable error message."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            projection='{"name": 1, "email": 1,}',  # Invalid JSON - trailing comma
            limit=1,
        )

    # Check that this is a JSON validation error
    error_message = str(exc_info.value)
    assert "Invalid JSON in projection" in error_message

    # Check that the error message is helpful
    assert "projection" in exc_info.value.developer_message
    assert "JSON" in exc_info.value.additional_prompt_content

    # Check that the original JSON error is in the cause chain
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_invalid_json_in_sort(mock_context) -> None:
    """Test that invalid JSON in sort returns a reasonable error message."""
    with pytest.raises(RetryableToolError) as exc_info:
        await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            sort=['{"field": "name", "direction": 1,}'],  # Invalid JSON - trailing comma
            limit=1,
        )

    # Check that this is a JSON validation error
    error_message = str(exc_info.value)
    assert "Invalid JSON in sort" in error_message

    # Check that the error message is helpful
    assert "sort" in exc_info.value.developer_message
    assert "JSON" in exc_info.value.additional_prompt_content

    # Check that the original JSON error is in the cause chain
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_invalid_json_in_count_filter(mock_context) -> None:
    """Test that invalid JSON in count_documents filter returns a reasonable error message."""
    with pytest.raises(RetryableToolError) as exc_info:
        await count_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": "active",}',  # Invalid JSON - trailing comma
        )

    # Check that this is a JSON validation error
    error_message = str(exc_info.value)
    assert "Invalid JSON in filter_dict" in error_message

    # Check that the error message is helpful
    assert "filter_dict" in exc_info.value.developer_message
    assert "JSON" in exc_info.value.additional_prompt_content

    # Check that the original JSON error is in the cause chain
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_invalid_json_in_pipeline(mock_context) -> None:
    """Test that invalid JSON in aggregation pipeline returns a reasonable error message."""
    with pytest.raises(RetryableToolError) as exc_info:
        await aggregate_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            pipeline=['{"$match": {"status": "active",}}'],  # Invalid JSON - trailing comma
        )

    # Check that this is a JSON validation error
    error_message = str(exc_info.value)
    assert "Invalid JSON in pipeline" in error_message

    # Check that the error message is helpful
    assert "pipeline" in exc_info.value.developer_message
    assert "JSON" in exc_info.value.additional_prompt_content

    # Check that the original JSON error is in the cause chain
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_malformed_json_string(mock_context) -> None:
    """Test various malformed JSON strings return reasonable error messages."""
    test_cases = [
        ('{"unclosed": "string}', "Unterminated string"),
        ('{"missing_quotes": value}', "Expecting"),
        ('{missing_closing_brace: "value"}', "Expecting"),
        ('[{"array": "with"}, {"missing": }]', "Expecting"),
    ]

    for invalid_json, expected_error_fragment in test_cases:
        with pytest.raises(RetryableToolError) as exc_info:
            await find_documents(
                mock_context,
                database_name="test_database",
                collection_name="users",
                filter_dict=invalid_json,
                limit=1,
            )

        # Check that this is a JSON validation error
        error_message = str(exc_info.value)
        assert "Invalid JSON in filter_dict" in error_message

        # Check that specific error details are included when expected
        if expected_error_fragment:
            assert (
                expected_error_fragment in error_message
                or expected_error_fragment in exc_info.value.developer_message
            )

        # Ensure helpful context is provided
        assert "filter_dict" in exc_info.value.developer_message
        assert "JSON" in exc_info.value.additional_prompt_content
        assert "escaping" in exc_info.value.additional_prompt_content

        # Check that the original JSON error is in the cause chain
        assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_valid_json_does_not_error(mock_context) -> None:
    """Test that valid JSON does not raise JSON parsing errors."""
    # This should not raise a JSON parsing error (might raise other errors, but not JSON-related)
    try:
        result = await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"status": "active"}',
            projection='{"name": 1, "_id": 0}',
            sort=['{"field": "name", "direction": 1}'],
            limit=1,
        )
        # If we get here, JSON parsing succeeded
        assert isinstance(result, list)
    except (ToolExecutionError, RetryableToolError) as e:
        # If we get an error, it should not be about JSON parsing
        # Check both the outer error and any nested error
        error_message = str(e)
        nested_message = str(e.__cause__) if e.__cause__ else ""
        assert "Invalid JSON" not in error_message
        assert "Invalid JSON" not in nested_message


@pytest.mark.asyncio
async def test_duplicate_keys_are_valid_json(mock_context) -> None:
    """Test that duplicate keys in JSON are valid (Python JSON allows this)."""
    # This should NOT raise a JSON parsing error because duplicate keys are valid JSON
    try:
        result = await find_documents(
            mock_context,
            database_name="test_database",
            collection_name="users",
            filter_dict='{"duplicate": "key", "duplicate": "key"}',  # Valid JSON - last value wins
            limit=1,
        )
        # If we get here, JSON parsing succeeded (might get empty results, but no JSON error)
        assert isinstance(result, list)
    except (ToolExecutionError, RetryableToolError) as e:
        # If we get an error, it should not be about JSON parsing
        error_message = str(e)
        nested_message = str(e.__cause__) if e.__cause__ else ""
        assert "Invalid JSON" not in error_message
        assert "Invalid JSON" not in nested_message
