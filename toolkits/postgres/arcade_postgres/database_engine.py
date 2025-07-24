from typing import Any, ClassVar
from urllib.parse import urlparse

from arcade_tdk.errors import RetryableToolError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

MAX_ROWS_RETURNED = 1000
TEST_QUERY = "SELECT 1"


class DatabaseEngine:
    _instance: ClassVar[None] = None
    _engines: ClassVar[dict[str, AsyncEngine]] = {}

    @classmethod
    async def get_instance(cls, connection_string: str) -> AsyncEngine:
        parsed_url = urlparse(connection_string)

        # TODO: something strange with sslmode= and friends
        # query_params = parse_qs(parsed_url.query)
        # query_params = {
        #     k: v[0] for k, v in query_params.items()
        # }  # assume one value allowed for each query param

        async_connection_string = f"{parsed_url.scheme.replace('postgresql', 'postgresql+asyncpg')}://{parsed_url.netloc}{parsed_url.path}"
        key = f"{async_connection_string}"
        if key not in cls._engines:
            cls._engines[key] = create_async_engine(async_connection_string)

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
                    developer_message="Connection to postgres failed.",
                    additional_prompt_content="Check the connection string and try again.",
                ) from e

    @classmethod
    async def get_engine(cls, connection_string: str) -> Any:
        engine = await cls.get_instance(connection_string)

        class ConnectionContextManager:
            def __init__(self, engine: AsyncEngine) -> None:
                self.engine = engine

            async def __aenter__(self) -> AsyncEngine:
                return self.engine

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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

    @classmethod
    def sanitize_query(  # noqa: C901
        cls,
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
    ) -> tuple[str, dict[str, Any]]:
        # Remove the leading keywords from the clauses if they are present
        if select_clause.strip().split(" ")[0].upper() == "SELECT":
            select_clause = select_clause.strip()[6:]

        if from_clause.strip().split(" ")[0].upper() == "FROM":
            from_clause = from_clause.strip()[4:]

        if join_clause and join_clause.strip().split(" ")[0].upper() == "JOIN":
            join_clause = join_clause.strip()[4:]

        if where_clause and where_clause.strip().split(" ")[0].upper() == "WHERE":
            where_clause = where_clause.strip()[5:]

        if group_by_clause and group_by_clause.strip().split(" ")[0].upper() == "GROUP BY":
            group_by_clause = group_by_clause.strip()[8:]

        if order_by_clause and order_by_clause.strip().split(" ")[0].upper() == "ORDER BY":
            order_by_clause = order_by_clause.strip()[8:]

        if having_clause and having_clause.strip().split(" ")[0].upper() == "HAVING":
            having_clause = having_clause.strip()[6:]

        first_select_word = select_clause.strip().split(" ")[0].upper()
        if first_select_word in [
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
            "TRUNCATE",
            "REINDEX",
            "VACUUM",
            "ANALYZE",
            "COMMENT",
        ]:
            raise RetryableToolError(
                "Only SELECT queries are allowed.",
            )

        if select_clause.strip() == "*":
            raise RetryableToolError(
                "Do not use * in the select clause.  Use a comma separated list of columns you wish to return.",
            )

        if limit > MAX_ROWS_RETURNED:
            raise RetryableToolError(
                f"Limit is too high.  Maximum is {MAX_ROWS_RETURNED}.",
            )

        if offset < 0:
            raise RetryableToolError(
                "Offset must be greater than or equal to 0.",
                developer_message="Offset must be greater than or equal to 0.",
            )

        if limit <= 0:
            raise RetryableToolError(
                "Limit must be greater than 0.",
                developer_message="Limit must be greater than 0.",
            )

        # Build query with identifiers directly interpolated, but use parameters for values
        parts = []
        if with_clause:
            parts.append(f"WITH {with_clause}")
        parts.append(f"SELECT {select_clause} FROM {from_clause}")  # noqa: S608
        if join_clause:
            parts.append(f"JOIN {join_clause}")
        if where_clause:
            parts.append(f"WHERE {where_clause}")
        if group_by_clause:
            parts.append(f"GROUP BY {group_by_clause}")
        if having_clause:
            parts.append(f"HAVING {having_clause}")
        if order_by_clause:
            parts.append(f"ORDER BY {order_by_clause}")
        parts.append("LIMIT :limit OFFSET :offset")
        query = " ".join(parts)

        # Only use parameters for values, not identifiers
        parameters = {
            "limit": limit,
            "offset": offset,
        }

        return query, parameters
