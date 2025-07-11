import re
from typing import Any, ClassVar
from urllib.parse import urlparse

from arcade_tdk.errors import RetryableToolError
from sqlalchemy import text
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
        parsed_url = urlparse(connection_string)

        # TODO: something strange with sslmode= and friends
        # query_params = parse_qs(parsed_url.query)
        # query_params = {
        #     k: v[0] for k, v in query_params.items()
        # }  # assume one value allowed for each query param

        async_connection_string = f"{parsed_url.scheme.replace('postgresql', 'postgresql+asyncpg')}://{parsed_url.netloc}{parsed_url.path}"
        key = f"{async_connection_string}:{isolation_level}"
        if key not in cls._engines:
            cls._engines[key] = create_async_engine(
                async_connection_string,
                isolation_level=isolation_level,
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
                    developer_message="Connection to postgres failed.",
                    additional_prompt_content="Check the connection string and try again.",
                ) from e

    @classmethod
    async def get_engine(
        cls, connection_string: str, isolation_level: str = DEFAULT_ISOLATION_LEVEL
    ) -> Any:
        engine = await cls.get_instance(connection_string, isolation_level)

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
