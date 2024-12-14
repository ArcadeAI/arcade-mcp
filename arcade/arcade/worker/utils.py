import asyncio
from typing import Any


def is_async_callable(func: Any) -> bool:
    return asyncio.iscoroutinefunction(func) or (
        callable(func) and asyncio.iscoroutinefunction(func.__call__)
    )
