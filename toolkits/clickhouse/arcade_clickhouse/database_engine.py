import contextlib
from typing import Any, ClassVar
from urllib.parse import urlparse

import clickhouse_connect
from arcade_tdk.errors import RetryableToolError

MAX_ROWS_RETURNED = 1000
TEST_QUERY = "SELECT 1"


class DatabaseEngine:
    _instance: ClassVar[None] = None
    _clients: ClassVar[dict[str, Any]] = {}

    @classmethod
    async def get_instance(cls, connection_string: str) -> Any:
        parsed_url = urlparse(connection_string)

        # Extract connection parameters from the URL
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port
        database = parsed_url.path.lstrip("/") or "default"
        username = parsed_url.username
        password = parsed_url.password

        # Handle different ClickHouse protocols
        # clickhouse-connect only supports HTTP and HTTPS interfaces
        if parsed_url.scheme in ["clickhouse+native"]:
            # Convert native protocol to HTTP for clickhouse-connect compatibility
            # Convert native port 9000 to HTTP port 8123
            port = 8123 if port == 9000 else port or 8123
            interface = "http"
        elif parsed_url.scheme in ["clickhouse+https"]:
            # For HTTPS protocol
            port = port or 8443
            interface = "https"
        else:
            # For HTTP or unspecified, use port 8123 by default
            port = port or 8123
            interface = "http"

        key = f"{interface}://{host}:{port}/{database}"

        if key not in cls._clients:
            try:
                # Create ClickHouse client
                client_args: dict[str, Any] = {
                    "host": host,
                    "port": port,
                    "database": database,
                    "interface": interface,
                }

                if username:
                    client_args["username"] = username
                if password:
                    client_args["password"] = password

                client = clickhouse_connect.get_client(**client_args)
                cls._clients[key] = client

                # Test the connection
                client.command(TEST_QUERY)

            except Exception as e:
                # Remove failed client from cache
                cls._clients.pop(key, None)
                raise RetryableToolError(
                    f"Connection failed: {e}",
                    developer_message="Connection to ClickHouse failed.",
                    additional_prompt_content="Check the connection string and try again.",
                ) from e

        return cls._clients[key]

    @classmethod
    async def get_engine(cls, connection_string: str) -> Any:
        client = await cls.get_instance(connection_string)

        class ConnectionContextManager:
            def __init__(self, client: Any) -> None:
                self.client = client

            async def __aenter__(self) -> Any:
                return self.client

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                # Connection cleanup is handled by clickhouse-connect
                pass

        return ConnectionContextManager(client)

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up all cached clients. Call this when shutting down."""
        for client in cls._clients.values():
            with contextlib.suppress(Exception):
                client.close()
        cls._clients.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache without disposing clients. Use with caution."""
        cls._clients.clear()

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
            "OPTIMIZE",  # ClickHouse-specific
            "SYSTEM",  # ClickHouse-specific
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
