import asyncio
from collections import OrderedDict
from threading import Lock
from typing import Generic, TypeVar

from arcade_jira.constants import JIRA_CACHE_MAX_ITEMS

T = TypeVar("T")


class LRUCache(Generic[T]):
    def __init__(self, max_size: int):
        self.cache: OrderedDict[str, T] = OrderedDict()
        self.max_size = max_size
        self.thread_lock = Lock()
        self.async_lock = asyncio.Lock()

    # Thread-safe synchronous methods
    def get(self, key: str) -> T | None:
        with self.thread_lock:
            if key not in self.cache:
                return None

            value = self.cache.pop(key)
            self.cache[key] = value
            return value

    def set(self, key: str, value: T) -> None:
        with self.thread_lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = value

    # Async-safe methods
    async def async_get(self, key: str) -> T | None:
        async with self.async_lock:
            if key not in self.cache:
                return None

            value = self.cache.pop(key)
            self.cache[key] = value
            return value

    async def async_set(self, key: str, value: T) -> None:
        async with self.async_lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = value


CLOUD_ID_CACHE = LRUCache[str](max_size=JIRA_CACHE_MAX_ITEMS)
CLOUD_NAME_CACHE = LRUCache[str](max_size=JIRA_CACHE_MAX_ITEMS)
CLIENT_SEMAPHORE_CACHE = LRUCache[asyncio.Semaphore](max_size=JIRA_CACHE_MAX_ITEMS)


def get_cloud_id(auth_token: str) -> str | None:
    return CLOUD_ID_CACHE.get(auth_token)


def get_cloud_name(auth_token: str) -> str | None:
    return CLOUD_NAME_CACHE.get(auth_token)


def set_cloud_id(auth_token: str, cloud_id: str) -> None:
    CLOUD_ID_CACHE.set(auth_token, cloud_id)


def set_cloud_name(auth_token: str, cloud_name: str) -> None:
    CLOUD_NAME_CACHE.set(auth_token, cloud_name)


def get_jira_client_semaphore(auth_token: str) -> asyncio.Semaphore | None:
    return CLIENT_SEMAPHORE_CACHE.get(auth_token)


def set_jira_client_semaphore(auth_token: str, semaphore: asyncio.Semaphore) -> None:
    CLIENT_SEMAPHORE_CACHE.set(auth_token, semaphore)


async def async_get_cloud_id(auth_token: str) -> str | None:
    return await CLOUD_ID_CACHE.async_get(auth_token)


async def async_get_cloud_name(auth_token: str) -> str | None:
    return await CLOUD_NAME_CACHE.async_get(auth_token)


async def async_set_cloud_id(auth_token: str, cloud_id: str) -> None:
    await CLOUD_ID_CACHE.async_set(auth_token, cloud_id)


async def async_set_cloud_name(auth_token: str, cloud_name: str) -> None:
    await CLOUD_NAME_CACHE.async_set(auth_token, cloud_name)


async def async_get_jira_client_semaphore(auth_token: str) -> asyncio.Semaphore | None:
    return await CLIENT_SEMAPHORE_CACHE.async_get(auth_token)


async def async_set_jira_client_semaphore(auth_token: str, semaphore: asyncio.Semaphore) -> None:
    await CLIENT_SEMAPHORE_CACHE.async_set(auth_token, semaphore)
