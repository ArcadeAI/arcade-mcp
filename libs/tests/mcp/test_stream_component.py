import asyncio
import json
from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_serve.fastapi.stream import StreamComponent
from arcade_tdk import tool


@tool
def tool_multiply(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Multiply two numbers."""
    return a * b


class MockWorker:
    """Mock worker for testing."""

    def __init__(self, catalog: ToolCatalog, disable_auth: bool = True):
        self.catalog = catalog
        self.disable_auth = disable_auth
        self.secret = "test-secret"  # noqa: S105


class TestRouter:
    """Test router to capture registered routes."""

    def __init__(self):
        self.routes = []

    def add_route(self, path: str, handler, **kwargs):
        self.routes.append({"path": path, "handler": handler, "kwargs": kwargs})


@pytest.fixture
def tool_catalog():
    """Create a catalog with test tools."""
    catalog = ToolCatalog()
    catalog.add_tool(tool_multiply, "test_toolkit")
    return catalog


@pytest.fixture
def mock_worker(tool_catalog):
    """Create a mock worker."""
    return MockWorker(tool_catalog)


@pytest.fixture
def stream_component(mock_worker):
    """Create a Stream component."""
    return StreamComponent(mock_worker)


class TestStreamComponent:
    """Test the Stream component functionality."""

    def test_component_initialization(self, stream_component):
        """Test that the component initializes correctly."""
        assert stream_component.worker is not None
        assert stream_component.sessions == {}
        assert stream_component.sessions_lock is not None
        assert stream_component.mcp_server is not None

    def test_register_routes(self, stream_component):
        """Test that routes are registered correctly."""
        router = TestRouter()
        stream_component.register(router)

        # Should register 1 route (POST only)
        assert len(router.routes) == 1

        # Check POST route
        post_route = router.routes[0]
        assert post_route["path"] == "mcp"
        assert post_route["kwargs"]["method"] == "POST"
        assert post_route["kwargs"]["response_class"].__name__ == "StreamingResponse"

    @pytest.mark.asyncio
    async def test_session_cleanup_task(self, stream_component):
        """Test that cleanup task starts and stops correctly."""
        # Start cleanup task
        stream_component.startup()
        assert stream_component._cleanup_task is not None
        assert not stream_component._cleanup_task.done()

        # Stop cleanup task
        await stream_component.shutdown()
        assert stream_component._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_request_validation(self, stream_component):
        """Test request validation."""

        class MockRequest:
            def __init__(self, headers, body_data, disconnected=False):
                self.headers = headers
                self._body = body_data
                self._disconnected = disconnected

            async def body(self):
                return self._body

            async def is_disconnected(self):
                if self._disconnected:
                    return True
                # Simulate waiting
                await asyncio.sleep(10)
                return False

        # Test invalid content type
        request = MockRequest(
            headers={"content-type": "text/plain"}, body_data=b'{"method": "test"}'
        )

        response = await stream_component(request)
        assert response.status_code == 400
        assert response.media_type == "application/x-ndjson"

        # Get the response body
        body = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                body += chunk
            else:
                body += chunk.encode()

        data = json.loads(body.decode().strip())
        assert data["status"] == "error"
        assert "Content-Type" in data["error"]

    @pytest.mark.asyncio
    async def test_session_limit_enforcement(self, stream_component):
        """Test that session limits are enforced."""
        from arcade_serve.fastapi.stream import MAX_SESSIONS

        # Start cleanup task
        stream_component.startup()

        try:
            # Create many sessions
            async with stream_component.sessions_lock:
                for i in range(MAX_SESSIONS + 50):
                    session_id = f"test-{i}"
                    session = type(
                        "Session",
                        (),
                        {
                            "session_id": session_id,
                            "queue": asyncio.Queue(),
                            "last_active": i,
                            "close": asyncio.coroutine(lambda: None),
                        },
                    )()
                    stream_component.sessions[session_id] = session

            # Wait for cleanup
            await asyncio.sleep(15)

            # Verify limit is enforced
            async with stream_component.sessions_lock:
                assert len(stream_component.sessions) <= MAX_SESSIONS

        finally:
            await stream_component.shutdown()
