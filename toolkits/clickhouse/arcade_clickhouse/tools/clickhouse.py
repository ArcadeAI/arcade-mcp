from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..database_engine import MAX_ROWS_RETURNED, DatabaseEngine


@tool(requires_secrets=["CLICKHOUSE_DATABASE_CONNECTION_STRING"])
async def discover_schemas(
    context: ToolContext,
) -> list[str]:
    """Discover all the schemas in the ClickHouse database.

    Note: ClickHouse doesn't have schemas like PostgreSQL, so this returns a default schema name.
    """
    # ClickHouse doesn't have schemas like PostgreSQL, but we return a default for compatibility
    return ["default"]


@tool(requires_secrets=["CLICKHOUSE_DATABASE_CONNECTION_STRING"])
async def discover_databases(
    context: ToolContext,
) -> list[str]:
    """Discover all the databases in the ClickHouse database."""
    async with await DatabaseEngine.get_engine(
        context.get_secret("CLICKHOUSE_DATABASE_CONNECTION_STRING")
    ) as client:
        databases = await _get_databases(client)
        return databases


@tool(requires_secrets=["CLICKHOUSE_DATABASE_CONNECTION_STRING"])
async def discover_tables(
    context: ToolContext,
) -> list[str]:
    """Discover all the tables in the ClickHouse database when the list of tables is not known.

    ALWAYS use this tool before any other tool that requires a table name.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("CLICKHOUSE_DATABASE_CONNECTION_STRING")
    ) as client:
        tables = await _get_tables(client, "default")
        return tables


@tool(requires_secrets=["CLICKHOUSE_DATABASE_CONNECTION_STRING"])
async def get_table_schema(
    context: ToolContext,
    schema_name: Annotated[str, "The schema to get the table schema of"],
    table_name: Annotated[str, "The table to get the schema of"],
) -> list[str]:
    """
    Get the schema/structure of a ClickHouse table in the ClickHouse database when the schema is not known, and the name of the table is provided.

    This tool should ALWAYS be used before executing any query.  All tables in the query must be discovered first using the <DiscoverTables> tool.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("CLICKHOUSE_DATABASE_CONNECTION_STRING")
    ) as client:
        return await _get_table_schema(client, "default", table_name)


@tool(requires_secrets=["CLICKHOUSE_DATABASE_CONNECTION_STRING"])
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
    You have a connection to a ClickHouse database.
    Execute a SELECT query and return the results against the ClickHouse database.  No other queries (INSERT, UPDATE, DELETE, etc.) are allowed.

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
    * ClickHouse is case-sensitive, so be careful with table and column names.
    """
    async with await DatabaseEngine.get_engine(
        context.get_secret("CLICKHOUSE_DATABASE_CONNECTION_STRING")
    ) as client:
        try:
            return await _execute_query(
                client,
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


async def _get_databases(client: Any) -> list[str]:
    """Get all the databases in ClickHouse"""
    # ClickHouse uses SHOW DATABASES instead of information_schema
    result = client.query("SHOW DATABASES")
    databases = [row[0] for row in result.result_rows]

    # Filter out system databases
    system_databases = {
        "system",
        "information_schema",
        "INFORMATION_SCHEMA",
        "default",
        "temporary_tables",
        "temporary_tables_metadata",
    }
    databases = [db for db in databases if db not in system_databases]
    databases.sort()

    return databases


async def _get_tables(client: Any, database_name: str) -> list[str]:
    """Get all the tables in the specified ClickHouse database"""
    # ClickHouse uses SHOW TABLES FROM database_name
    result = client.query(f"SHOW TABLES FROM {database_name}")
    tables = [row[0] for row in result.result_rows]
    tables.sort()

    return tables


async def _get_table_schema(client: Any, database_name: str, table_name: str) -> list[str]:
    """Get the schema of a ClickHouse table"""
    # ClickHouse uses DESCRIBE TABLE database_name.table_name
    result = client.query(f"DESCRIBE TABLE {database_name}.{table_name}")
    columns = result.result_rows

    # Get primary key information
    # ClickHouse doesn't have traditional primary keys like PostgreSQL
    # Instead, it has sorting keys and primary keys that are part of the table engine
    try:
        pk_result = client.query(f"SHOW CREATE TABLE {database_name}.{table_name}")
        if pk_result.result_rows:
            create_statement = pk_result.result_rows[0][0]
            # Parse the CREATE statement to extract primary key information
            primary_keys = _extract_primary_keys_from_create_statement(create_statement)
        else:
            primary_keys = set()
    except Exception:
        primary_keys = set()

    results = []
    for column in columns:
        column_name = column[
            0
        ]  # ClickHouse DESCRIBE returns: name, type, default_type, default_expression, comment, codec_expression, ttl_expression
        column_type = column[1]

        # Build column description
        description = f"{column_name}: {column_type}"

        # Add primary key indicator
        if column_name in primary_keys:
            description += " (PRIMARY KEY)"

        # Add default value if present
        if len(column) > 3 and column[3]:  # default_expression
            description += f" DEFAULT {column[3]}"

        # Add comment if present
        if len(column) > 4 and column[4]:  # comment
            description += f" COMMENT '{column[4]}'"

        results.append(description)

    return results[:MAX_ROWS_RETURNED]


def _extract_primary_keys_from_create_statement(create_statement: str) -> set[str]:
    """Extract primary key columns from ClickHouse CREATE TABLE statement"""
    primary_keys = set()

    # Look for PRIMARY KEY clause
    import re

    pk_match = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", create_statement, re.IGNORECASE)
    if pk_match:
        pk_columns = pk_match.group(1).split(",")
        for col in pk_columns:
            primary_keys.add(col.strip().strip("`"))

    # Look for ORDER BY clause (which can also indicate primary key)
    order_match = re.search(r"ORDER BY\s*\(([^)]+)\)", create_statement, re.IGNORECASE)
    if order_match:
        order_columns = order_match.group(1).split(",")
        for col in order_columns:
            primary_keys.add(col.strip().strip("`"))

    return primary_keys


async def _execute_query(
    client: Any,
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

    # For clickhouse-connect, we need to substitute parameters manually
    # since it doesn't use SQLAlchemy-style parameter binding
    formatted_query = query
    for param_name, param_value in parameters.items():
        formatted_query = formatted_query.replace(f":{param_name}", str(param_value))

    result = client.query(formatted_query)
    rows = result.result_rows
    results = [str(row) for row in rows]
    return results[:MAX_ROWS_RETURNED]
