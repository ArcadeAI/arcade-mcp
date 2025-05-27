import asyncio
import logging
import queue
import signal
import sys
import threading
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    pass

from arcade_serve.mcp.server import MCPServer

logger = logging.getLogger("arcade.mcp")

T = TypeVar("T")


def stdio_reader(stdin: object, q: queue.Queue[str | None]) -> None:
    """Read lines from stdin and put them into a queue."""
    for line in stdin:  # type: ignore[attr-defined]
        q.put(line)
    q.put(None)


def stdio_writer(stdout: object, q: queue.Queue[str | None]) -> None:
    """Write messages from a queue to stdout."""
    try:
        while True:
            msg = q.get()
            if msg is None:
                break

            # Ensure message ends with a newline for proper JSON-RPC-over-stdio
            if not msg.endswith("\n"):
                msg += "\n"

            stdout.write(msg)  # type: ignore[attr-defined]
            stdout.flush()  # type: ignore[attr-defined]
    except Exception:
        logger.exception("Error in stdio writer")


class StdioServer(MCPServer):
    """
    Stdio server that handles signals and cleanup.
    """

    def __init__(
        self,
        tool_catalog: Any,
        enable_logging: bool = True,
        **client_kwargs: dict[str, Any],
    ):
        # Set up stdio-specific middleware configuration
        middleware_config = client_kwargs.get("middleware_config", {})
        middleware_config["stdio_mode"] = True
        client_kwargs["middleware_config"] = middleware_config

        super().__init__(tool_catalog, enable_logging, **client_kwargs)
        self.read_q: queue.Queue[str | None] = queue.Queue()
        self.write_q: queue.Queue[str | None] = queue.Queue()
        self.reader_thread: threading.Thread | None = None
        self.writer_thread: threading.Thread | None = None
        self.running = False
        self.shutdown_event = asyncio.Event()

    def start_io_threads(self) -> None:
        """Start stdio reader and writer threads."""
        self.reader_thread = threading.Thread(
            target=self._stdio_reader, args=(sys.stdin, self.read_q), daemon=True
        )
        self.writer_thread = threading.Thread(
            target=self._stdio_writer, args=(sys.stdout, self.write_q), daemon=True
        )
        self.reader_thread.start()
        self.writer_thread.start()

    def _stdio_reader(self, stdin: object, q: queue.Queue[str | None]) -> None:
        """Read lines from stdin and put them into a queue."""
        try:
            for line in stdin:  # type: ignore[attr-defined]
                if not self.running:
                    break
                q.put(line)
        except Exception:
            logger.exception("Error in stdio reader")
        finally:
            q.put(None)  # Signal EOF

    def _stdio_writer(self, stdout: object, q: queue.Queue[str | None]) -> None:
        """Write messages from a queue to stdout."""
        try:
            while self.running:
                msg = q.get()
                if msg is None:
                    break
                stdout.write(msg)  # type: ignore[attr-defined]
                stdout.flush()  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Error in stdio writer")

    async def _read_stream(self) -> AsyncGenerator[str, None]:
        """Async generator that yields lines from the read queue."""
        while self.running:
            try:
                line = await asyncio.to_thread(self.read_q.get)
                if line is None:
                    break
                yield line
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error reading from stdin")
                break

    async def shutdown(self) -> None:
        """Gracefully shut down the server."""
        if not self.running:
            return

        logger.info("Shutting down stdio server...")
        self.running = False

        # Signal shutdown to MCP server
        await self.shutdown()

        # Clean up IO queues and threads
        try:
            if self.read_q:
                self.read_q.put(None)
            if self.write_q:
                self.write_q.put(None)
        except Exception:
            logger.exception("Error during shutdown")

        # Signal completion
        self.shutdown_event.set()
        logger.info("Stdio server shutdown complete")

    async def run(self) -> None:
        """Run the stdio server with signal handling."""
        self.running = True

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            except NotImplementedError:
                # Windows doesn't support POSIX signals
                if sys.platform == "win32":
                    logger.warning("Signal handling not fully supported on Windows")
                else:
                    logger.warning(f"Failed to set up signal handler for {sig}")

        # Start IO threads
        self.start_io_threads()

        logger.info("Starting MCP server with stdio transport")

        # Create WriteStream class for MCP server
        class WriteStream:
            async def send(self_, message: str) -> None:
                if self.running:
                    await asyncio.to_thread(self.write_q.put, message)

        try:
            # Run MCP server connection
            await self.run_connection(self._read_stream(), WriteStream(), None)
        except asyncio.CancelledError:
            # Handle cancellation
            logger.info("Server operation cancelled")
        except KeyboardInterrupt:
            # Handle keyboard interrupt
            logger.info("Keyboard interrupt received")
        except Exception:
            # Handle unexpected errors
            logger.exception("Unexpected error")
        finally:
            # Ensure we clean up
            await self.shutdown()
            # Wait for shutdown to complete
            await self.shutdown_event.wait()
