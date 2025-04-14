import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Union

try:
    from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
    from mcp.server.lowlevel import Server as MCPServer
    from mcp.server.models import InitializationOptions
    from mcp.types import JSONRPCMessage

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


from arcade.worker.mcp.message_processor import MCPMessageProcessor

logger = logging.getLogger("arcade.mcp")


class StreamProcessor:
    """Processes messages between streams with middleware support."""

    def __init__(self, processor: Optional[MCPMessageProcessor] = None):
        """Initialize the stream processor."""
        self.processor = processor
        self.running = False
        self._lock = threading.RLock()

    async def process_receive_stream(
        self,
        receive_stream: MemoryObjectReceiveStream,
        send_stream: MemoryObjectSendStream,
        is_request: bool = True,
    ) -> None:
        """
        Process messages from a receive stream to a send stream.

        Args:
            receive_stream: Stream to read messages from
            send_stream: Stream to write messages to
            is_request: Whether we're processing a request (True) or response (False)
        """
        try:
            with self._lock:
                self.running = True

            async with send_stream:
                async for message in receive_stream:
                    try:
                        processed_message = message
                        if isinstance(message, JSONRPCMessage) and self.processor:
                            if is_request:
                                processed_message = self.processor.process_request(message)
                            else:
                                processed_message = self.processor.process_response(message)

                        await send_stream.send(processed_message)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                        # In case of error, pass through the original message
                        try:
                            await send_stream.send(message)
                        except Exception as send_err:
                            logger.exception(
                                f"Failed to send original message after error: {send_err}"  # noqa: TRY401
                            )
        except Exception as e:
            logger.error(f"Stream processing error: {e}", exc_info=True)
        finally:
            with self._lock:
                self.running = False
            logger.debug("Stream processor stopped")


class DirectPassthrough:
    """
    A direct passthrough for streams, avoiding task groups for initialization.
    This sequential approach helps avoid initialization timing issues.
    """

    def __init__(self, connection_id: str = "unknown"):
        """Initialize a direct passthrough."""
        self.connection_id = connection_id
        self.initialized = False
        self._lock = threading.RLock()
        self._shutdown_requested = False

    async def shutdown(self) -> None:
        """Request shutdown of this connection."""
        self._shutdown_requested = True
        logger.debug(f"Shutdown requested for connection {self.connection_id}")

    async def run(
        self,
        original_server: MCPServer,
        client_stream: MemoryObjectReceiveStream,
        server_stream: MemoryObjectSendStream,
        init_options: Any,
        processor: Optional[MCPMessageProcessor] = None,
    ) -> None:
        """
        Run the server directly with the provided streams.

        Args:
            original_server: The server to run
            client_stream: Stream to receive messages from the client
            server_stream: Stream to send messages to the client
            init_options: Initialization options
            processor: Optional message processor
        """
        logger.debug(f"Starting direct passthrough for connection {self.connection_id}")

        # For simplicity, we'll use the parent MCPServer directly without
        # middleware processing, as that seems to be causing initialization issues
        try:
            # Get the parent MCPServer's run method directly
            parent_run = MCPServer.run.__get__(original_server, type(original_server))

            # Run the MCP server directly - this ensures initialization completes
            # before any messages are processed
            await parent_run(client_stream, server_stream, init_options)
            self.initialized = True

        except asyncio.CancelledError:
            logger.debug(f"Connection {self.connection_id} cancelled gracefully")
        except Exception as e:
            if "before initialization was complete" in str(e):
                logger.exception(
                    f"Initialization timing issue for {self.connection_id} "
                    f"This is likely due to the server receiving messages before init completes."
                )
            else:
                logger.exception(f"Error in direct passthrough for {self.connection_id}")
            raise


