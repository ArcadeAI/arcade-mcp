"""Tests for worker tool sync: health endpoint hash/started_at and ToolNotFoundError."""

from typing import Annotated

import pytest
from arcade_core.schema import ToolCallRequest, ToolReference
from arcade_tdk import tool

from arcade_serve.core.base import BaseWorker
from arcade_serve.core.common import ToolNotFoundError


@tool
def hello_tool(name: Annotated[str, "The name"]) -> str:
    """Say hello"""
    return f"Hello, {name}!"


@tool
def goodbye_tool(name: Annotated[str, "The name"]) -> str:
    """Say goodbye"""
    return f"Goodbye, {name}!"


class TestHealthCheckWithHash:
    """Tests for BaseWorker.health_check with tool_definitions_hash and started_at."""

    def _make_worker(self):
        worker = BaseWorker(secret="test-secret")
        worker.register_tool(hello_tool, "TestToolkit")
        return worker

    def test_health_includes_hash(self):
        """Health response includes tool_definitions_hash."""
        worker = self._make_worker()
        result = worker.health_check()
        assert "tool_definitions_hash" in result
        assert isinstance(result["tool_definitions_hash"], str)
        assert len(result["tool_definitions_hash"]) == 64

    def test_health_includes_started_at(self):
        """Health response includes started_at as ISO 8601."""
        worker = self._make_worker()
        result = worker.health_check()
        assert "started_at" in result
        assert isinstance(result["started_at"], str)
        # Should be parseable as ISO 8601
        from datetime import datetime
        datetime.fromisoformat(result["started_at"])

    def test_started_at_stable(self):
        """started_at does not change between calls."""
        worker = self._make_worker()
        r1 = worker.health_check()
        r2 = worker.health_check()
        assert r1["started_at"] == r2["started_at"]

    def test_hash_matches_catalog(self):
        """Health hash matches ToolCatalog.compute_hash() output."""
        worker = self._make_worker()
        result = worker.health_check()
        expected = worker.catalog.compute_hash()
        assert result["tool_definitions_hash"] == expected

    def test_hash_stable_between_calls(self):
        """Hash does not change between health check calls."""
        worker = self._make_worker()
        r1 = worker.health_check()
        r2 = worker.health_check()
        assert r1["tool_definitions_hash"] == r2["tool_definitions_hash"]

    def test_health_still_has_status_and_tool_count(self):
        """Health response still includes standard fields."""
        worker = self._make_worker()
        result = worker.health_check()
        assert result["status"] == "ok"
        assert result["tool_count"] == "1"


class TestToolNotFoundError:
    """Tests for ToolNotFoundError raised when tool is not in catalog."""

    @pytest.mark.asyncio
    async def test_call_missing_tool_raises_not_found(self):
        """Calling a tool not in the catalog raises ToolNotFoundError."""
        worker = BaseWorker(secret="test-secret")
        worker.register_tool(hello_tool, "TestToolkit")

        request = ToolCallRequest(
            tool=ToolReference(
                name="NonexistentTool",
                toolkit="TestToolkit",
            ),
            inputs={"name": "World"},
        )

        with pytest.raises(ToolNotFoundError):
            await worker.call_tool(request)

    @pytest.mark.asyncio
    async def test_call_valid_tool_works(self):
        """Calling a valid tool does not raise ToolNotFoundError."""
        worker = BaseWorker(secret="test-secret")
        worker.register_tool(hello_tool, "TestToolkit")

        request = ToolCallRequest(
            tool=ToolReference(
                name="HelloTool",
                toolkit="TestToolkit",
            ),
            inputs={"name": "World"},
        )

        response = await worker.call_tool(request)
        assert response.success

    def test_tool_not_found_error_message(self):
        """ToolNotFoundError has a useful error message."""
        err = ToolNotFoundError("MyTool", "1.0.0")
        assert "MyTool" in str(err)
        assert "1.0.0" in str(err)

    def test_tool_not_found_error_without_version(self):
        """ToolNotFoundError works without a version."""
        err = ToolNotFoundError("MyTool")
        assert "MyTool" in str(err)
