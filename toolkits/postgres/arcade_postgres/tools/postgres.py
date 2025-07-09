import re
from typing import Annotated, Any, ClassVar

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

MAX_ROWS_RETURNED = 1000
DEFAULT_ISOLATION_LEVEL = "READ COMMITTED"
TEST_QUERY = "SELECT 1"
ERROR_REMAPPING = {
    re.compile(r"This result object does not return rows"): "Only SELECT queries are allowed.",
}


class DatabaseEngine:
    _instance: ClassVar[None] = None
    _engines: ClassVar[dict[str, AsyncEngine]] = {}

    @classmethod
    async def get_instance(
        cls, connection_string: str, isolation_level: str = DEFAULT_ISOLATION_LEVEL
    ) -> AsyncEngine:
        key = f"{connection_string}:{isolation_level}"
        if key not in cls._engines:
            # Convert sync connection string to async if needed
            if connection_string.startswith("postgresql://"):
                async_connection_string = connection_string.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            else:
                async_connection_string = connection_string

            cls._engines[key] = create_async_engine(
                async_connection_string, isolation_level=isolation_level
            )

        # try a simple query to see if the connection is valid
        try:
            async with cls._engines[key].connect() as connection:
                await connection.execute(text(TEST_QUERY))
            return cls._engines[key]
        except Exception:
            await cls._engines[key].dispose()

            # try again
            try:
                async with cls._engines[key].connect() as connection:
                    await connection.execute(text(TEST_QUERY))
                return cls._engines[key]
            except Exception as e:
                raise RetryableToolError(
                    f"Connection failed: {e}",
                    developer_message=f"Connection to '{connection_string}' failed.",
                    additional_prompt_content="Check the connection string and try again.",
                    retry_after_ms=10,
                ) from e

    @classmethod
    async def get_engine(
        cls, connection_string: str, isolation_level: str = DEFAULT_ISOLATION_LEVEL
    ):
        engine = await cls.get_instance(connection_string, isolation_level)

        class ConnectionContextManager:
            def __init__(self, engine):
                self.engine = engine

            async def __aenter__(self):
                return self.engine

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Connection cleanup is handled by the async context manager
                pass

        return ConnectionContextManager(engine)

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up all cached engines. Call this when shutting down."""
        for engine in cls._engines.values():
            await engine.dispose()
        cls._engines.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the engine cache without disposing engines. Use with caution."""
        cls._engines.clear()


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
async def discover_tables(
    context: ToolContext,
    schema_name: Annotated[str, "The database schema to discover tables in"] = "public",
) -> list[str]:
    """Discover all the tables in the postgres database when the list of tables is not known.

    THIS TOOL SHOULD ALWAYS BE USED BEFORE ANY OTHER TOOL THAT REQUIRES A TABLE NAME.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("DATABASE_CONNECTION_STRING")
    ) as engine:
        tables = await _get_tables(engine, schema_name)
        return tables


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
async def get_table_schema(
    context: ToolContext,
    schema_name: Annotated[str, "The database schema to get the table schema of"],
    table_name: Annotated[str, "The table to get the schema of"],
) -> list[str]:
    """
    Get the schema of a postgres table in the postgres database when the schema is not known, and the name of the table is provided.

    THIS TOOL SHOULD ALWAYS BE USED BEFORE EXECUTING ANY QUERY.  ALL TABLES IN THE QUERY MUST BE DISCOVERED FIRST.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("DATABASE_CONNECTION_STRING")
    ) as engine:
        return await _get_table_schema(engine, schema_name, table_name)


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
async def execute_query(
    context: ToolContext,
    query: Annotated[str, "The postgres SQL query to execute.  Only SELECT queries are allowed."],
) -> list[str]:
    """
    You have a connection to a postgres database.
    Execute a query and return the results against the postgres database.

    ONLY USE THIS TOOL IF YOU HAVE ALREADY LOADED THE SCHEMA OF THE TABLES YOU NEED TO QUERY.  USE THE <GetTableSchema> TOOL TO LOAD THE SCHEMA IF NOT ALREADY KNOWN.

    When running queries, follow the following rules which will help avoid errors:
    * Always use case-insensitive queries to match strings in the query.
    * Always trim strings in the query.
    * Prefer LIKE queries over direct string matches or regex queries.
    * Only join on columns that are indexed or the primary key.  Do not join on arbitrary columns.

    Only SELECT queries are allowed.  Do not use INSERT, UPDATE, DELETE, or other DML statements.  This tool will reject them.

    Unless otherwise specified, ensure that query has a LIMIT of 100 for all results.  This tool will enforce that no more than 1000 rows are returned at maximum.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("DATABASE_CONNECTION_STRING")
    ) as engine:
        try:
            return await _execute_query(engine, query)
        except Exception as e:
            for pattern, replacement in ERROR_REMAPPING.items():
                if pattern.search(str(e)):
                    e = Exception(replacement)

            raise RetryableToolError(
                f"Query failed: {e}",
                developer_message=f"Query '{query}' failed.",
                additional_prompt_content="Load the database schema <GetTableSchema> or use the <DiscoverTables> tool to discover the tables and try again.",
                retry_after_ms=10,
            ) from e


async def _get_tables(engine: AsyncEngine, schema_name: str) -> list[str]:
    """Get all the tables in the database"""
    async with engine.connect() as conn:
        schemas: list[str] = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_schema_names()
        )
        tables = []
        for schema in schemas:
            if schema == schema_name:
                these_tables = await conn.run_sync(
                    lambda sync_conn, s=schema: inspect(sync_conn).get_table_names(schema=s)
                )
                tables.extend(these_tables)
        return tables


async def _get_table_schema(engine: AsyncEngine, schema_name: str, table_name: str) -> list[str]:
    """Get the schema of a table"""
    async with engine.connect() as connection:
        columns_table = await connection.run_sync(
            lambda sync_conn, t=table_name, s=schema_name: inspect(sync_conn).get_columns(t, s)
        )

        # Get primary key information
        pk_constraint = await connection.run_sync(
            lambda sync_conn, t=table_name, s=schema_name: inspect(sync_conn).get_pk_constraint(
                t, s
            )
        )
        primary_keys = set(pk_constraint.get("constrained_columns", []))

        # Get index information
        indexes = await connection.run_sync(
            lambda sync_conn, t=table_name, s=schema_name: inspect(sync_conn).get_indexes(t, s)
        )
        indexed_columns = set()
        for index in indexes:
            indexed_columns.update(index.get("column_names", []))

        results = []
        for column in columns_table:
            column_name = column["name"]
            column_type = column["type"].python_type.__name__

            # Build column description
            description = f"{column_name}: {column_type}"

            # Add primary key indicator
            if column_name in primary_keys:
                description += " (PRIMARY KEY)"

            # Add index indicator
            if column_name in indexed_columns:
                description += " (INDEXED)"

            results.append(description)

        return results[:MAX_ROWS_RETURNED]


async def _execute_query(
    engine: AsyncEngine, query: str, params: dict[str, Any] | None = None
) -> list[str]:
    """Execute a query and return the results."""
    async with engine.connect() as connection:
        result = await connection.execute(text(query), params)
        rows = result.fetchall()
        results = [str(row) for row in rows]
        return results[:MAX_ROWS_RETURNED]
