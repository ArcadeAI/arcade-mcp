from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from ..database_engine import MAX_ROWS_RETURNED, DatabaseEngine


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
async def discover_schemas(
    context: ToolContext,
) -> list[str]:
    """Discover all the schemas in the postgres database."""
    async with await DatabaseEngine.get_engine(
        context.get_secret("DATABASE_CONNECTION_STRING")
    ) as engine:
        schemas = await _get_schemas(engine)
        return schemas


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
async def discover_tables(
    context: ToolContext,
    schema_name: Annotated[
        str, "The database schema to discover tables in (default value: 'public')"
    ] = "public",
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
    Get the schema/structure of a postgres table in the postgres database when the schema is not known, and the name of the table is provided.

    THIS TOOL SHOULD ALWAYS BE USED BEFORE EXECUTING ANY QUERY.  ALL TABLES IN THE QUERY MUST BE DISCOVERED FIRST USING THE <DiscoverTables> TOOL.
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

    When running queries, follow these rules which will help avoid errors:
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
            raise RetryableToolError(
                f"Query failed: {e}",
                developer_message=f"Query '{query}' failed.",
                additional_prompt_content="Load the database schema <GetTableSchema> or use the <DiscoverTables> tool to discover the tables and try again.",
                retry_after_ms=10,
            ) from e


async def _get_schemas(engine: AsyncEngine) -> list[str]:
    """Get all the schemas in the database"""
    async with engine.connect() as conn:

        def get_schema_names(sync_conn: Any) -> list[str]:
            return list(inspect(sync_conn).get_schema_names())

        schemas: list[str] = await conn.run_sync(get_schema_names)
        schemas = [schema for schema in schemas if schema != "information_schema"]

        return schemas


async def _get_tables(engine: AsyncEngine, schema_name: str) -> list[str]:
    """Get all the tables in the database"""
    async with engine.connect() as conn:

        def get_schema_names(sync_conn: Any) -> list[str]:
            return list(inspect(sync_conn).get_schema_names())

        schemas: list[str] = await conn.run_sync(get_schema_names)
        tables = []
        for schema in schemas:
            if schema == schema_name:

                def get_table_names(sync_conn: Any, s: str = schema) -> list[str]:
                    return list(inspect(sync_conn).get_table_names(schema=s))

                these_tables = await conn.run_sync(get_table_names)
                tables.extend(these_tables)
        return tables


async def _get_table_schema(engine: AsyncEngine, schema_name: str, table_name: str) -> list[str]:
    """Get the schema of a table"""
    async with engine.connect() as connection:

        def get_columns(sync_conn: Any, t: str = table_name, s: str = schema_name) -> list[Any]:
            return list(inspect(sync_conn).get_columns(t, s))

        columns_table = await connection.run_sync(get_columns)

        # Get primary key information
        pk_constraint = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_pk_constraint(table_name, schema_name)
        )
        primary_keys = set(pk_constraint.get("constrained_columns", []))

        # Get index information
        indexes = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes(table_name, schema_name)
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
        result = await connection.execute(text(DatabaseEngine.sanitize_query(query)), params)
        rows = result.fetchall()
        results = [str(row) for row in rows]
        return results[:MAX_ROWS_RETURNED]
