"""HTTP Session Manager for MCP servers.

Manages HTTP streaming sessions with optional resumability via event store.
"""

import contextlib
import logging
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Optional
from uuid import uuid4

import anyio
from anyio.abc import TaskStatus
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.transports.http_streamable import (
    MCP_SESSION_ID_HEADER,
    EventStore,
    HTTPStreamableTransport,
)

logger = logging.getLogger(__name__)


class HTTPSessionManager:
    """Manages HTTP streaming sessions with optional resumability.

    This class abstracts session management, event storage, and request handling
    for HTTP streaming transports. It handles:

    1. Session tracking for clients
    2. Resumability via optional event store
    3. Connection management and lifecycle
    4. Request handling and transport setup

    Important: Only one HTTPSessionManager instance should be created per application.
    The instance cannot be reused after its run() context has completed.
    """

    def __init__(
        self,
        server: MCPServer,
        event_store: Optional[EventStore] = None,
        json_response: bool = False,
        stateless: bool = False,
    ):
        """Initialize HTTP session manager.

        Args:
            server: The MCP server instance
            event_store: Optional event store for resumability
            json_response: Whether to use JSON responses instead of SSE
            stateless: If True, creates fresh transport for each request
        """
        self.server = server
        self.event_store = event_store
        self.json_response = json_response
        self.stateless = stateless

        # Session tracking (only used if not stateless)
        self._session_creation_lock = anyio.Lock()
        self._server_instances: dict[str, HTTPStreamableTransport] = {}

        # Task group will be set during lifespan
        self._task_group: Optional[anyio.abc.TaskGroup] = None

        # Thread-safe tracking of run() calls
        self._run_lock = anyio.Lock()
        self._has_started = False

    @contextlib.asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Run the session manager with lifecycle management.

        This creates and manages the task group for all session operations.

        Important: This method can only be called once per instance.
        Create a new instance if you need to restart.
        """
        async with self._run_lock:
            if self._has_started:
                raise RuntimeError(
                    "HTTPSessionManager.run() can only be called once per instance. "
                    "Create a new instance if you need to run again."
                )
            self._has_started = True

        async with anyio.create_task_group() as tg:
            self._task_group = tg
            logger.info("HTTP session manager started")
            try:
                yield
            finally:
                logger.info("HTTP session manager shutting down")
                tg.cancel_scope.cancel()
                self._task_group = None
                self._server_instances.clear()

    async def handle_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process ASGI request with proper session handling.

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if self._task_group is None:
            raise RuntimeError("Task group is not initialized. Make sure to use run().")

        if self.stateless:
            await self._handle_stateless_request(scope, receive, send)
        else:
            await self._handle_stateful_request(scope, receive, send)

    async def _handle_stateless_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process request in stateless mode - new transport per request."""
        logger.debug("Stateless mode: Creating new transport for this request")

        # Create transport without session ID in stateless mode
        http_transport = HTTPStreamableTransport(
            mcp_session_id=None,
            is_json_response_enabled=self.json_response,
            event_store=None,  # No event store in stateless mode
        )

        # Start server in a new task
        async def run_stateless_server(
            *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED
        ) -> None:
            async with http_transport.connect() as streams:
                read_stream, write_stream = streams
                task_status.started()
                try:
                    # Create a new session for this request
                    session = ServerSession(
                        server=self.server,
                        read_stream=read_stream,
                        write_stream=write_stream,
                        init_options={"transport_type": "http"},
                    )

                    # Set the session on the transport
                    http_transport.session = session

                    # Run the session (start + loop until closed)
                    await session.run()

                    # Brief yield to allow cleanup
                    await anyio.sleep(0)
                except Exception:
                    logger.exception("Stateless session crashed")

        if self._task_group is None:
            raise RuntimeError("Task group not initialized")
        await self._task_group.start(run_stateless_server)

        # Handle the HTTP request
        await http_transport.handle_request(scope, receive, send)

        # Terminate the transport
        await http_transport.terminate()

    async def _handle_stateful_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process request in stateful mode - maintain session state."""
        request = Request(scope, receive)
        request_mcp_session_id = request.headers.get(MCP_SESSION_ID_HEADER)

        # Existing session case
        if request_mcp_session_id and request_mcp_session_id in self._server_instances:
            transport = self._server_instances[request_mcp_session_id]
            logger.debug("Session already exists, handling request directly")
            await transport.handle_request(scope, receive, send)
            return

        if request_mcp_session_id is None:
            # New session case
            logger.debug("Creating new transport")
            async with self._session_creation_lock:
                new_session_id = uuid4().hex
                http_transport = HTTPStreamableTransport(
                    mcp_session_id=new_session_id,
                    is_json_response_enabled=self.json_response,
                    event_store=self.event_store,
                )

                if http_transport.mcp_session_id is None:
                    raise RuntimeError("MCP session ID not set")
                self._server_instances[http_transport.mcp_session_id] = http_transport
                logger.info(f"Created new transport with session ID: {new_session_id}")

                # Define the server runner
                async def run_server(
                    *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED
                ) -> None:
                    async with http_transport.connect() as streams:
                        read_stream, write_stream = streams
                        task_status.started()
                        try:
                            # Create a session for this connection
                            session = ServerSession(
                                server=self.server,
                                read_stream=read_stream,
                                write_stream=write_stream,
                                init_options={"transport_type": "http"},
                            )

                            # Set the session on the transport
                            http_transport.session = session

                            # Run the session (start + loop until closed)
                            await session.run()

                            # Brief yield to allow cleanup
                            await anyio.sleep(0)
                        except Exception as e:
                            logger.error(
                                f"Session {http_transport.mcp_session_id} crashed: {e}",
                                exc_info=True,
                            )
                        finally:
                            # Clean up on crash
                            if (
                                http_transport.mcp_session_id
                                and http_transport.mcp_session_id in self._server_instances
                                and not http_transport.is_terminated
                            ):
                                logger.info(
                                    f"Cleaning up crashed session {http_transport.mcp_session_id}"
                                )
                                del self._server_instances[http_transport.mcp_session_id]

                if self._task_group is None:
                    raise RuntimeError("Task group not initialized")
                await self._task_group.start(run_server)

                # Handle the HTTP request
                await http_transport.handle_request(scope, receive, send)
        else:
            # Invalid session ID
            response = Response(
                "Bad Request: No valid session ID provided",
                status_code=HTTPStatus.BAD_REQUEST,
            )
            await response(scope, receive, send)