class PatchedMCPServer(MCPServer):
    """
    A patched version of the MCP Server that supports middleware and multiple connections.
    """

    def __init__(
        self, max_connections: int = 100, max_worker_threads: int = 10, *args: Any, **kwargs: Any
    ):
        """Initialize the patched MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError("The MCP package is required for the PatchedMCPServer")

        # Initialize the base MCPServer
        super().__init__(*args, **kwargs)

        # Store message processor
        self.message_processor: Optional[MCPMessageProcessor] = None

        self.max_connections = max_connections
        self.max_worker_threads = max_worker_threads

        # Connection management
        self.connections: dict[str, DirectPassthrough] = {}
        self.connection_count = 0
        self._lock = threading.RLock()

        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_worker_threads, thread_name_prefix="mcp_worker_"
        )

        # Shutdown flag
        self._shutdown = False

    def set_message_processor(self, processor: MCPMessageProcessor) -> None:
        """
        Set the message processor for this server.

        Args:
            processor: The message processor to use
        """
        self.message_processor = processor
        logger.debug("Message processor set for MCP server")

    def _get_connection_id(self) -> str:
        """Generate a unique connection ID."""
        with self._lock:
            self.connection_count += 1
            return f"conn_{self.connection_count}"

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the server and all connections.
        """
        logger.info("Shutting down MCP server...")

        if not hasattr(self, "_lock"):
            logger.warning("MCP server not fully initialized, skipping detailed shutdown")
            return

        # Set the shutdown flag first
        with self._lock:
            self._shutdown = True
            # Make a copy of connections to avoid modification during iteration
            connections = list(self.connections.items())

        # Notify all connections to shut down first
        logger.debug(f"Notifying {len(connections)} connections to shut down")
        for conn_id, conn in connections:
            try:
                if hasattr(conn, "shutdown"):
                    await conn.shutdown()
            except Exception as e:
                logger.exception(f"Error requesting shutdown for connection {conn_id}: {e}")

        # Now clean them up
        for conn_id, _ in connections:
            try:
                logger.debug(f"Cleaning up connection {conn_id}")
                with self._lock:
                    if conn_id in self.connections:
                        del self.connections[conn_id]
            except Exception as e:
                logger.exception(f"Error cleaning up connection {conn_id}: {e}")

        # Shutdown the executor
        try:
            if hasattr(self, "executor"):
                self.executor.shutdown(wait=False)
        except Exception as e:
            logger.exception(f"Error shutting down executor: {e}")

        logger.info("MCP server shutdown complete")

    async def run(
        self,
        read_stream: MemoryObjectReceiveStream,
        write_stream: MemoryObjectSendStream,
        init_options: Union[dict[str, Any], InitializationOptions],
    ) -> None:
        """
        Run a new MCP server instance for this connection.

        This method creates a new direct passthrough for each connection.

        Args:
            read_stream: Stream to read messages from
            write_stream: Stream to write messages to
            init_options: Initialization options
        """
        if hasattr(self, "_shutdown") and self._shutdown:
            logger.info("Server is shutting down, rejecting new connection")
            return

        connection_id = self._get_connection_id()
        logger.info(f"Starting server for connection {connection_id}")

        # Create a direct passthrough handler
        passthrough = DirectPassthrough(connection_id)

        # Store the connection
        with self._lock:
            self.connections[connection_id] = passthrough

        try:
            # Run the passthrough directly - this ensures proper initialization
            # before any messages are processed
            await passthrough.run(
                original_server=self,
                client_stream=read_stream,
                server_stream=write_stream,
                init_options=init_options,
                processor=self.message_processor,
            )

            logger.info(f"Connection {connection_id} completed")
        except asyncio.CancelledError:
            logger.info(f"Connection {connection_id} cancelled gracefully")
        except Exception as e:
            logger.error(f"Error in connection {connection_id}: {e}", exc_info=True)
            raise
        finally:
            # Clean up the connection
            try:
                with self._lock:
                    if connection_id in self.connections:
                        del self.connections[connection_id]
                logger.info(f"Connection {connection_id} cleanup complete")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up connection {connection_id}: {cleanup_error}")
