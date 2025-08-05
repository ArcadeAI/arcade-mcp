import os
from os import environ

import pytest
import pytest_asyncio
from arcade_clickhouse.tools.clickhouse import (
    DatabaseEngine,
    discover_schemas,
    discover_tables,
    execute_select_query,
    get_table_schema,
)
from arcade_tdk import ToolContext, ToolSecretItem
from arcade_tdk.errors import RetryableToolError

CLICKHOUSE_DATABASE_CONNECTION_STRING = (
    environ.get("TEST_CLICKHOUSE_DATABASE_CONNECTION_STRING")
    or "clickhouse+native://localhost:9000/default"
)


@pytest.fixture
def mock_context():
    context = ToolContext()
    context.secrets = []
    context.secrets.append(
        ToolSecretItem(
            key="CLICKHOUSE_DATABASE_CONNECTION_STRING", value=CLICKHOUSE_DATABASE_CONNECTION_STRING
        )
    )

    return context


# before the tests, restore the database from the dump
@pytest_asyncio.fixture(autouse=True)
async def restore_database():
    import clickhouse_connect

    # Create client for database setup
    client = clickhouse_connect.get_client(host="localhost", port=8123)

    # Clear existing tables first to avoid duplicates
    client.command("DROP TABLE IF EXISTS default.messages")
    client.command("DROP TABLE IF EXISTS default.users")

    # Read and execute the dump file
    with open(f"{os.path.dirname(__file__)}/dump.sql") as f:
        queries = f.read().split(";")
        for query in queries:
            if query.strip():
                client.command(query)

    client.close()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_engines():
    """Clean up database engines after each test to prevent connection leaks."""
    yield
    # Clean up all cached engines after each test
    await DatabaseEngine.cleanup()


@pytest.mark.asyncio
async def test_discover_schemas(mock_context) -> None:
    assert await discover_schemas(mock_context) == ["default"]


@pytest.mark.asyncio
async def test_discover_tables(mock_context) -> None:
    tables = await discover_tables(mock_context)
    assert sorted(tables) == ["messages", "users"]


@pytest.mark.asyncio
async def test_get_table_schema(mock_context) -> None:
    users_schema = await get_table_schema(mock_context, "default", "users")
    expected_users = [
        "id: UInt32 (PRIMARY KEY)",
        "name: String",
        "email: String",
        "password_hash: String",
        "created_at: DateTime (PRIMARY KEY)",
        "updated_at: DateTime",
        "status: String",
    ]
    assert users_schema == expected_users

    messages_schema = await get_table_schema(mock_context, "default", "messages")
    expected_messages = [
        "id: UInt32 (PRIMARY KEY)",
        "body: String",
        "user_id: UInt32",
        "created_at: DateTime (PRIMARY KEY)",
        "updated_at: DateTime",
    ]
    assert messages_schema == expected_messages


@pytest.mark.asyncio
async def test_execute_select_query(mock_context) -> None:
    # Test specific user query with limit
    result1 = await execute_select_query(
        mock_context,
        select_clause="id, name, email",
        from_clause="users",
        where_clause="id = 1",
        limit=1,
    )
    assert result1 == ["(1, 'Alice', 'alice@example.com')"]

    # Test query with offset
    result2 = await execute_select_query(
        mock_context,
        select_clause="id, name, email",
        from_clause="users",
        order_by_clause="id",
        limit=1,
        offset=1,
    )
    assert result2 == ["(2, 'Bob', 'bob@example.com')"]


@pytest.mark.asyncio
async def test_execute_select_query_with_keywords(mock_context) -> None:
    result = await execute_select_query(
        mock_context,
        select_clause="SELECT id, name, email",
        from_clause="FROM users",
        limit=1,
    )
    assert result == ["(1, 'Alice', 'alice@example.com')"]


@pytest.mark.asyncio
async def test_execute_select_query_with_join(mock_context) -> None:
    result = await execute_select_query(
        mock_context,
        select_clause="u.id, u.name, u.email, m.id, m.body",
        from_clause="users u",
        join_clause="messages m ON u.id = m.user_id",
        limit=1,
    )
    assert result == ["(1, 'Alice', 'alice@example.com', 1, 'Hello everyone!')"]


@pytest.mark.asyncio
async def test_execute_select_query_with_group_by(mock_context) -> None:
    result = await execute_select_query(
        mock_context,
        select_clause="u.name, COUNT(m.id) AS message_count",
        from_clause="messages m",
        join_clause="users u ON m.user_id = u.id",
        group_by_clause="u.name",
        order_by_clause="message_count DESC",
        limit=2,
    )
    assert result == [
        "('Evan', 13)",
        "('Alice', 3)",
    ]


@pytest.mark.asyncio
async def test_execute_select_query_with_no_results(mock_context) -> None:
    # does not raise an error
    assert (
        await execute_select_query(
            mock_context,
            select_clause="id, name, email",
            from_clause="users",
            where_clause="id = 9999999999",
        )
        == []
    )


@pytest.mark.asyncio
async def test_execute_select_query_with_problem(mock_context) -> None:
    # 'foo' is not a valid id
    with pytest.raises(RetryableToolError) as e:
        await execute_select_query(
            mock_context,
            select_clause="*",
            from_clause="users",
            where_clause="id = 'foo'",
        )
    assert "Do not use * in the select clause" in str(e.value)


@pytest.mark.asyncio
async def test_execute_select_query_rejects_non_select(mock_context) -> None:
    with pytest.raises(RetryableToolError) as e:
        await execute_select_query(
            mock_context,
            select_clause="INSERT INTO users (name, email, password_hash) VALUES ('Luigi', 'luigi@example.com', 'password')",
            from_clause="users",
        )
    assert "Only SELECT queries are allowed" in str(e.value)
