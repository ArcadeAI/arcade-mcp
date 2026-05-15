"""Tests for per-request metadata isolation via ContextVar."""

import asyncio

import pytest
from arcade_mcp_server.request_context import (
    get_request_meta,
    reset_request_meta,
    set_request_meta,
)


class TestRequestContext:
    """Test the request_context ContextVar-based metadata isolation."""

    def test_get_returns_none_by_default(self):
        assert get_request_meta() is None

    def test_set_and_get_roundtrip(self):
        token = set_request_meta({"progressToken": "tok-1", "custom": 42})
        try:
            meta = get_request_meta()
            assert meta is not None
            assert meta.progressToken == "tok-1"
            assert meta.custom == 42
        finally:
            reset_request_meta(token)

    def test_set_with_none_is_none(self):
        # First set something
        token1 = set_request_meta({"progressToken": "tok"})
        try:
            token2 = set_request_meta(None)
            try:
                assert get_request_meta() is None
            finally:
                reset_request_meta(token2)
        finally:
            reset_request_meta(token1)

    def test_reset_restores_previous(self):
        token1 = set_request_meta({"progressToken": "original"})
        try:
            token2 = set_request_meta({"progressToken": "override"})
            assert get_request_meta().progressToken == "override"  # type: ignore[union-attr]
            reset_request_meta(token2)
            assert get_request_meta().progressToken == "original"  # type: ignore[union-attr]
        finally:
            reset_request_meta(token1)

    @pytest.mark.asyncio
    async def test_isolation_between_concurrent_tasks(self):
        """Two concurrent asyncio tasks each set different meta; they don't interfere."""
        results: dict[str, str | None] = {}
        barrier = asyncio.Event()
        task_a_set = asyncio.Event()

        async def task_a() -> None:
            token = set_request_meta({"progressToken": "A"})
            try:
                task_a_set.set()
                # Wait for task_b to set its own meta
                await barrier.wait()
                # Should still see A
                meta = get_request_meta()
                results["a"] = meta.progressToken if meta else None  # type: ignore[union-attr]
            finally:
                reset_request_meta(token)

        async def task_b() -> None:
            # Wait for task_a to set its meta first
            await task_a_set.wait()
            token = set_request_meta({"progressToken": "B"})
            try:
                barrier.set()
                meta = get_request_meta()
                results["b"] = meta.progressToken if meta else None  # type: ignore[union-attr]
            finally:
                reset_request_meta(token)

        await asyncio.gather(
            asyncio.create_task(task_a()),
            asyncio.create_task(task_b()),
        )

        assert results["a"] == "A"
        assert results["b"] == "B"

    @pytest.mark.asyncio
    async def test_background_task_does_not_leak_into_parent(self):
        """A background task's ContextVar changes don't affect the parent context."""
        parent_token = set_request_meta({"progressToken": "parent"})
        try:
            child_done = asyncio.Event()

            async def background() -> None:
                # Child inherits parent's ContextVar value
                meta = get_request_meta()
                assert meta is not None
                assert meta.progressToken == "parent"  # type: ignore[union-attr]
                # Override in child
                token = set_request_meta({"progressToken": "child"})
                try:
                    child_done.set()
                finally:
                    reset_request_meta(token)

            task = asyncio.create_task(background())
            await child_done.wait()
            await task

            # Parent still sees its own value
            meta = get_request_meta()
            assert meta is not None
            assert meta.progressToken == "parent"  # type: ignore[union-attr]
        finally:
            reset_request_meta(parent_token)
