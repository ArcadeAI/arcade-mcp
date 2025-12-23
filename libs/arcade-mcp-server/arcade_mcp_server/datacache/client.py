from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from arcade_mcp_server.datacache.types import DatacacheSetResult

try:
    import duckdb  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    duckdb = None  # type: ignore[assignment]


class DatacacheClientError(RuntimeError):
    pass


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    """Validate a SQL identifier (table/column name) to avoid injection."""
    if not _IDENT_RE.match(name):
        raise DatacacheClientError(f"Invalid identifier: {name!r}")
    return name


def _now_epoch() -> int:
    return int(time.time())


@dataclass
class DatacacheClient:
    """Async-friendly DuckDB client executed on a dedicated single thread."""

    path: str
    default_ttl: int | None = None

    _executor: ThreadPoolExecutor | None = None
    _conn: Any | None = None

    @classmethod
    async def open(cls, *, path: str, default_ttl: int | None = None) -> DatacacheClient:
        if duckdb is None:
            raise DatacacheClientError("duckdb dependency not installed; required for datacache")
        self = cls(path=path, default_ttl=default_ttl)
        self._executor = ThreadPoolExecutor(max_workers=1)

        def _connect() -> Any:
            return duckdb.connect(path)

        loop = asyncio.get_running_loop()
        self._conn = await loop.run_in_executor(self._executor, _connect)
        return self

    async def aclose(self) -> None:
        if self._executor is None:
            return
        loop = asyncio.get_running_loop()

        def _close() -> None:
            try:
                if self._conn is not None:
                    self._conn.close()
            finally:
                self._conn = None

        try:
            await loop.run_in_executor(self._executor, _close)
        finally:
            self._executor.shutdown(wait=False, cancel_futures=False)
            self._executor = None

    async def _run(self, fn: Callable[[Any], Any]) -> Any:
        if self._executor is None or self._conn is None:
            raise DatacacheClientError("DatacacheClient is not open")
        loop = asyncio.get_running_loop()

        def _call() -> Any:
            return fn(self._conn)

        return await loop.run_in_executor(self._executor, _call)

    # ----------------------------
    # Discovery / query primitives
    # ----------------------------

    async def discover_databases(self) -> list[dict[str, Any]]:
        def _q(conn: Any) -> list[dict[str, Any]]:
            rows = conn.execute("PRAGMA database_list").fetchall()
            cols = [d[0] for d in conn.description]
            return [dict(zip(cols, r)) for r in rows]

        return await self._run(_q)

    async def discover_tables(self, database: str) -> list[str]:
        def _q(conn: Any) -> list[str]:
            # DuckDB uses \"main\" by default; information_schema is global.
            rows = conn.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_catalog = ?
                  AND table_schema = 'main'
                ORDER BY table_name
                """,
                [database],
            ).fetchall()
            return [r[0] for r in rows]

        return await self._run(_q)

    async def discover_schema(self, database: str, table: str) -> list[dict[str, Any]]:
        def _q(conn: Any) -> list[dict[str, Any]]:
            rows = conn.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_catalog = ?
                  AND table_schema = 'main'
                  AND table_name = ?
                ORDER BY ordinal_position
                """,
                [database, table],
            ).fetchall()
            return [{"column_name": r[0], "data_type": r[1], "is_nullable": r[2]} for r in rows]

        return await self._run(_q)

    async def query(self, database: str, table: str, sql: str) -> list[dict[str, Any]]:
        def _q(conn: Any) -> list[dict[str, Any]]:
            if not sql:
                safe_table = _ident(table)
                sql_to_run = f'SELECT * FROM "{safe_table}"'  # noqa: S608
                cur = conn.execute(sql_to_run)
            else:
                # Caller-provided SQL: treat as trusted by the tool author.
                cur = conn.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

        return await self._run(_q)

    # ----------------------------
    # Higher-level cache helpers
    # ----------------------------

    async def set(
        self,
        table_name: str,
        obj: dict[str, Any],
        *,
        id_col: str = "id",
        ttl: int | None = None,
    ) -> DatacacheSetResult:
        safe_table = _ident(table_name)
        effective_ttl = self.default_ttl if ttl is None else ttl
        if id_col not in obj:
            raise DatacacheClientError(f"Object missing id_col '{id_col}'")

        # Approximate size of what we received (pre-flattening).
        try:
            bytes_saved = len(json.dumps(obj, sort_keys=True, default=str).encode("utf-8"))
        except Exception:
            bytes_saved = len(str(obj).encode("utf-8"))

        # Flatten: top-level keys only; complex values stored as JSON.
        row: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                row[k] = json.dumps(v, sort_keys=True)
            else:
                row[k] = v

        # meta columns always present
        now = _now_epoch()
        row.setdefault("id", row.get(id_col))
        row["updated_at"] = now
        row["ttl"] = effective_ttl

        record_id = str(row.get("id"))

        def _q(conn: Any) -> tuple[str, dict[str, Any] | None]:
            # Ensure table exists with meta columns.
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{safe_table}" (
                    id VARCHAR PRIMARY KEY,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    ttl BIGINT
                )
                """
            )

            # Determine if this is an insert or update, and preserve created_at for updates.
            existing = conn.execute(
                f'SELECT created_at FROM "{safe_table}" WHERE id = ?',  # noqa: S608
                [record_id],
            ).fetchone()
            if existing is None:
                action: str = "inserted"
                row["created_at"] = now
            else:
                action = "updated"
                # Legacy safety: if an older row has NULL created_at, backfill.
                row["created_at"] = existing[0] if existing[0] is not None else now

            # Ensure user columns exist.
            existing_cols = {
                r[0]
                for r in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'main' AND table_name = ?
                    """,
                    [safe_table],
                ).fetchall()
            }
            for col in row:
                if col in existing_cols:
                    continue
                # store as VARCHAR by default (safe + flexible)
                safe_col = _ident(str(col))
                conn.execute(f'ALTER TABLE "{safe_table}" ADD COLUMN "{safe_col}" VARCHAR')

            # Upsert.
            cols = list(row.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_sql = ", ".join([f'"{_ident(str(c))}"' for c in cols])
            updates = ", ".join([
                f'"{_ident(str(c))}"=excluded."{_ident(str(c))}"' for c in cols if c != "id"
            ])
            values: Sequence[Any] = [row[c] for c in cols]
            sql_upsert = (
                f'INSERT INTO "{safe_table}" ({col_sql}) VALUES ({placeholders}) '  # noqa: S608
                f"ON CONFLICT(id) DO UPDATE SET {updates}"
            )
            conn.execute(sql_upsert, list(values))

            # Return the row we just saved.
            cur = conn.execute(f'SELECT * FROM "{safe_table}" WHERE id = ?', [record_id])  # noqa: S608
            saved = cur.fetchone()
            if saved is None:
                return action, None
            cols = [d[0] for d in cur.description]
            return action, dict(zip(cols, saved))

        action, saved_row = await self._run(_q)
        if saved_row is None:
            raise DatacacheClientError(
                "Datacache set() succeeded but could not read back saved row"
            )

        if saved_row.get("created_at") is None or saved_row.get("updated_at") is None:
            raise DatacacheClientError(
                "Datacache set() read back a row missing created_at/updated_at; this should not happen"
            )
        created_at = int(saved_row["created_at"])
        updated_at = int(saved_row["updated_at"])
        return DatacacheSetResult(
            table=table_name,
            id=record_id,
            action=action,  # type: ignore[arg-type]
            record=saved_row,
            created_at=created_at,
            updated_at=updated_at,
            bytes_saved=bytes_saved,
        )

    async def get(self, table_name: str, id: str) -> dict[str, Any] | None:  # noqa: A002
        now = _now_epoch()
        safe_table = _ident(table_name)

        def _q(conn: Any) -> dict[str, Any] | None:
            sql_get = (
                f'SELECT * FROM "{safe_table}" '  # noqa: S608
                "WHERE id = ? AND (ttl IS NULL OR ttl = 0 OR (updated_at + ttl) >= ?)"
            )
            cur = conn.execute(sql_get, [id, now])
            row = cur.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))

        return await self._run(_q)

    async def search(self, table_name: str, property: str, value: str) -> list[dict[str, Any]]:  # noqa: A002
        now = _now_epoch()
        needle = f"%{value}%"
        safe_table = _ident(table_name)
        safe_prop = _ident(property)

        def _q(conn: Any) -> list[dict[str, Any]]:
            sql_search = (
                f'SELECT * FROM "{safe_table}" '  # noqa: S608
                f'WHERE lower(CAST("{safe_prop}" AS VARCHAR)) LIKE lower(?) '
                "AND (ttl IS NULL OR ttl = 0 OR (updated_at + ttl) >= ?)"
            )
            cur = conn.execute(sql_search, [needle, now])
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

        return await self._run(_q)
