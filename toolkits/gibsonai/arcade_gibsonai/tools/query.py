import re
from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import RetryableToolError

from ..api_client import GibsonAIClient


def _is_read_only_query(query: str) -> bool:
    """Check if a query is read-only (only SELECT, SHOW, DESCRIBE, EXPLAIN operations)."""
    # Remove comments and normalize whitespace
    normalized_query = re.sub(r"--.*?$|/\*.*?\*/", "", query, flags=re.MULTILINE | re.DOTALL)
    normalized_query = " ".join(normalized_query.strip().split())

    # Check if query starts with read-only operations
    read_only_patterns = [
        r"^\s*SELECT\s",
        r"^\s*SHOW\s",
        r"^\s*DESCRIBE\s",
        r"^\s*DESC\s",
        r"^\s*EXPLAIN\s",
        r"^\s*WITH\s.*SELECT\s",  # CTE with SELECT
    ]

    return any(re.match(pattern, normalized_query, re.IGNORECASE) for pattern in read_only_patterns)


@tool(requires_secrets=["GIBSONAI_API_KEY"])
async def execute_read_query(
    context: ToolContext,
    query: Annotated[
        str,
        "The read-only SQL query to execute against GibsonAI project database. "
        "Only SELECT, SHOW, DESCRIBE, and EXPLAIN operations are permitted.",
    ],
) -> list[str]:
    """
    Execute a read-only SQL query and return the results from the GibsonAI
    project relational database.

    This tool supports only read operations including:
    * SELECT queries for data retrieval
    * SHOW commands for metadata inspection
    * DESCRIBE/DESC commands for table structure
    * EXPLAIN commands for query analysis
    * WITH clauses (Common Table Expressions) that contain SELECT operations

    When running queries, follow these rules which will help avoid errors:
    * First discover the database schema in the GibsonAI project database when
      schema is not known.
    * Discover all the tables in the database when the list of tables is not
      known.
    * Always use case-insensitive queries to match strings in the query.
    * Always trim strings in the query.
    * Prefer LIKE queries over direct string matches or regex queries.
    * Only join on columns that are indexed or the primary key.

    For SELECT queries, unless otherwise specified, ensure that query has a
    LIMIT of 100 for all results.
    """
    # Validate that the query is read-only
    if not _is_read_only_query(query):
        raise RetryableToolError(
            "Only read-only queries (SELECT, SHOW, DESCRIBE, EXPLAIN) are permitted",
            developer_message=f"Query '{query}' contains write operations which are not allowed.",
            additional_prompt_content=(
                "Please use the appropriate DML/DDL tools for data modification operations."
            ),
            retry_after_ms=0,
        )

    api_key = context.get_secret("GIBSONAI_API_KEY")
    client = GibsonAIClient(api_key)

    try:
        results = await client.execute_query(query)
    except Exception as e:
        raise RetryableToolError(
            f"Query failed: {e}",
            developer_message=f"Query '{query}' failed against GibsonAI database.",
            additional_prompt_content="Please check your query syntax and try again.",
            retry_after_ms=10,
        ) from e
    else:
        return results
