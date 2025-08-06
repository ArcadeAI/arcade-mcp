import asyncio
import json
from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_serve.fastapi.sse import SSEComponent
from arcade_tdk import tool


@tool
def test_add(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Add two numbers together."""
    return a + b


class MockWorker:
    """Mock worker for testing."""

    def __init__(self, catalog: ToolCatalog, disable_auth: bool = True):
        self.catalog = catalog
        self.disable_auth = disable_auth
        self.secret = "test-secret"


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
    catalog.add_tool(test_add, "test_toolkit")
    return catalog


@pytest.fixture
def mock_worker(tool_catalog):
    """Create a mock worker."""
    return MockWorker(tool_catalog)


@pytest.fixture
def sse_component(mock_worker):
    """Create an SSE component."""
    return SSEComponent(mock_worker)


class TestSSEComponent:
    """Test the SSE component functionality."""

    def test_component_initialization(self, sse_component):
        """Test that the component initializes correctly."""
        assert sse_component.worker is not None
        assert sse_component.sessions == {}
        assert sse_component.sessions_lock is not None
        assert sse_component.mcp_server is not None

    def test_register_routes(self, sse_component):
        """Test that routes are registered correctly."""
        router = TestRouter()
        sse_component.register(router)

        # Should register 2 routes (GET and POST)
        assert len(router.routes) == 2

        # Check GET route
        get_route = next(r for r in router.routes if r["kwargs"]["method"] == "GET")
        assert get_route["path"] == "mcp"
        assert get_route["kwargs"]["response_class"].__name__ == "EventSourceResponse"

        # Check POST route
        post_route = next(r for r in router.routes if r["kwargs"]["method"] == "POST")
        assert post_route["path"] == "mcp"

    @pytest.mark.asyncio
    async def test_session_creation_and_cleanup(self, sse_component):
        """Test session creation and cleanup."""
        # Start cleanup task
        sse_component.startup()

        try:
            # Create sessions
            session_ids = []
            async with sse_component.sessions_lock:
                for i in range(5):
                    session_id = f"test-session-{i}"
                    session = type(
                        "Session",
                        (),
                        {
                            "session_id": session_id,
                            "queue": asyncio.Queue(),
                            "last_active": 0,  # Set to 0 to trigger cleanup
                            "close": asyncio.coroutine(lambda: None),
                        },
                    )()
                    sse_component.sessions[session_id] = session
                    session_ids.append(session_id)

            # Wait for cleanup to run
            await asyncio.sleep(15)  # Wait longer than cleanup interval

            # Check that sessions were cleaned up
            async with sse_component.sessions_lock:
                assert len(sse_component.sessions) == 0

        finally:
            # Stop cleanup task
            await sse_component.shutdown()

    @pytest.mark.asyncio
    async def test_max_sessions_limit(self, sse_component):
        """Test that max sessions limit is enforced."""
        # Import the constants
        from arcade_serve.fastapi.sse import MAX_SESSIONS

        # Start cleanup task
        sse_component.startup()

        try:
            # Create more sessions than the limit
            async with sse_component.sessions_lock:
                for i in range(MAX_SESSIONS + 10):
                    session_id = f"test-session-{i}"
                    session = type(
                        "Session",
                        (),
                        {
                            "session_id": session_id,
                            "queue": asyncio.Queue(),
                            "last_active": i,  # Older sessions have lower values
                            "close": asyncio.coroutine(lambda: None),
                        },
                    )()
                    sse_component.sessions[session_id] = session

            # Wait for cleanup to run
            await asyncio.sleep(15)

            # Check that we're at or below the limit
            async with sse_component.sessions_lock:
                assert len(sse_component.sessions) <= MAX_SESSIONS

        finally:
            # Stop cleanup task
            await sse_component.shutdown()


@pytest.mark.asyncio
async def test_sse_post_validation(sse_component):
    """Test POST request validation."""

    # Mock request with invalid content type
    class MockRequest:
        def __init__(self, headers, body):
            self.method = "POST"
            self.headers = headers
            self._body = body

        async def body(self):
            return self._body

        async def json(self):
            return json.loads(self._body)

    # Test invalid content type
    request = MockRequest(headers={"content-type": "text/plain"}, body=b'{"method": "test"}')
    response = await sse_component(request)
    assert response["status"] == "error"
    assert "Content-Type" in response["message"]

    # Test oversized request
    request = MockRequest(
        headers={"content-type": "application/json"},
        body=b'{"data": "' + b"x" * (1024 * 1024 + 1) + b'"}',
    )
    response = await sse_component(request)
    assert response["status"] == "error"
    assert "too large" in response["message"]

    # Test invalid JSON
    request = MockRequest(headers={"content-type": "application/json"}, body=b'{"invalid json')
    response = await sse_component(request)
    assert response["status"] == "error"
    assert "Invalid JSON" in response["message"]
