"""Task lifecycle manager for MCP 2025-11-25 Tasks primitive.

Manages task creation, status transitions, result storage, background task
tracking, TTL-based expiration, and authorization-context-scoped isolation.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from arcade_mcp_server.types import Task, TaskStatus

logger = logging.getLogger("arcade.mcp.tasks")

TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

# Default page size for tasks/list pagination (resolved decision 38).
DEFAULT_LIST_PAGE_SIZE = 20


class NotFoundError(Exception):
    """Task not found or context mismatch (same error for both -- no info leak)."""


class InvalidTaskStateError(Exception):
    """Attempted invalid state transition on a task."""


class InvalidCursorError(Exception):
    """Cursor is malformed, unrecognized, or points at a task that no longer exists.

    Per plan resolved decision 38, invalid/expired cursors result in JSON-RPC
    -32602 (invalid params) at the handler boundary.
    """


def _encode_cursor(task: Task) -> str:
    """Opaque base64url-encoded cursor with {taskId, createdAt}.

    Resolved decision 38: cursor format is an internal detail -- clients treat
    it as an opaque string.
    """
    payload = json.dumps(
        {"taskId": task.taskId, "createdAt": task.createdAt},
        separators=(",", ":"),
        sort_keys=True,
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode a cursor issued by ``_encode_cursor``.

    Raises InvalidCursorError on any malformed input.
    """
    try:
        # base64url, tolerating missing padding
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        task_id = data["taskId"]
        created_at = data["createdAt"]
    except (binascii.Error, ValueError, UnicodeDecodeError, KeyError, TypeError) as e:
        raise InvalidCursorError("malformed cursor") from e
    if not isinstance(task_id, str) or not isinstance(created_at, str):
        raise InvalidCursorError("cursor payload has wrong types")
    return task_id, created_at


