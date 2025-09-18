"""
Base Async Managers

Provides async-safe registries with RW locking, versioning, and subscriptions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Any, Generic, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")


class AsyncRWLock:
    """Simple async RW lock allowing concurrent readers and exclusive writers."""

    def __init__(self) -> None:
        self._reader_count = 0
        self._reader_lock = asyncio.Lock()
        self._gate = asyncio.Lock()

    async def read(self) -> Any:
        class _ReadCtx:
            async def __aenter__(_self) -> None:
                async with self._reader_lock:
                    self._reader_count += 1
                    if self._reader_count == 1:
                        await self._gate.acquire()

            async def __aexit__(
                _self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: TracebackType | None,
            ) -> None:
                async with self._reader_lock:
                    self._reader_count -= 1
                    if self._reader_count == 0:
                        self._gate.release()

        return _ReadCtx()

    async def write(self) -> Any:
        class _WriteCtx:
            async def __aenter__(_self) -> None:
                await self._gate.acquire()

            async def __aexit__(
                _self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: TracebackType | None,
            ) -> None:
                self._gate.release()

        return _WriteCtx()


class AsyncRegistry(Generic[K, V]):
    """Async-safe registry with deterministic listing and change notifications."""

    def __init__(self, component: str) -> None:
        self.component = component
        self._items: dict[K, V] = {}
        self._lock = AsyncRWLock()
        self._version = 0
        self._subscribers: list[Callable[[str, K | None, V | None, V | None, int], None]] = []

    def subscribe(self, fn: Callable[[str, K | None, V | None, V | None, int], None]) -> None:
        self._subscribers.append(fn)

    async def get(self, key: K) -> V:
        async with await self._lock.read():
            if key not in self._items:
                raise KeyError(f"{self.component.title()} '{key}' not found")
            return self._items[key]

    async def keys(self) -> list[K]:
        async with await self._lock.read():
            return sorted(self._items.keys(), key=lambda k: str(k))

    async def list(self) -> list[V]:
        async with await self._lock.read():
            return [self._items[k] for k in sorted(self._items.keys(), key=lambda k: str(k))]

    async def upsert(self, key: K, value: V) -> None:
        async with await self._lock.write():
            old = self._items.get(key)
            self._items[key] = value
            self._version += 1
            version = self._version
        for fn in self._subscribers:
            fn("upsert", key, old, value, version)

    async def remove(self, key: K) -> V:
        async with await self._lock.write():
            if key not in self._items:
                raise KeyError(f"{self.component.title()} '{key}' not found")
            old = self._items.pop(key)
            self._version += 1
            version = self._version
        for fn in self._subscribers:
            fn("remove", key, old, None, version)
        return old

    async def bulk_load(self, items: Iterable[tuple[K, V]]) -> None:
        async with await self._lock.write():
            for k, v in items:
                self._items[k] = v
            self._version += 1
            version = self._version
        for fn in self._subscribers:
            fn("bulk_load", cast(K, None), None, None, version)

    @property
    def version(self) -> int:
        return self._version


class ComponentManager(Generic[K, V]):
    """Base component manager with lifecycle and async registry."""

    def __init__(self, component: str) -> None:
        self.registry: AsyncRegistry[K, V] = AsyncRegistry(component)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False

    def subscribe(self, fn: Callable[[str, K | None, V | None, V | None, int], None]) -> None:
        self.registry.subscribe(fn)

    @property
    def version(self) -> int:
        return self.registry.version
