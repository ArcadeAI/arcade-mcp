import asyncio
import threading

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TaskTrackerMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks active HTTP request tasks for force quit functionality."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._active_tasks: set[asyncio.Task] = set()
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
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

    def cancel_all_tasks(self):
        """
        Cancel all tracked tasks.
        MUST be called from event loop context (or via call_soon_threadsafe).
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
