"""
Stdio Transport

Provides stdio (stdin/stdout) transport for MCP communication.
"""

import asyncio
import contextlib
import logging
import queue
import signal
import sys
import threading
import uuid
from collections.abc import AsyncIterator
from typing import Any

from arcade_mcp_server.exceptions import TransportError
from arcade_mcp_server.session import ServerSession

logger = logging.getLogger("arcade.mcp.transports.stdio")


class StdioWriteStream:
    """Write stream implementation for stdio."""

    def __init__(self, write_queue: queue.Queue[str | None]):
        self.write_queue = write_queue

    async def send(self, data: str) -> None:
        """Send data to stdout."""
        if not data.endswith("\n"):
            data += "\n"
        await asyncio.to_thread(self.write_queue.put, data)


class StdioReadStream:
    """Read stream implementation for stdio."""

    def __init__(self, read_queue: queue.Queue[str | None]):
        self.read_queue = read_queue
        self._running = True

    def stop(self) -> None:
        """Stop the read stream."""
        self._running = False

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        if not self._running:
            raise StopAsyncIteration
        try:
            line = await asyncio.to_thread(self.read_queue.get)
        except asyncio.CancelledError:
            raise StopAsyncIteration
        except Exception as e:
            logger.exception("Error reading from stdin")
            raise TransportError(f"Read error: {e}") from e
        if line is None or not self._running:
            raise StopAsyncIteration
        return line


class StdioTransport:
    """
    Stdio transport implementation for stdio communication.

    This transport uses stdin/stdout for MCP communication,
    suitable for command-line tools and scripts.
    """

    def __init__(self, name: str = "stdio"):
        """Initialize stdio transport."""
        self.name = name
        self.read_queue: queue.Queue[str | None] = queue.Queue()
        self.write_queue: queue.Queue[str | None] = queue.Queue()
        self.reader_thread: threading.Thread | None = None
        self.writer_thread: threading.Thread | None = None
        self._shutdown_event = asyncio.Event()
        self._running = False
        self._sessions: dict[str, ServerSession] = {}

    async def start(self) -> None:
        """Start the transport."""
        # Component start is handled here directly

        # Start I/O threads
        self._running = True
        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name=f"{self.name}-reader",
        )
        self.writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name=f"{self.name}-writer",
        )
        self.reader_thread.start()
        self.writer_thread.start()

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # Windows doesn't support POSIX signals
                if sys.platform == "win32":
                    logger.warning("Signal handling not fully supported on Windows")
                else:
                    logger.warning(f"Failed to set up signal handler for {sig}")

    async def stop(self) -> None:
        """Stop the transport."""
        if not self._running:
            return

        logger.info("Stopping stdio transport")
        self._running = False

        # Signal threads to stop
        self.read_queue.put(None)
        self.write_queue.put(None)

        # Wait for threads to finish
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1.0)
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=1.0)

        # Set shutdown event
        self._shutdown_event.set()

    def _reader_loop(self) -> None:
        """Reader thread loop."""
        try:
            for line in sys.stdin:
                if not self._running:
                    break
                self.read_queue.put(line.strip())
        except Exception:
            logger.exception("Error in reader thread")
        finally:
            self.read_queue.put(None)  # Signal EOF

    def _writer_loop(self) -> None:
        """Writer thread loop."""
        try:
            while self._running:
                msg = self.write_queue.get()
                if msg is None:
                    break
                sys.stdout.write(msg)
                sys.stdout.flush()
        except Exception:
            logger.exception("Error in writer thread")

    @contextlib.asynccontextmanager
    async def connect_session(self, **options: Any) -> AsyncIterator[ServerSession]:
        """
        Create a stdio session.

        Since stdio is inherently single-session, this will fail
        if a session is already active.
        """
        # Check if already have a session
        sessions = await self.list_sessions()
        if sessions:
            raise TransportError("Stdio transport only supports one session")

        # Create session
        session_id = str(uuid.uuid4())
        read_stream = StdioReadStream(self.read_queue)
        write_stream = StdioWriteStream(self.write_queue)

        init_options = {"transport_type": "stdio", **options}

        session = ServerSession(
            server=None,  # set by the caller using run_connection; not used here
            session_id=session_id,
            read_stream=read_stream,
            write_stream=write_stream,
            init_options=init_options,
            stateless=True,
        )

        # Register session
        await self.register_session(session)

        try:
            yield session
        finally:
            # Cleanup
            read_stream.stop()
            await self.unregister_session(session_id)

    async def wait_for_shutdown(self) -> None:
        """Wait for the transport to shut down."""
        await self._shutdown_event.wait()

    # Minimal session registry to support connect_session lifecycle
    async def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    async def register_session(self, session: ServerSession) -> None:
        self._sessions[session.session_id] = session

    async def unregister_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
