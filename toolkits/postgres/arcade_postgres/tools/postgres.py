from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from ..database_engine import MAX_ROWS_RETURNED, DatabaseEngine


@tool(requires_secrets=["POSTGRES_DATABASE_CONNECTION_STRING"])
async def discover_schemas(
    context: ToolContext,
) -> list[str]:
    """Discover all the schemas in the postgres database."""
    async with await DatabaseEngine.get_engine(
        context.get_secret("POSTGRES_DATABASE_CONNECTION_STRING")
    ) as engine:
        schemas = await _get_schemas(engine)
        return schemas


@tool(requires_secrets=["POSTGRES_DATABASE_CONNECTION_STRING"])
async def discover_tables(
    context: ToolContext,
    schema_name: Annotated[
        str, "The database schema to discover tables in (default value: 'public')"
    ] = "public",
) -> list[str]:
    """Discover all the tables in the postgres database when the list of tables is not known.

    ALWAYS use this tool before any other tool that requires a table name.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("POSTGRES_DATABASE_CONNECTION_STRING")
    ) as engine:
        tables = await _get_tables(engine, schema_name)
        return tables


@tool(requires_secrets=["POSTGRES_DATABASE_CONNECTION_STRING"])
async def get_table_schema(
    context: ToolContext,
    schema_name: Annotated[str, "The database schema to get the table schema of"],
    table_name: Annotated[str, "The table to get the schema of"],
) -> list[str]:
    """
    Get the schema/structure of a postgres table in the postgres database when the schema is not known, and the name of the table is provided.

    This tool should ALWAYS be used before executing any query.  All tables in the query must be discovered first using the <DiscoverTables> tool.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("POSTGRES_DATABASE_CONNECTION_STRING")
    ) as engine:
        return await _get_table_schema(engine, schema_name, table_name)


@tool(requires_secrets=["POSTGRES_DATABASE_CONNECTION_STRING"])
async def execute_select_query(
    context: ToolContext,
    select_clause: Annotated[
        str,
        "This is the part of the SQL query that comes after the SELECT keyword wish a comma separated list of columns you wish to return.  Do not include the SELECT keyword.",
    ],
    from_clause: Annotated[
        str,
        "This is the part of the SQL query that comes after the FROM keyword.  Do not include the FROM keyword.",
    ],
    limit: Annotated[
        int,
        "The maximum number of rows to return.  This is the LIMIT clause of the query.  Default: 100.",
    ] = 100,
    offset: Annotated[
        int, "The number of rows to skip.  This is the OFFSET clause of the query.  Default: 0."
    ] = 0,
    join_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the JOIN keyword.  Do not include the JOIN keyword.  If no join is needed, leave this blank.",
    ] = None,
    where_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the WHERE keyword.  Do not include the WHERE keyword.  If no where clause is needed, leave this blank.",
    ] = None,
    having_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the HAVING keyword.  Do not include the HAVING keyword.  If no having clause is needed, leave this blank.",
    ] = None,
    group_by_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the GROUP BY keyword.  Do not include the GROUP BY keyword.  If no group by clause is needed, leave this blank.",
    ] = None,
    order_by_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the ORDER BY keyword.  Do not include the ORDER BY keyword.  If no order by clause is needed, leave this blank.",
    ] = None,
    with_clause: Annotated[
        str | None,
        "This is the part of the SQL query that comes after the WITH keyword when basing the query on a virtual table.  If no WITH clause is needed, leave this blank.",
    ] = None,
) -> list[str]:
    """
    You have a connection to a postgres database.
    Execute a SELECT query and return the results against the postgres database.  No other queries (INSERT, UPDATE, DELETE, etc.) are allowed.

    ONLY use this tool if you have already loaded the schema of the tables you need to query.  Use the <GetTableSchema> tool to load the schema if not already known.

    The final query will be constructed as follows:
    SELECT {select_query_part} FROM {from_clause} JOIN {join_clause} WHERE {where_clause} HAVING {having_clause} ORDER BY {order_by_clause} LIMIT {limit} OFFSET {offset}

    When running queries, follow these rules which will help avoid errors:
    * Never "select *" from a table.  Always select the columns you need.
    * Always order your results by the most important columns first.  If you aren't sure, order by the primary key.
    * Always use case-insensitive queries to match strings in the query.
    * Always trim strings in the query.
    * Prefer LIKE queries over direct string matches or regex queries.
    * Only join on columns that are indexed or the primary key.  Do not join on arbitrary columns.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("POSTGRES_DATABASE_CONNECTION_STRING")
    ) as engine:
        try:
            return await _execute_query(
                engine,
                select_clause=select_clause,
                from_clause=from_clause,
                limit=limit,
                offset=offset,
                join_clause=join_clause,
                where_clause=where_clause,
                having_clause=having_clause,
                group_by_clause=group_by_clause,
                order_by_clause=order_by_clause,
                with_clause=with_clause,
            )
        except Exception as e:
            raise RetryableToolError(
                f"Query failed: {e}",
                developer_message=f"Query failed with parameters: select_clause={select_clause}, from_clause={from_clause}, limit={limit}, offset={offset}, join_clause={join_clause}, where_clause={where_clause}, having_clause={having_clause}, order_by_clause={order_by_clause}, with_clause={with_clause}.",
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

        tables.sort()
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
    engine: AsyncEngine,
    select_clause: str,
    from_clause: str,
    limit: int,
    offset: int,
    join_clause: str | None,
    where_clause: str | None,
    having_clause: str | None,
    group_by_clause: str | None,
    order_by_clause: str | None,
    with_clause: str | None,
) -> list[str]:
    """Execute a query and return the results."""
    async with engine.connect() as connection:
        query, parameters = DatabaseEngine.sanitize_query(
            select_clause=select_clause,
            from_clause=from_clause,
            limit=limit,
            offset=offset,
            join_clause=join_clause,
            where_clause=where_clause,
            having_clause=having_clause,
            group_by_clause=group_by_clause,
            order_by_clause=order_by_clause,
            with_clause=with_clause,
        )
        print(f"Query: {query}")
        print(f"Parameters: {parameters}")
        result = await connection.execute(text(query), parameters)
        rows = result.fetchall()
        results = [str(row) for row in rows]
        return results[:MAX_ROWS_RETURNED]
