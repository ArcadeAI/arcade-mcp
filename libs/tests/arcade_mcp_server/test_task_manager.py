"""Tests for TaskManager (Phase 4 of MCP 2025-11-25 support)."""

import asyncio
import base64
import contextlib
import json

import pytest
import pytest_asyncio
from arcade_mcp_server.managers.task_manager import (
    DEFAULT_LIST_PAGE_SIZE,
    InvalidCursorError,
    InvalidTaskStateError,
    NotFoundError,
    TaskManager,
    _decode_cursor,
    _encode_cursor,
)
from arcade_mcp_server.types import TaskStatus

CONTEXT_A = "auth:https://issuer.example.com:client-app:alice"
CONTEXT_B = "auth:https://issuer.example.com:client-app:bob"
CONTEXT_STDIO = "session:s1"


class TestTaskManager:
    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_create_task(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A, ttl=60000)
        assert task.taskId is not None
        assert task.status == TaskStatus.WORKING
        assert task.ttl == 60000

    @pytest.mark.asyncio
    async def test_get_task(self, task_manager):
        created = await task_manager.create_task(context_key=CONTEXT_A)
        retrieved = await task_manager.get_task(created.taskId, context_key=CONTEXT_A)
        assert retrieved.taskId == created.taskId

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_raises(self, task_manager):
        with pytest.raises(NotFoundError):
            await task_manager.get_task("nonexistent", context_key=CONTEXT_A)

    @pytest.mark.asyncio
    async def test_get_task_wrong_context_raises(self, task_manager):
        """Task created by context A is not visible to context B (authorization isolation)."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        with pytest.raises(NotFoundError):
            await task_manager.get_task(task.taskId, context_key=CONTEXT_B)

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_context_raises(self, task_manager):
        """Task created by context A cannot be cancelled by context B."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        with pytest.raises(NotFoundError):
            await task_manager.cancel_task(task.taskId, context_key=CONTEXT_B)

    @pytest.mark.asyncio
    async def test_list_tasks_scoped_to_context(self, task_manager):
        """list_tasks only returns tasks belonging to the requesting authorization context."""
        t1 = await task_manager.create_task(context_key=CONTEXT_A)
        t2 = await task_manager.create_task(context_key=CONTEXT_B)
        tasks_a, _ = await task_manager.list_tasks(context_key=CONTEXT_A)
        tasks_b, _ = await task_manager.list_tasks(context_key=CONTEXT_B)
        assert len(tasks_a) == 1
        assert tasks_a[0].taskId == t1.taskId
        assert len(tasks_b) == 1
        assert tasks_b[0].taskId == t2.taskId

    @pytest.mark.asyncio
    async def test_update_task_status(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        updated = await task_manager.update_status(task.taskId, TaskStatus.COMPLETED, "Done")
        assert updated.status == TaskStatus.COMPLETED
        assert updated.statusMessage == "Done"

    @pytest.mark.asyncio
    async def test_update_terminal_task_raises(self, task_manager):
        """Cannot update status of a completed/failed/cancelled task."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        with pytest.raises(InvalidTaskStateError):
            await task_manager.update_status(task.taskId, TaskStatus.WORKING)

    @pytest.mark.asyncio
    async def test_cancel_task(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        cancelled = await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        assert cancelled.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_terminal_task_raises(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        with pytest.raises(InvalidTaskStateError):
            await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)

    @pytest.mark.asyncio
    async def test_task_status_transitions(self, task_manager):
        """Valid transitions: working -> input_required -> working -> completed."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.INPUT_REQUIRED)
        t = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert t.status == TaskStatus.INPUT_REQUIRED
        await task_manager.update_status(task.taskId, TaskStatus.WORKING)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        t = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert t.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_last_updated_at_changes_on_update(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        original_updated = task.lastUpdatedAt
        await asyncio.sleep(0.01)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        updated = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert updated.lastUpdatedAt != original_updated

    @pytest.mark.asyncio
    async def test_list_tasks(self, task_manager):
        t1 = await task_manager.create_task(context_key=CONTEXT_A)
        t2 = await task_manager.create_task(context_key=CONTEXT_A)
        tasks, next_cursor = await task_manager.list_tasks(context_key=CONTEXT_A)
        assert len(tasks) >= 2
        task_ids = {t.taskId for t in tasks}
        assert t1.taskId in task_ids
        assert t2.taskId in task_ids
        # Only 2 tasks, default page size is 20, so there's no next page.
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, task_manager):
        tasks, next_cursor = await task_manager.list_tasks(context_key=CONTEXT_A)
        assert tasks == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_task_ttl_expiration(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A, ttl=1)  # 1ms TTL
        await asyncio.sleep(0.05)
        await task_manager.cleanup_expired()
        with pytest.raises(NotFoundError):
            await task_manager.get_task(task.taskId, context_key=CONTEXT_A)

    @pytest.mark.asyncio
    async def test_task_default_ttl_when_not_specified(self, task_manager):
        """When ttl is omitted from request, server applies default TTL."""
        task = await task_manager.create_task(context_key=CONTEXT_A)  # no ttl
        assert task.ttl is not None  # server applied default
        assert task.ttl > 0

    @pytest.mark.asyncio
    async def test_task_ttl_capped_at_max_retention(self, task_manager):
        """When requested TTL exceeds _max_retention, effective TTL is capped."""
        # Default _max_retention is 86400000 (24h)
        task = await task_manager.create_task(context_key=CONTEXT_A, ttl=200_000_000)  # > 24h
        assert task.ttl == task_manager._max_retention  # capped to 24h

    @pytest.mark.asyncio
    async def test_task_default_ttl_is_always_integer(self, task_manager):
        """With default _max_retention configured, Task.ttl is NEVER null."""
        task = await task_manager.create_task(context_key=CONTEXT_A)  # no ttl
        assert task.ttl is not None
        assert isinstance(task.ttl, int)
        assert task.ttl > 0

    @pytest.mark.asyncio
    async def test_task_unlimited_ttl_only_when_max_retention_none(self):
        """Task.ttl=None (unlimited) is ONLY reported when _max_retention is None."""
        manager = TaskManager(max_retention=None)
        await manager.start()
        try:
            task = await manager.create_task(context_key=CONTEXT_A, ttl=None)
            assert task.ttl is None  # genuinely unlimited
            await manager.cleanup_expired()
            # Should still exist
            retrieved = await manager.get_task(task.taskId, context_key=CONTEXT_A)
            assert retrieved.taskId == task.taskId
        finally:
            await manager.stop()


class TestTaskManagerResultBlocking:
    """Tests for tasks/result blocking semantics."""

    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_set_and_get_result_after_completion(self, task_manager):
        """get_result on a completed task returns immediately."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        result_data = {"content": [{"type": "text", "text": "done"}], "isError": False}
        await task_manager.set_result(task.taskId, result_data)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        result = await task_manager.get_result(task.taskId, context_key=CONTEXT_A)
        assert result == result_data

    @pytest.mark.asyncio
    async def test_get_result_blocks_until_terminal_status(self, task_manager):
        """get_result on a working task blocks until terminal status."""
        task = await task_manager.create_task(context_key=CONTEXT_A)

        async def complete_later():
            await asyncio.sleep(0.1)
            await task_manager.set_result(task.taskId, {"done": True})
            await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(complete_later())
            result = await asyncio.wait_for(
                task_manager.get_result(task.taskId, context_key=CONTEXT_A), timeout=5.0
            )
        assert result == {"done": True}

    @pytest.mark.asyncio
    async def test_get_result_returns_error_for_failed_task(self, task_manager):
        """tasks/result for a failed task returns the JSON-RPC error response."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        error_data = {"code": -32603, "message": "Tool execution failed"}
        await task_manager.set_error(task.taskId, error_data)
        await task_manager.update_status(task.taskId, TaskStatus.FAILED)
        result = await task_manager.get_result(task.taskId, context_key=CONTEXT_A)
        assert result["code"] == -32603

    @pytest.mark.asyncio
    async def test_get_result_for_cancelled_task(self, task_manager):
        """tasks/result for a cancelled task returns cancellation response."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        result = await task_manager.get_result(task.taskId, context_key=CONTEXT_A)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_result_wrong_context_raises(self, task_manager):
        """Cannot retrieve result for a task owned by another authorization context."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.set_result(task.taskId, {"done": True})
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        with pytest.raises(NotFoundError):
            await task_manager.get_result(task.taskId, context_key=CONTEXT_B)


class TestTaskManagerBackgroundTracking:
    """Tests for asyncio.Task tracking and lifecycle."""

    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_track_background_task(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        bg = asyncio.create_task(asyncio.sleep(10))
        task_manager.track_background_task(task.taskId, bg)
        assert task_manager.has_background_task(task.taskId)
        bg.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bg

    @pytest.mark.asyncio
    async def test_cancel_task_cancels_background_asyncio_task(self, task_manager):
        """Cancelling a task via tasks/cancel cancels the tracked asyncio.Task."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        cancelled_flag = asyncio.Event()

        async def long_running():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled_flag.set()
                raise

        bg = asyncio.create_task(long_running())
        task_manager.track_background_task(task.taskId, bg)
        # Yield to let the background task start
        await asyncio.sleep(0)
        await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        # Give event loop a chance to propagate cancellation
        await asyncio.sleep(0.01)
        await asyncio.wait_for(cancelled_flag.wait(), timeout=2.0)
        assert cancelled_flag.is_set()

    @pytest.mark.asyncio
    async def test_stop_cancels_all_background_tasks(self, task_manager):
        """TaskManager.stop() cancels all running background tasks."""
        t1 = await task_manager.create_task(context_key=CONTEXT_A)
        t2 = await task_manager.create_task(context_key=CONTEXT_A)
        bg1 = asyncio.create_task(asyncio.sleep(60))
        bg2 = asyncio.create_task(asyncio.sleep(60))
        task_manager.track_background_task(t1.taskId, bg1)
        task_manager.track_background_task(t2.taskId, bg2)
        await task_manager.stop()
        assert bg1.cancelled() or bg1.done()
        assert bg2.cancelled() or bg2.done()


class TestTaskCancellationRace:
    """Tests for atomic state transitions and cancellation race handling."""

    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_cancel_then_complete_stays_cancelled(self, task_manager):
        """If cancel wins the race, subsequent complete attempt must not change status."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        with pytest.raises(InvalidTaskStateError):
            await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        t = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert t.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_then_fail_stays_cancelled(self, task_manager):
        """If cancel wins the race, subsequent fail attempt must not change status."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        with pytest.raises(InvalidTaskStateError):
            await task_manager.update_status(task.taskId, TaskStatus.FAILED)
        t = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert t.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_complete_then_cancel_stays_completed(self, task_manager):
        """If complete wins the race, subsequent cancel must fail."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        with pytest.raises(InvalidTaskStateError):
            await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)

    @pytest.mark.asyncio
    async def test_concurrent_cancel_and_complete(self, task_manager):
        """Concurrent cancel and complete -- exactly one succeeds, status is terminal."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        results = []

        async def try_cancel():
            try:
                await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
                results.append("cancelled")
            except InvalidTaskStateError:
                results.append("cancel_failed")

        async def try_complete():
            try:
                await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
                results.append("completed")
            except InvalidTaskStateError:
                results.append("complete_failed")

        await asyncio.gather(try_cancel(), try_complete())
        t = await task_manager.get_task(task.taskId, context_key=CONTEXT_A)
        assert t.status in {TaskStatus.CANCELLED, TaskStatus.COMPLETED}
        # Exactly one succeeded
        assert ("cancelled" in results) != ("completed" in results)

    @pytest.mark.asyncio
    async def test_update_status_idempotent_same_terminal(self, task_manager):
        """Setting the same terminal status twice is idempotent (no error)."""
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        result = await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        assert result.status == TaskStatus.COMPLETED


class TestTaskProgressTokenContinuity:
    """Tests for progress token persistence across task lifetime."""

    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_progress_token_stored_on_create(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        task_manager.set_progress_token(task.taskId, "pt-123")
        assert task_manager.get_progress_token(task.taskId) == "pt-123"

    @pytest.mark.asyncio
    async def test_progress_token_none_when_not_set(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        assert task_manager.get_progress_token(task.taskId) is None

    @pytest.mark.asyncio
    async def test_progress_token_survives_status_changes(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        task_manager.set_progress_token(task.taskId, "pt-456")
        await task_manager.update_status(task.taskId, TaskStatus.INPUT_REQUIRED)
        assert task_manager.get_progress_token(task.taskId) == "pt-456"
        await task_manager.update_status(task.taskId, TaskStatus.WORKING)
        assert task_manager.get_progress_token(task.taskId) == "pt-456"


class TestTaskProgressTerminalStop:
    """Tests for progress.mdx:73: Progress notifications for tasks MUST stop
    after the task reaches a terminal status."""

    @pytest_asyncio.fixture
    async def task_manager(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_is_terminal_false_for_working(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        assert not task_manager.is_terminal(task.taskId)

    @pytest.mark.asyncio
    async def test_is_terminal_true_for_completed(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        assert task_manager.is_terminal(task.taskId)

    @pytest.mark.asyncio
    async def test_is_terminal_true_for_failed(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.update_status(task.taskId, TaskStatus.FAILED)
        assert task_manager.is_terminal(task.taskId)

    @pytest.mark.asyncio
    async def test_is_terminal_true_for_cancelled(self, task_manager):
        task = await task_manager.create_task(context_key=CONTEXT_A)
        await task_manager.cancel_task(task.taskId, context_key=CONTEXT_A)
        assert task_manager.is_terminal(task.taskId)


class TestLazyAndPeriodicExpiration:
    """Verify cleanup_expired() is invoked on access (lazy) and by a periodic
    background task (eager). These guard against the implementation regressing
    back to 'cleanup_expired defined but never called'."""

    @pytest.mark.asyncio
    async def test_get_task_triggers_lazy_cleanup(self):
        manager = TaskManager()
        await manager.start()
        try:
            task = await manager.create_task(context_key=CONTEXT_A, ttl=1)  # 1ms
            await asyncio.sleep(0.05)
            # Accessing an EXPIRED task must raise NotFoundError (proving
            # cleanup was run before the lookup).
            with pytest.raises(NotFoundError):
                await manager.get_task(task.taskId, context_key=CONTEXT_A)
            # The task must have been actually removed from the internal map.
            assert task.taskId not in manager._tasks
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_list_tasks_triggers_lazy_cleanup(self):
        manager = TaskManager()
        await manager.start()
        try:
            expired = await manager.create_task(context_key=CONTEXT_A, ttl=1)
            fresh = await manager.create_task(context_key=CONTEXT_A, ttl=60_000)
            await asyncio.sleep(0.05)
            listed, _ = await manager.list_tasks(context_key=CONTEXT_A)
            ids = {t.taskId for t in listed}
            assert fresh.taskId in ids
            assert expired.taskId not in ids
            # Expired task must be gone from the map.
            assert expired.taskId not in manager._tasks
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_periodic_cleanup_task_runs(self):
        """Periodic cleanup task removes expired tasks without explicit access."""
        manager = TaskManager()
        # Use a very short interval for testing
        manager._cleanup_interval_seconds = 0.05
        await manager.start()
        try:
            assert manager._cleanup_task is not None
            assert not manager._cleanup_task.done()
            task = await manager.create_task(context_key=CONTEXT_A, ttl=1)  # 1ms
            # Wait long enough for the periodic loop to fire at least once.
            await asyncio.sleep(0.2)
            # Task should have been removed by the periodic cleanup loop
            # without any access to get_task/list_tasks.
            assert task.taskId not in manager._tasks
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent_for_cleanup_task(self):
        """Calling start() twice does not spawn a second cleanup loop."""
        manager = TaskManager()
        await manager.start()
        first = manager._cleanup_task
        await manager.start()
        assert manager._cleanup_task is first
        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_cleanup_task(self):
        manager = TaskManager()
        await manager.start()
        assert manager._cleanup_task is not None
        await manager.stop()
        # After stop(), the cleanup task reference is cleared.
        assert manager._cleanup_task is None


class TestListTasksPaginationContract:
    """Resolved decision 38: tasks/list pagination contract.

    - Ordering: ``createdAt`` descending (newest first); ``taskId`` ascending
      tiebreaker for identical timestamps.
    - Default page size: :data:`DEFAULT_LIST_PAGE_SIZE` (20).
    - Cursor: opaque base64url-encoded ``{taskId, createdAt}``.
    - Invalid/expired cursor -> :class:`InvalidCursorError` (handler maps to
      ``-32602``).
    """

    @pytest_asyncio.fixture
    async def tm(self):
        manager = TaskManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_default_page_size_is_20(self, tm):
        for _ in range(25):
            await tm.create_task(context_key=CONTEXT_A)
        tasks, next_cursor = await tm.list_tasks(context_key=CONTEXT_A)
        assert len(tasks) == DEFAULT_LIST_PAGE_SIZE == 20
        assert next_cursor is not None

    @pytest.mark.asyncio
    async def test_no_next_cursor_when_all_fit(self, tm):
        for _ in range(5):
            await tm.create_task(context_key=CONTEXT_A)
        tasks, next_cursor = await tm.list_tasks(context_key=CONTEXT_A)
        assert len(tasks) == 5
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_ordering_is_newest_first(self, tm):
        created = []
        for _ in range(5):
            t = await tm.create_task(context_key=CONTEXT_A)
            created.append(t)
            await asyncio.sleep(0.01)  # ensure different createdAt timestamps
        tasks, _ = await tm.list_tasks(context_key=CONTEXT_A)
        returned_ids = [t.taskId for t in tasks]
        # Newest first -- reverse of creation order.
        assert returned_ids == [t.taskId for t in reversed(created)]

    @pytest.mark.asyncio
    async def test_taskid_tiebreaker_when_createdat_equal(self, tm):
        """When two tasks share createdAt, taskId ascending is the tiebreaker."""
        # Create two tasks with the same timestamp by patching.
        t1 = await tm.create_task(context_key=CONTEXT_A)
        t2 = await tm.create_task(context_key=CONTEXT_A)
        # Force equal createdAt
        _ck, task1 = tm._tasks[t1.taskId]
        _ck2, task2 = tm._tasks[t2.taskId]
        shared = "2025-01-01T00:00:00+00:00"
        task1.createdAt = shared
        task2.createdAt = shared
        tasks, _ = await tm.list_tasks(context_key=CONTEXT_A)
        returned_ids = [t.taskId for t in tasks]
        # With equal createdAt, taskId ascending order is the tiebreaker.
        assert returned_ids == sorted(returned_ids)

    @pytest.mark.asyncio
    async def test_cursor_paginates_to_next_page_without_overlap(self, tm):
        for _ in range(25):
            await tm.create_task(context_key=CONTEXT_A)
        page1, cursor = await tm.list_tasks(context_key=CONTEXT_A)
        assert cursor is not None
        page2, cursor2 = await tm.list_tasks(context_key=CONTEXT_A, cursor=cursor)
        page1_ids = {t.taskId for t in page1}
        page2_ids = {t.taskId for t in page2}
        assert page1_ids.isdisjoint(page2_ids)
        # 25 tasks total, 20 on page1, 5 on page2, no further pages.
        assert len(page2) == 5
        assert cursor2 is None

    @pytest.mark.asyncio
    async def test_exhaustive_pagination_covers_all_tasks_exactly_once(self, tm):
        all_created = set()
        for _ in range(25):
            t = await tm.create_task(context_key=CONTEXT_A)
            all_created.add(t.taskId)
        seen = set()
        cursor = None
        for _ in range(10):  # safety bound
            page, cursor = await tm.list_tasks(context_key=CONTEXT_A, cursor=cursor)
            for t in page:
                assert t.taskId not in seen  # no duplicates
                seen.add(t.taskId)
            if cursor is None:
                break
        assert seen == all_created

    @pytest.mark.asyncio
    async def test_invalid_cursor_raises_invalid_cursor_error(self, tm):
        await tm.create_task(context_key=CONTEXT_A)
        with pytest.raises(InvalidCursorError):
            await tm.list_tasks(context_key=CONTEXT_A, cursor="not-a-valid-cursor!!")

    @pytest.mark.asyncio
    async def test_cursor_for_nonexistent_task_raises(self, tm):
        """A syntactically valid cursor pointing at an unknown task -> InvalidCursorError."""
        stale = _encode_cursor_literal(task_id="ghost-task", created_at="2025-01-01T00:00:00+00:00")
        await tm.create_task(context_key=CONTEXT_A)
        with pytest.raises(InvalidCursorError):
            await tm.list_tasks(context_key=CONTEXT_A, cursor=stale)

    @pytest.mark.asyncio
    async def test_cursor_roundtrip(self, tm):
        t = await tm.create_task(context_key=CONTEXT_A)
        cursor = _encode_cursor(t)
        task_id, created_at = _decode_cursor(cursor)
        assert task_id == t.taskId
        assert created_at == t.createdAt

    @pytest.mark.asyncio
    async def test_cursor_is_opaque_base64url(self, tm):
        t = await tm.create_task(context_key=CONTEXT_A)
        cursor = _encode_cursor(t)
        # Must decode as base64url (tolerating missing padding); payload is JSON
        # with taskId and createdAt.
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        payload = json.loads(raw)
        assert payload["taskId"] == t.taskId
        assert payload["createdAt"] == t.createdAt

    @pytest.mark.asyncio
    async def test_explicit_limit_overrides_default_page_size(self, tm):
        for _ in range(10):
            await tm.create_task(context_key=CONTEXT_A)
        tasks, cursor = await tm.list_tasks(context_key=CONTEXT_A, limit=3)
        assert len(tasks) == 3
        assert cursor is not None  # 10 > 3


def _encode_cursor_literal(*, task_id: str, created_at: str) -> str:
    """Helper to build a syntactically-valid cursor for a non-existent task."""
    payload = json.dumps(
        {"taskId": task_id, "createdAt": created_at},
        separators=(",", ":"),
        sort_keys=True,
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
