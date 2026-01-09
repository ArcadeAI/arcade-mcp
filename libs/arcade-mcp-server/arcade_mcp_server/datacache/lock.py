from __future__ import annotations

import asyncio
import contextlib
import os
import time
import uuid
from dataclasses import dataclass

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None  # type: ignore[assignment]


class DatacacheLockError(RuntimeError):
    pass


@dataclass
class RedisLock:
    redis_url: str
    key: str
    ttl_seconds: int
    wait_seconds: int
    value: str = ""

    async def __aenter__(self) -> RedisLock:
        if redis_async is None:
            raise DatacacheLockError(
                "redis dependency not installed; required for datacache locking"
            )

        # Unique lock value so we can safely release.
        self.value = f"{os.getpid()}:{uuid.uuid4()}"
        client = redis_async.from_url(self.redis_url, decode_responses=True)

        deadline = time.time() + float(self.wait_seconds)
        try:
            while True:
                ok = await client.set(self.key, self.value, ex=self.ttl_seconds, nx=True)
                if ok:
                    self._client = client  # type: ignore[attr-defined]
                    return self
                if time.time() >= deadline:
                    break
                await asyncio.sleep(0.1)
        finally:
            if not hasattr(self, "_client"):
                with contextlib.suppress(Exception):
                    await client.aclose()

        raise DatacacheLockError(f"Timed out acquiring datacache lock: {self.key}")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        client = getattr(self, "_client", None)
        if client is None:
            return

        # Release only if value matches (Lua CAS).
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            await client.eval(lua, 1, self.key, self.value)
        finally:
            with contextlib.suppress(Exception):
                await client.aclose()
