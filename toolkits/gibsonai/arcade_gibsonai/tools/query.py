from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..api_client import GibsonAIClient


@tool(requires_secrets=["GIBSONAI_API_KEY"])
async def execute_query(
    context: ToolContext,
    query: Annotated[
        str,
        "The SQL query to execute against GibsonAI project database. Supports all SQL operations including SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.",
    ],
) -> list[str]:
    """
    Execute a SQL query and return the results from the GibsonAI project relational database.

    This tool supports all SQL operations including:
    * SELECT queries for data retrieval
    * INSERT, UPDATE, DELETE for data manipulation
    * CREATE, ALTER, DROP for schema management
    * Any other valid SQL statements

    When running queries, follow these rules which will help avoid errors:
    * First discover the database schema in the GibsonAI project database when schema is not known.
    * Discover all the tables in the database when the list of tables is not known.
    * Always use case-insensitive queries to match strings in the query.
    * Always trim strings in the query.
    * Prefer LIKE queries over direct string matches or regex queries.
    * Only join on columns that are indexed or the primary key.

    For SELECT queries, unless otherwise specified, ensure that query has a LIMIT of 100 for all results.
    """
    api_key = context.get_secret("GIBSONAI_API_KEY")
    client = GibsonAIClient(api_key)

    try:
        results = await client.execute_query(query)
        return results
    except Exception as e:
        raise RetryableToolError(
            f"Query failed: {e}",
            developer_message=f"Query '{query}' failed against GibsonAI database.",
            additional_prompt_content="Please check your query syntax and try again.",
            retry_after_ms=10,
        ) from e
