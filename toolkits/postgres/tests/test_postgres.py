import pytest
from arcade_postgres.tools.postgres import (
    discover_tables,
    execute_query,
    get_table_schema,
)
from arcade_tdk import ToolContext, ToolSecretItem


@pytest.fixture
def mock_context():
    context = ToolContext()
    context.secrets = []
    context.secrets.append(
        ToolSecretItem(
            key="DATABASE_CONNECTION_STRING", value="postgresql://evan@localhost:5432/postgres"
        )
    )

    return context


@pytest.mark.asyncio
async def test_discover_tables(mock_context) -> None:
    assert await discover_tables(mock_context) == ["users", "messages"]


@pytest.mark.asyncio
async def test_get_table_schema(mock_context) -> None:
    assert await get_table_schema(mock_context, "public", "users") == [
        "id: int (PRIMARY KEY)",
        "name: str (INDEXED)",
        "email: str (INDEXED)",
        "password_hash: str",
        "created_at: datetime",
        "updated_at: datetime",
        "status: str",
    ]

    assert await get_table_schema(mock_context, "public", "messages") == [
        "id: int (PRIMARY KEY)",
        "body: str",
        "user_id: int",
        "created_at: datetime",
        "updated_at: datetime",
    ]


@pytest.mark.asyncio
async def test_execute_query(mock_context) -> None:
    assert await execute_query(mock_context, "SELECT id, name, email FROM users WHERE id = 1") == [
        "(1, 'Mario', 'mario@example.com')"
    ]
