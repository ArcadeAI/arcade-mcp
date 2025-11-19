import asyncio
import threading
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class TaskTrackerMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks active HTTP request tasks for force quit functionality."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._active_tasks: set[asyncio.Task] = set()
        self._lock = threading.Lock()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Track the current task while handling the request."""
        task = asyncio.current_task()

        with self._lock:
            if task:
                self._active_tasks.add(task)

        try:
            response = await call_next(request)
            return response
        finally:
            with self._lock:
                if task:
                    self._active_tasks.discard(task)

    def cancel_all_tasks(self) -> int:
        """
        Cancel all tracked (active) HTTP request tasks.

        This method must be called from within the asyncio event loop's thread
        (not from background thread) because it calls task.cancel()

        Returns:
            int: Number of tasks successfully cancelled.
        """
        # Make a copy to avoid mutation during iteration
        with self._lock:
            tasks_to_cancel = list(self._active_tasks)

        cancelled_count = 0
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
                cancelled_count += 1

        return cancelled_count
