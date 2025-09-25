import asyncio
import queue
from unittest.mock import MagicMock, patch

import pytest
from arcade_mcp_server.exceptions import TransportError
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.transports.stdio import (
    StdioReadStream,
    StdioTransport,
    StdioWriteStream,
)


class TestStdioWriteStream:
    """Test StdioWriteStream functionality."""

    @pytest.mark.asyncio
    async def test_send_adds_newline(self):
        """Test that send adds newline to data without one."""
        write_queue = queue.Queue()
        stream = StdioWriteStream(write_queue)

        await stream.send("test message")

        # Check that newline was added
        assert write_queue.get() == "test message\n"

    @pytest.mark.asyncio
    async def test_send_preserves_existing_newline(self):
        """Test that send doesn't add extra newline if one exists."""
        write_queue = queue.Queue()
        stream = StdioWriteStream(write_queue)

        await stream.send("test message\n")

        # Check that no extra newline was added
        assert write_queue.get() == "test message\n"


class TestStdioReadStream:
    """Test StdioReadStream functionality."""

    @pytest.mark.asyncio
    async def test_read_stream_iteration(self):
        """Test basic iteration over read stream."""
        read_queue = queue.Queue()
        stream = StdioReadStream(read_queue)

        # Put test data in queue
        read_queue.put("line1")
        read_queue.put("line2")
        read_queue.put(None)  # EOF marker

        lines = []
        async for line in stream:
            lines.append(line)

        assert lines == ["line1", "line2"]

    @pytest.mark.asyncio
    async def test_read_stream_stop(self):
        """Test that stopping the stream raises StopAsyncIteration."""
        read_queue = queue.Queue()
        stream = StdioReadStream(read_queue)

        stream.stop()

        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    @pytest.mark.asyncio
    async def test_read_stream_none_stops_iteration(self):
        """Test that None in queue stops iteration."""
        read_queue = queue.Queue()
        stream = StdioReadStream(read_queue)

        read_queue.put(None)

        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()


class TestStdioTransport:
    """Test StdioTransport functionality."""

    @pytest.mark.asyncio
    async def test_transport_initialization(self):
        """Test transport initializes with correct defaults."""
        transport = StdioTransport()

        assert transport.name == "stdio"
        assert isinstance(transport.read_queue, queue.Queue)
        assert isinstance(transport.write_queue, queue.Queue)
        assert transport.reader_thread is None
        assert transport.writer_thread is None
        assert not transport._running
        assert transport._sessions == {}

    @pytest.mark.asyncio
    async def test_transport_custom_name(self):
        """Test transport can be initialized with custom name."""
        transport = StdioTransport(name="custom-stdio")
        assert transport.name == "custom-stdio"

    @pytest.mark.asyncio
    async def test_start_creates_threads(self):
        """Test that start() creates and starts I/O threads."""
        transport = StdioTransport()

        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            await transport.start()

            # Should create two threads (reader and writer)
            assert mock_thread.call_count == 2
            # Both threads should be started
            assert mock_thread_instance.start.call_count == 2
            assert transport._running is True

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        """Test that stop() sets _running to False and signals threads."""
        transport = StdioTransport()
        transport._running = True

        # Mock threads
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_reader.is_alive.return_value = False
        mock_writer.is_alive.return_value = False

        transport.reader_thread = mock_reader
        transport.writer_thread = mock_writer

        await transport.stop()

        assert transport._running is False
        assert transport._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self):
        """Test list_sessions returns empty list initially."""
        transport = StdioTransport()
        sessions = await transport.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_register_session(self):
        """Test session registration."""
        transport = StdioTransport()
        mock_session = MagicMock(spec=ServerSession)
        mock_session.session_id = "test-session"

        await transport.register_session(mock_session)

        sessions = await transport.list_sessions()
        assert sessions == ["test-session"]
        assert transport._sessions["test-session"] == mock_session

    @pytest.mark.asyncio
    async def test_unregister_session(self):
        """Test session unregistration."""
        transport = StdioTransport()
        mock_session = MagicMock(spec=ServerSession)
        mock_session.session_id = "test-session"

        # Register then unregister
        await transport.register_session(mock_session)
        await transport.unregister_session("test-session")

        sessions = await transport.list_sessions()
        assert sessions == []
        assert "test-session" not in transport._sessions

    @pytest.mark.asyncio
    async def test_connect_session_single_session_limit(self):
        """Test that stdio transport only allows one session."""
        transport = StdioTransport()

        # Mock existing session
        mock_session = MagicMock(spec=ServerSession)
        mock_session.session_id = "existing-session"
        transport._sessions["existing-session"] = mock_session

        # Try to connect another session
        with pytest.raises(TransportError, match="Stdio transport only supports one session"):
            async with transport.connect_session():
                pass

    @pytest.mark.asyncio
    async def test_connect_session_creates_session(self):
        """Test that connect_session creates a proper session."""
        transport = StdioTransport()

        # Mock UUID generation
        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.return_value = "test-uuid"
            mock_uuid.return_value.__str__.return_value = "test-uuid"

            async with transport.connect_session() as session:
                assert isinstance(session, ServerSession)
                assert session.session_id == "test-uuid"
                assert session.stateless is True

                # Check session was registered
                sessions = await transport.list_sessions()
                assert "test-uuid" in sessions

        # Check session was unregistered after context exit
        sessions = await transport.list_sessions()
        assert "test-uuid" not in sessions

    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self):
        """Test wait_for_shutdown waits for shutdown event."""
        transport = StdioTransport()

        # Start a task that will set the shutdown event after a delay
        async def set_shutdown():
            await asyncio.sleep(0.01)
            transport._shutdown_event.set()

        task = asyncio.create_task(set_shutdown())

        # This should complete when the event is set
        await transport.wait_for_shutdown()

        assert transport._shutdown_event.is_set()
        await task  # Clean up the task
