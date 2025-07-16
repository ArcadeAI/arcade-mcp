import pytest
from unittest.mock import AsyncMock, patch
from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError

from arcade_gibsonai.tools.query import execute_query


@pytest.mark.asyncio
async def test_execute_select_query():
    """Test successful SELECT query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["result1", "result2"]
        mock_client_class.return_value = mock_client

        result = await execute_query(mock_context, "SELECT * FROM users LIMIT 10")

        assert result == ["result1", "result2"]
        mock_client.execute_query.assert_called_once_with(
            "SELECT * FROM users LIMIT 10"
        )


@pytest.mark.asyncio
async def test_execute_insert_query():
    """Test successful INSERT query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row inserted"]
        mock_client_class.return_value = mock_client

        result = await execute_query(
            mock_context,
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')",
        )

        assert result == ["1 row inserted"]
        mock_client.execute_query.assert_called_once_with(
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')"
        )


@pytest.mark.asyncio
async def test_execute_update_query():
    """Test successful UPDATE query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row updated"]
        mock_client_class.return_value = mock_client

        result = await execute_query(
            mock_context, "UPDATE users SET email = 'new@example.com' WHERE id = 1"
        )

        assert result == ["1 row updated"]
        mock_client.execute_query.assert_called_once_with(
            "UPDATE users SET email = 'new@example.com' WHERE id = 1"
        )


@pytest.mark.asyncio
async def test_execute_delete_query():
    """Test successful DELETE query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["1 row deleted"]
        mock_client_class.return_value = mock_client

        result = await execute_query(mock_context, "DELETE FROM users WHERE id = 5")

        assert result == ["1 row deleted"]
        mock_client.execute_query.assert_called_once_with(
            "DELETE FROM users WHERE id = 5"
        )


@pytest.mark.asyncio
async def test_execute_create_table_query():
    """Test successful CREATE TABLE query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["Table created successfully"]
        mock_client_class.return_value = mock_client

        result = await execute_query(
            mock_context,
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255))",
        )

        assert result == ["Table created successfully"]
        mock_client.execute_query.assert_called_once_with(
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255))"
        )


@pytest.mark.asyncio
async def test_execute_alter_table_query():
    """Test successful ALTER TABLE query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["Table altered successfully"]
        mock_client_class.return_value = mock_client

        result = await execute_query(
            mock_context, "ALTER TABLE products ADD COLUMN description TEXT"
        )

        assert result == ["Table altered successfully"]
        mock_client.execute_query.assert_called_once_with(
            "ALTER TABLE products ADD COLUMN description TEXT"
        )


@pytest.mark.asyncio
async def test_execute_drop_table_query():
    """Test successful DROP TABLE query execution."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["Table dropped successfully"]
        mock_client_class.return_value = mock_client

        result = await execute_query(mock_context, "DROP TABLE temporary_data")

        assert result == ["Table dropped successfully"]
        mock_client.execute_query.assert_called_once_with("DROP TABLE temporary_data")


@pytest.mark.asyncio
async def test_execute_query_failure():
    """Test query execution failure."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.side_effect = Exception("Database error")
        mock_client_class.return_value = mock_client

        with pytest.raises(RetryableToolError) as exc_info:
            await execute_query(mock_context, "SELECT * FROM users")

        assert "Query failed: Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_complex_query():
    """Test complex query with joins and conditions."""
    mock_context = AsyncMock(spec=ToolContext)
    mock_context.get_secret.return_value = "test_api_key"

    with patch("arcade_gibsonai.tools.query.GibsonAIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = ["complex_result"]
        mock_client_class.return_value = mock_client

        complex_query = """
        SELECT u.name, p.title, o.total 
        FROM users u 
        JOIN orders o ON u.id = o.user_id 
        JOIN products p ON o.product_id = p.id 
        WHERE u.active = true 
        ORDER BY o.created_at DESC 
        LIMIT 50
        """

        result = await execute_query(mock_context, complex_query)

        assert result == ["complex_result"]
        mock_client.execute_query.assert_called_once_with(complex_query)