class TaskManager:
    """Manages the lifecycle of MCP tasks.

    Args:
        max_retention: Maximum TTL ceiling in milliseconds. None = unlimited.
            Default is 86_400_000 (24 hours).
        default_ttl: Default TTL in milliseconds when request omits it.
            Default is 300_000 (5 minutes).
    """

    def __init__(
        self,
        max_retention: int | None = 86_400_000,
        default_ttl: int = 300_000,
    ) -> None:
        self._max_retention = max_retention
        self._default_ttl = default_ttl

        # task_id -> (context_key, Task)
        self._tasks: dict[str, tuple[str, Task]] = {}

        # Per-task locks for atomic state transitions
        self._state_locks: dict[str, asyncio.Lock] = {}

        # Per-task events to unblock get_result waiters
        self._events: dict[str, asyncio.Event] = {}

        # Stored results (success) and errors
        self._results: dict[str, Any] = {}
        self._errors: dict[str, dict[str, Any]] = {}

        # Progress tokens for continuity (AD 6)
        self._progress_tokens: dict[str, Any] = {}

        # Tracked background asyncio.Tasks
        self._bg_tasks: dict[str, asyncio.Task[Any]] = {}

        # Periodic cleanup task (TTL expiration). Interval in seconds.
        self._cleanup_interval_seconds: float = 60.0
        self._cleanup_task: asyncio.Task[None] | None = None

        self._started = False

    async def start(self) -> None:
        """Start the task manager.

        Spawns a periodic TTL-cleanup task so that expired tasks are removed
        from memory even without explicit access. The loop runs until
        stop() cancels it.
        """
        self._started = True
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            except RuntimeError:
                # No running event loop (e.g. constructed outside async ctx);
                # lazy cleanup in get_task/list_tasks will still enforce TTL.
                self._cleanup_task = None

    async def stop(self) -> None:
        """Stop the task manager and cancel all background tasks."""
        # Stop periodic cleanup first
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            # The cleanup loop surfaces CancelledError; swallow it and any
            # unexpected shutdown-time error so stop() is always safe to call.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._cleanup_task
        self._cleanup_task = None

        # Cancel all tracked background tasks
        for _task_id, bg in list(self._bg_tasks.items()):
            if not bg.done():
                bg.cancel()
        # Wait for cancellation to propagate
        if self._bg_tasks:
            bg_list = list(self._bg_tasks.values())
            await asyncio.gather(*bg_list, return_exceptions=True)
        self._bg_tasks.clear()
        self._started = False

    async def _cleanup_loop(self) -> None:
        """Run cleanup_expired() on a fixed interval until cancelled."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_seconds)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Don't let a cleanup failure tear down the whole manager.
                # Log but keep looping so next iteration retries.
                logger.warning("TaskManager cleanup loop iteration failed", exc_info=True)

    async def create_task(
        self,
        context_key: str,
        ttl: int | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            context_key: Authorization context key scoping this task.
            ttl: Requested TTL in ms. None means "request omitted it" --
                 the handler must distinguish "not present" vs "explicitly null".

        Returns:
            The created Task with effective TTL.
        """
        # Compute effective TTL
        effective_ttl: int | None
        if ttl is not None:
            # Client provided a TTL value
            effective_ttl = ttl
            if self._max_retention is not None:
                effective_ttl = min(effective_ttl, self._max_retention)
        else:
            # Client omitted TTL -- apply default
            if self._max_retention is not None:
                effective_ttl = min(self._default_ttl, self._max_retention)
            else:
                # Operator unlimited: no default ceiling, keep None (unlimited)
                effective_ttl = None

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        task = Task(
            taskId=task_id,
            status=TaskStatus.WORKING,
            createdAt=now,
            lastUpdatedAt=now,
            ttl=effective_ttl,
        )

        self._tasks[task_id] = (context_key, task)
        self._state_locks[task_id] = asyncio.Lock()
        self._events[task_id] = asyncio.Event()

        return task

    async def get_task(self, task_id: str, context_key: str) -> Task:
        """Get a task by ID, scoped to context.

        Raises NotFoundError for missing task OR context mismatch (no info leak).
        """
        # Lazy TTL enforcement on access -- ensures expired tasks are not
        # returned even if the periodic cleanup loop is behind.
        await self.cleanup_expired()

        entry = self._tasks.get(task_id)
        if entry is None or entry[0] != context_key:
            raise NotFoundError(f"Task not found: {task_id}")
        return entry[1]

    async def list_tasks(
        self,
        context_key: str,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[Task], str | None]:
        """List tasks owned by a context key with deterministic pagination.

        Contract (resolved decision 38):
        - Ordering: ``createdAt`` descending (newest first), with ``taskId``
          ascending as tiebreaker for identical timestamps.
        - Default page size: :data:`DEFAULT_LIST_PAGE_SIZE` (20).
        - Cursor: opaque base64url-encoded ``{taskId, createdAt}`` of the last
          item on the previously-returned page.
        - Invalid or unresolvable cursors raise :class:`InvalidCursorError`;
          the handler translates that into a JSON-RPC ``-32602``.
        - Mutation semantics: best-effort; no snapshot isolation.

        Returns a tuple ``(tasks, next_cursor)``. ``next_cursor`` is ``None``
        when no further pages exist.
        """
        # Lazy TTL enforcement on access.
        await self.cleanup_expired()

        # Scope to context.
        owned = [task for ctx_key, task in self._tasks.values() if ctx_key == context_key]

        # Deterministic ordering: createdAt desc, taskId asc tiebreaker.
        # Build a sort key that inverts the primary dimension (createdAt) while
        # leaving taskId ascending. Since createdAt is an ISO-8601 string, we
        # sort ascending and then reverse via a two-pass stable sort.
        owned.sort(key=lambda t: t.taskId)  # asc tiebreaker, stable
        owned.sort(key=lambda t: t.createdAt, reverse=True)  # createdAt desc

        # Apply cursor.
        if cursor is not None:
            cur_task_id, cur_created_at = _decode_cursor(cursor)
            idx: int | None = None
            for i, t in enumerate(owned):
                if t.taskId == cur_task_id and t.createdAt == cur_created_at:
                    idx = i
                    break
            if idx is None:
                # Cursor refers to a task that no longer exists / was expired.
                raise InvalidCursorError("cursor does not match any known task")
            owned = owned[idx + 1 :]

        # Apply limit (default page size).
        effective_limit = limit if (limit is not None and limit > 0) else DEFAULT_LIST_PAGE_SIZE
        page = owned[:effective_limit]

        # Compute nextCursor only if more items remain beyond this page.
        next_cursor: str | None = None
        if len(owned) > effective_limit and page:
            next_cursor = _encode_cursor(page[-1])

        return page, next_cursor

    async def cancel_task(self, task_id: str, context_key: str) -> Task:
        """Cancel a task. Raises NotFoundError or InvalidTaskStateError."""
        # Context check
        entry = self._tasks.get(task_id)
        if entry is None or entry[0] != context_key:
            raise NotFoundError(f"Task not found: {task_id}")

        task = await self.update_status(task_id, TaskStatus.CANCELLED)

        # Also cancel the tracked asyncio.Task if present
        bg = self._bg_tasks.get(task_id)
        if bg is not None and not bg.done():
            bg.cancel()

        return task

    async def update_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        message: str | None = None,
    ) -> Task:
        """Atomically update task status.

        - If current is terminal and new==current: idempotent no-op.
        - If current is terminal and different: raise InvalidTaskStateError.
        - Otherwise update status, statusMessage, lastUpdatedAt.
        - If new status is terminal: signal the event.
        """
        lock = self._state_locks.get(task_id)
        if lock is None:
            raise NotFoundError(f"Task not found: {task_id}")

        async with lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                raise NotFoundError(f"Task not found: {task_id}")

            _ctx_key, task = entry
            current = task.status

            if current in TERMINAL_STATUSES:
                if current == new_status:
                    # Idempotent no-op
                    return task
                raise InvalidTaskStateError(
                    f"Cannot transition from {current.value} to {new_status.value}"
                )

            # Perform update
            task.status = new_status
            if message is not None:
                task.statusMessage = message
            task.lastUpdatedAt = datetime.now(timezone.utc).isoformat()

            # If terminal, signal waiters
            if new_status in TERMINAL_STATUSES:
                event = self._events.get(task_id)
                if event is not None:
                    event.set()

            return task

    async def set_result(self, task_id: str, result: Any) -> None:
        """Store a successful result for a task."""
        self._results[task_id] = result

    async def set_error(self, task_id: str, error: dict[str, Any]) -> None:
        """Store an error result for a task."""
        self._errors[task_id] = error

    async def get_result(self, task_id: str, context_key: str) -> Any:
        """Get task result, blocking until terminal if still working.

        Raises NotFoundError for missing task or context mismatch.
        """
        # Context check
        entry = self._tasks.get(task_id)
        if entry is None or entry[0] != context_key:
            raise NotFoundError(f"Task not found: {task_id}")

        _ctx_key, task = entry

        # If not terminal, wait
        if task.status not in TERMINAL_STATUSES:
            event = self._events.get(task_id)
            if event is not None:
                await event.wait()

        # Return error if present, otherwise result
        if task_id in self._errors:
            return self._errors[task_id]
        if task_id in self._results:
            return self._results[task_id]
        # Cancelled with no explicit result/error
        return {"status": "cancelled", "message": "Task was cancelled"}

    def track_background_task(self, task_id: str, bg: asyncio.Task[Any]) -> None:
        """Track a background asyncio.Task for a managed task."""
        self._bg_tasks[task_id] = bg

    def has_background_task(self, task_id: str) -> bool:
        """Check if a background asyncio.Task is tracked."""
        return task_id in self._bg_tasks

    def set_progress_token(self, task_id: str, token: Any) -> None:
        """Store the progress token for a task."""
        self._progress_tokens[task_id] = token

    def get_progress_token(self, task_id: str) -> Any:
        """Get the progress token for a task, or None."""
        return self._progress_tokens.get(task_id)

    def is_terminal(self, task_id: str) -> bool:
        """Check if a task is in a terminal state (without lock)."""
        entry = self._tasks.get(task_id)
        if entry is None:
            return True  # Non-existent tasks are considered terminal
        return entry[1].status in TERMINAL_STATUSES

    async def cleanup_expired(self) -> None:
        """Remove expired tasks based on TTL.

        Expiry = createdAt + ttl. Tasks with ttl=None never expire.
        """
        now = datetime.now(timezone.utc)
        to_remove = []

        for task_id, (_ctx_key, task) in self._tasks.items():
            if task.ttl is None:
                continue
            created = datetime.fromisoformat(task.createdAt)
            # ttl is in milliseconds
            from datetime import timedelta

            expiry = created + timedelta(milliseconds=task.ttl)
            if now >= expiry:
                to_remove.append(task_id)

        for task_id in to_remove:
            self._tasks.pop(task_id, None)
            self._state_locks.pop(task_id, None)
            self._events.pop(task_id, None)
            self._results.pop(task_id, None)
            self._errors.pop(task_id, None)
            self._progress_tokens.pop(task_id, None)
            bg = self._bg_tasks.pop(task_id, None)
            if bg is not None and not bg.done():
                bg.cancel()
