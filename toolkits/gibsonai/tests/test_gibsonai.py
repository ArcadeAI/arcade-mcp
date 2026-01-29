"""Tests for GibsonAI toolkit with simple parameter interfaces."""

from unittest.mock import AsyncMock, patch

import pytest
from arcade_core.errors import RetryableToolError, ToolExecutionError
from arcade_tdk import ToolContext

from arcade_gibsonai.tools.delete import delete_records
from arcade_gibsonai.tools.insert import insert_records
from arcade_gibsonai.tools.query import execute_read_query
from arcade_gibsonai.tools.update import update_records


@pytest.mark.asyncio
async def test_execute_select_query():
    """Test successful SELECT query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = [
            "id,name,email",
            "1,John,john@example.com",
            "2,Jane,jane@example.com",
        ]
        mock_client_class.return_value = mock_client

        result = await execute_read_query(context=mock_context, query="SELECT * FROM users")

        assert len(result) == 3
        assert "John" in result[1]
        assert "Jane" in result[2]
        mock_client.execute_query.assert_called_once_with("SELECT * FROM users")


@pytest.mark.asyncio
async def test_execute_read_query_with_conditions():
    """Test SELECT query with WHERE conditions."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["id,name", "1,John"]
        mock_client_class.return_value = mock_client

        result = await execute_read_query(
            context=mock_context, query="SELECT * FROM users WHERE id = 1"
        )

        assert len(result) == 2
        mock_client.execute_query.assert_called_once_with("SELECT * FROM users WHERE id = 1")


@pytest.mark.asyncio
async def test_execute_non_read_query_raises_error():
    """Test that non-read queries raise an error."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with pytest.raises(RetryableToolError, match="Only read-only queries"):
        await execute_read_query(context=mock_context, query="DELETE FROM users WHERE id = 1")

    with pytest.raises(RetryableToolError, match="Only read-only queries"):
        await execute_read_query(
            context=mock_context, query="UPDATE users SET name = 'Bob' WHERE id = 1"
        )


@pytest.mark.asyncio
async def test_execute_query_failure():
    """Test query execution failure."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.side_effect = Exception("Database connection failed")
        mock_client_class.return_value = mock_client

        with pytest.raises(RetryableToolError):
            await execute_read_query(context=mock_context, query="SELECT * FROM users")


@pytest.mark.asyncio
async def test_insert_records_success():
    """Test successful record insertion."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.insert.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row inserted"]
        mock_client_class.return_value = mock_client

        result = await insert_records(
            context=mock_context,
            table_name="users",
            records='[{"name": "John", "email": "john@example.com"}]',
            on_conflict="IGNORE",
        )

        # Result should be the raw response from GibsonAI
        assert result == ["1 row inserted"]


@pytest.mark.asyncio
async def test_insert_records_multiple():
    """Test inserting multiple records."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.insert.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["2 rows affected"]
        mock_client_class.return_value = mock_client

        result = await insert_records(
            context=mock_context,
            table_name="users",
            records='[{"name": "John", "email": "john@example.com"}, {"name": "Jane", "email": "jane@example.com"}]',
            on_conflict="REPLACE",
        )

        assert result == ["2 rows affected"]


@pytest.mark.asyncio
async def test_insert_records_validation_errors():
    """Test various validation errors."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    # Test empty table name
    with pytest.raises(RetryableToolError, match="Table name cannot be empty"):
        await insert_records(
            context=mock_context, table_name="", records='[{"name": "John"}]', on_conflict="IGNORE"
        )

    # Test empty records
    with pytest.raises(RetryableToolError, match="At least one record is required"):
        await insert_records(
            context=mock_context, table_name="users", records="[]", on_conflict="IGNORE"
        )

    # Test invalid JSON format (not an array)
    with pytest.raises(RetryableToolError, match="Records must be a JSON array"):
        await insert_records(
            context=mock_context,
            table_name="users",
            records='{"name": "John"}',
            on_conflict="IGNORE",
        )

    # Test malformed JSON
    with pytest.raises(RetryableToolError, match="Invalid JSON format"):
        await insert_records(
            context=mock_context,
            table_name="users",
            records='[{"name": "John"',
            on_conflict="IGNORE",
        )


@pytest.mark.asyncio
async def test_update_records_success():
    """Test successful record update."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.update.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row affected"]
        mock_client_class.return_value = mock_client

        result = await update_records(
            context=mock_context,
            table_name="users",
            updates='{"name": "Johnny"}',
            conditions='[{"column": "id", "operator": "=", "value": 1}]',
        )

        assert "Successfully updated records in table 'users'" in result


@pytest.mark.asyncio
async def test_update_records_validation_errors():
    """Test update validation errors."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    # Test missing conditions
    with pytest.raises(
        RetryableToolError,
        match="Update operations require at least one WHERE condition for safety",
    ):
        await update_records(
            context=mock_context, table_name="users", updates='{"name": "Johnny"}', conditions="[]"
        )

    # Test invalid table name
    with pytest.raises(RetryableToolError, match="Table name cannot be empty"):
        await update_records(
            context=mock_context,
            table_name="",
            updates='{"name": "Johnny"}',
            conditions='[{"column": "id", "operator": "=", "value": 1}]',
        )


@pytest.mark.asyncio
async def test_delete_records_success():
    """Test successful record deletion."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.delete.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row affected"]
        mock_client_class.return_value = mock_client

        result = await delete_records(
            context=mock_context,
            table_name="users",
            conditions='[{"column": "id", "operator": "=", "value": 1}]',
            confirm_deletion=True,
        )

        assert "Successfully deleted records from table 'users'" in result


@pytest.mark.asyncio
async def test_delete_records_validation_errors():
    """Test delete validation errors."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    # Test missing confirmation
    with pytest.raises(ToolExecutionError, match="Error in execution of DeleteRecords"):
        await delete_records(
            context=mock_context,
            table_name="users",
            conditions='[{"column": "id", "operator": "=", "value": 5}]',
            confirm_deletion=False,
        )

    # Test empty table name
    with pytest.raises(ToolExecutionError, match="Error in execution of DeleteRecords"):
        await delete_records(
            context=mock_context,
            table_name="",
            conditions='[{"column": "id", "operator": "=", "value": 5}]',
            confirm_deletion=True,
        )
