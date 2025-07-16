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
    def sanitize_query(cls, query: str) -> str:
        """
        Sanitize a query to not break our read-only session.
        THIS IS REALLY UNSAFE AND SHOULD NOT BE USED IN PRODUCTION. USE A DATABASE CONNECTION WITH A READ-ONLY USER AND PREPARE STATEMENTS.
        There are also valid reasons for the ";" character, and this prevents that.
        """

        parts = query.split(";")
        if len(parts) > 1:
            raise RetryableToolError(
                "Multiple statements are not allowed in a single query.",
                developer_message="Multiple statements are not allowed in a single query.",
                additional_prompt_content="Split your query into multiple queries and try again.",
            )

        words = parts[0].split(" ")
        if words[0].upper().strip() != "SELECT":
            raise RetryableToolError(
                "Only SELECT queries are allowed.",
                developer_message="Only SELECT queries are allowed.",
                additional_prompt_content="Use the <DiscoverTables> and <GetTableSchema> tools to discover the tables and try again.",
            )

        return f"{query}"
