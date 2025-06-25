from typing import Annotated, Any, ClassVar

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError
from sqlalchemy import Engine, create_engine, inspect, text


class DatabaseEngine:
    _instance: ClassVar[None] = None
    _engines: ClassVar[dict[str, Engine]] = {}

    @classmethod
    def get_instance(
        cls, connection_string: str, isolation_level: str = "READ UNCOMMITTED"
    ) -> Engine:
        key = f"{connection_string}:{isolation_level}"
        if key not in cls._engines:
            cls._engines[key] = create_engine(connection_string, isolation_level=isolation_level)

        # try a simple query to see if the connection is valid
        try:
            with cls._engines[key].connect() as connection:
                connection.execute(text("SELECT 1"))
            return cls._engines[key]
        except Exception:
            cls._engines[key].dispose()

            # try again
            try:
                with cls._engines[key].connect() as connection:
                    connection.execute(text("SELECT 1"))
                return cls._engines[key]
            except Exception as e:
                raise RetryableToolError(
                    f"Connection failed: {e}",
                    developer_message=f"Connection to '{connection_string}' failed.",
                    additional_prompt_content="Check the connection string and try again.",
                    retry_after_ms=10,
                ) from e


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
def discover_tables(
    context: ToolContext,
    schema_name: Annotated[str, "The database schema to discover tables in"] = "public",
) -> list[str]:
    """Discover all the tables in the postgres database when the list of tables is not known.

    THIS TOOL SHOULD ALWAYS BE USED BEFORE ANY OTHER TOOL THAT REQUIRES A TABLE NAME.
    """
    engine = _get_engine(context.get_secret("DATABASE_CONNECTION_STRING"))
    tables = _get_tables(engine, schema_name)
    return tables


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
def get_table_schema(
    context: ToolContext,
    schema_name: Annotated[str, "The database schema to get the table schema of"],
    table_name: Annotated[str, "The table to get the schema of"],
) -> list[str]:
    """
    Get the schema of a postgres table in the postgres database when the schema is not known, and the name of the table is provided.

    THIS TOOL SHOULD ALWAYS BE USED BEFORE EXECUTING ANY QUERY.  ALL TABLES IN THE QUERY MUST BE DISCOVERED FIRST.
    """
    engine = _get_engine(context.get_secret("DATABASE_CONNECTION_STRING"))
    return _get_table_schema(engine, schema_name, table_name)


@tool(requires_secrets=["DATABASE_CONNECTION_STRING"])
def execute_query(
    context: ToolContext, query: Annotated[str, "The SQL query to execute"]
) -> list[str]:
    """
    You have a connection to a postgres database.
    Execute a query and return the results against the postgres database.  Only use this tool if you have already discovered the tables you need to query.
    """
    engine = _get_engine(context.get_secret("DATABASE_CONNECTION_STRING"))
    try:
        return _execute_query(engine, query)
    except Exception as e:
        raise RetryableToolError(
            f"Query failed: {e}",
            developer_message=f"Query '{query}' failed.",
            additional_prompt_content="Load the database schema (<GetTableSchema>) and try again.",
            retry_after_ms=10,
        ) from e


def _get_engine(connection_string: str, isolation_level: str = "READ UNCOMMITTED") -> Engine:
    """
    Get a connection to the database.
    """
    return DatabaseEngine.get_instance(connection_string, isolation_level)


def _get_tables(engine: Engine, schema_name: str) -> list[str]:
    """Get all the tables in the database"""
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    tables = []
    for schema in schemas:
        if schema == schema_name:
            tables.extend(inspector.get_table_names(schema=schema))
    return tables


def _get_table_schema(engine: Engine, schema_name: str, table_name: str) -> list[str]:
    """Get the schema of a table"""
    inspector = inspect(engine)
    columns_table = inspector.get_columns(table_name, schema_name)
    return [f"{column['name']}: {column['type'].python_type.__name__}" for column in columns_table]


def _execute_query(engine: Engine, query: str, params: dict[str, Any] | None = None) -> list[str]:
    """Execute a query and return the results."""
    with engine.connect() as connection:
        result = connection.execute(text(query), params)
        return [str(row) for row in result.fetchall()]
