from typing import Any, ClassVar

from arcade_tdk.errors import RetryableToolError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError

MAX_RECORDS_RETURNED = 1000
TEST_QUERY = {"ping": 1}


class DatabaseEngine:
    _instance: ClassVar[None] = None
    _clients: ClassVar[dict[str, AsyncIOMotorClient]] = {}

    @classmethod
    async def get_instance(cls, connection_string: str) -> AsyncIOMotorClient:
        key = connection_string
        if key not in cls._clients:
            cls._clients[key] = AsyncIOMotorClient(connection_string)

        # try a simple query to see if the connection is valid
        try:
            admin_db = cls._clients[key].admin
            await admin_db.command(TEST_QUERY)
            return cls._clients[key]
        except ServerSelectionTimeoutError:
            # close and try again
            cls._clients[key].close()
            cls._clients[key] = AsyncIOMotorClient(connection_string)

            try:
                admin_db = cls._clients[key].admin
                await admin_db.command(TEST_QUERY)
                return cls._clients[key]
            except Exception as e:
                raise RetryableToolError(
                    f"Connection failed: {e}",
                    developer_message="Connection to MongoDB failed.",
                    additional_prompt_content="Check the connection string and try again.",
                ) from e

    @classmethod
    async def get_database(cls, connection_string: str, database_name: str) -> Any:
        client = await cls.get_instance(connection_string)

        class DatabaseContextManager:
            def __init__(self, client: AsyncIOMotorClient, database_name: str) -> None:
                self.client = client
                self.database_name = database_name
                self.database = client[database_name]

            async def __aenter__(self) -> AsyncIOMotorDatabase:
                return self.database

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                # Connection cleanup is handled by the client cache
                pass

        return DatabaseContextManager(client, database_name)

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up all cached clients. Call this when shutting down."""
        for client in cls._clients.values():
            client.close()
        cls._clients.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache without closing clients. Use with caution."""
        cls._clients.clear()

    @classmethod
    def sanitize_query_params(
        cls,
        database_name: str,
        collection_name: str,
        filter_dict: dict[str, Any] | None,
        projection: dict[str, Any] | None,
        sort: list[dict[str, Any]] | None,
        limit: int,
        skip: int,
    ) -> tuple[
        str, str, dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None, int, int
    ]:
        if not database_name:
            raise RetryableToolError(
                "Database name is required.",
                developer_message="Database name cannot be empty.",
            )

        if not collection_name:
            raise RetryableToolError(
                "Collection name is required.",
                developer_message="Collection name cannot be empty.",
            )

        if filter_dict is None:
            filter_dict = {}

        if limit > MAX_RECORDS_RETURNED:
            raise RetryableToolError(
                f"Limit is too high. Maximum is {MAX_RECORDS_RETURNED}.",
            )

        if skip < 0:
            raise RetryableToolError(
                "Skip must be greater than or equal to 0.",
                developer_message="Skip must be greater than or equal to 0.",
            )

        if limit <= 0:
            raise RetryableToolError(
                "Limit must be greater than 0.",
                developer_message="Limit must be greater than 0.",
            )

        return database_name, collection_name, filter_dict, projection, sort, limit, skip
