import asyncio
import contextlib
import json
import time
import uuid
from logging import getLogger
from typing import Any, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sse_starlette.sse import EventSourceResponse

from arcade_serve.core.base import BaseWorker
from arcade_serve.core.common import (
    Router,
    WorkerComponent,
)
from arcade_serve.fastapi.auth import validate_engine_request
from arcade_serve.mcp.server import MCPServer

SESSION_TIMEOUT_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL_SECONDS = 10  # Check every 10 seconds instead of 60
MAX_SESSIONS = 1000  # Maximum number of concurrent sessions

logger = getLogger("arcade.mcp")


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.last_active: float = time.time()

    def touch(self) -> None:
        """Update the last active timestamp."""
        self.last_active = time.time()

    async def close(self) -> None:
        """Signal the session to close."""
        await self.queue.put(None)  # Sentinel value to terminate the stream


class SSEComponent(WorkerComponent):
    def __init__(self, worker: BaseWorker, local_context: dict[str, Any] | None = None) -> None:
        super().__init__(worker)
        self.sessions: dict[str, Session] = {}
        self.sessions_lock = asyncio.Lock()  # Add lock for thread-safe operations
        self.mcp_server = MCPServer(
            worker.catalog,
            auth_disabled=worker.disable_auth,
            local_context=local_context,
        )
        self._cleanup_task: asyncio.Task | None = None
        # Initialize HTTPBearer with auto_error based on auth settings
        self.security = HTTPBearer(auto_error=not worker.disable_auth)

    def startup(self) -> None:
        """Start the background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())

    async def shutdown(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

    async def _cleanup_inactive_sessions(self) -> None:
        """Periodically clean up sessions that have timed out."""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                now = time.time()

                # Collect sessions to remove while holding the lock
                sessions_to_close = []
                async with self.sessions_lock:
                    # Check if we're over the session limit
                    if len(self.sessions) > MAX_SESSIONS:
                        # Remove oldest sessions first
                        sorted_sessions = sorted(
                            self.sessions.items(), key=lambda x: x[1].last_active
                        )
                        excess_count = len(self.sessions) - MAX_SESSIONS
                        for session_id, session in sorted_sessions[:excess_count]:
                            sessions_to_close.append((session_id, session))

                    # Remove inactive sessions
                    for sid, session in self.sessions.items():
                        if now - session.last_active > SESSION_TIMEOUT_SECONDS:
                            sessions_to_close.append((sid, session))

                # Close and remove sessions outside the lock to avoid blocking
                for session_id, session in sessions_to_close:
                    try:
                        await session.close()
                    except Exception as e:
                        logger.warning(f"Error closing session {session_id}: {e}")

                    async with self.sessions_lock:
                        self.sessions.pop(session_id, None)

                    # Clean up write stream
                    if session_id in self.mcp_server.write_streams:
                        del self.mcp_server.write_streams[session_id]

            except asyncio.CancelledError:
                # Cleanup task cancelled during shutdown
                break
            except Exception as e:
                logger.exception(f"Error in session cleanup: {e}")
                # Continue running even if there's an error

    def register(self, router: Router) -> None:
        """
        Register the MCP SSE route with the router.
        """
        # For MCP SSE, we need direct access to the FastAPI Request object,
        # so we bypass the normal router wrapper and register directly with FastAPI
        from arcade_serve.fastapi.worker import FastAPIRouter

        if isinstance(router, FastAPIRouter):
            # Register GET endpoint directly with FastAPI
            router.app.add_api_route(
                "/mcp",
                self.__call__,
                methods=["GET"],
                response_class=EventSourceResponse,
                operation_id="mcp_sse",
                description="MCP Server-Sent Events",
                summary="MCP Server-Sent Events",
                tags=["MCP"],
            )

            # Register POST endpoint directly with FastAPI
            auth_dependency = self.get_auth_dependency()
            router.app.add_api_route(
                "/mcp",
                self.__call__,
                methods=["POST"],
                dependencies=[Depends(auth_dependency)] if not self.worker.disable_auth else [],
                operation_id="mcp_post",
                description="MCP POST",
                summary="MCP POST",
                tags=["MCP"],
            )
        else:
            # Fallback to normal registration
            router.add_route(
                "mcp",
                self,
                method="GET",
                response_class=EventSourceResponse,
                operation_id="mcp_sse",
                description="MCP Server-Sent Events",
                summary="MCP Server-Sent Events",
                tags=["MCP"],
                require_auth=False,
            )

            auth_dependency = self.get_auth_dependency()
            router.add_route(
                "mcp",
                self,
                method="POST",
                operation_id="mcp_post",
                description="MCP POST",
                summary="MCP POST",
                tags=["MCP"],
                require_auth=not self.worker.disable_auth,
            )

    def get_auth_dependency(self) -> Callable:
        async def dependency(
            credentials: HTTPAuthorizationCredentials | None = Depends(self.security),
        ) -> None:
            if not self.worker.disable_auth and credentials:
                await validate_engine_request(self.worker.secret, credentials)

        return dependency

    async def __call__(self, request: Request) -> EventSourceResponse:
        """
        Handle the request to get the catalog.
        """
        if request.method == "GET":
            session_id = str(uuid.uuid4())
            session = Session(session_id)

            # Add session with lock
            async with self.sessions_lock:
                self.sessions[session_id] = session

            async def event_generator():
                try:
                    # Send the session ID as the first event
                    yield {
                        "event": "session_id",
                        "data": json.dumps({"session_id": session_id}),
                    }

                    # Stream messages from the session's queue
                    while True:
                        try:
                            # Use timeout to periodically check connection health
                            message = await asyncio.wait_for(session.queue.get(), timeout=30.0)
                            if message is None:  # Sentinel value
                                break
                            yield {"data": json.dumps(message)}
                        except asyncio.TimeoutError:
                            # Send keepalive ping
                            yield {"event": "ping", "data": "{}"}
                            continue
                except asyncio.CancelledError:
                    # Client disconnected
                    pass
                except Exception as e:
                    # Log unexpected errors
                    logger.exception(f"SSE stream error: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "Internal server error",
                            "status": "error",
                        }),
                    }
                finally:
                    # Clean up session on disconnect
                    async with self.sessions_lock:
                        if session_id in self.sessions:
                            del self.sessions[session_id]

                    # Clean up write stream
                    if session_id in self.mcp_server.write_streams:
                        del self.mcp_server.write_streams[session_id]

            return EventSourceResponse(event_generator())
        elif request.method == "POST":
            try:
                # Validate content type
                content_type = request.headers.get("content-type", "")
                if not content_type.startswith("application/json"):
                    return {
                        "status": "error",
                        "message": "Content-Type must be application/json",
                    }

                # Parse request body with size limit
                body_bytes = await request.body()
                if len(body_bytes) > 1024 * 1024:  # 1MB limit
                    return {
                        "status": "error",
                        "message": "Request body too large (max 1MB)",
                    }

                try:
                    body = json.loads(body_bytes)
                except json.JSONDecodeError as e:
                    return {"status": "error", "message": f"Invalid JSON: {e!s}"}

                session_id = request.headers.get("X-Session-ID")

                if body.get("method") == "initialize":
                    session_id = str(uuid.uuid4())
                    session = Session(session_id)

                    # Add session with lock
                    async with self.sessions_lock:
                        self.sessions[session_id] = session

                    # Create write stream adapter for SSE
                    class SSEWriteStream:
                        def __init__(self, session: Session):
                            self.session = session

                        async def send(self, message: str) -> None:
                            # Parse message and put in queue
                            try:
                                if isinstance(message, str):
                                    data = json.loads(message)
                                else:
                                    data = message
                                await self.session.queue.put(data)
                            except Exception:
                                logger.exception("Error sending SSE notification")

                    # Register write stream with MCP server
                    self.mcp_server.write_streams[session_id] = SSEWriteStream(session)

                    try:
                        response = await self.mcp_server.handle_message(body, user_id=session_id)
                        if response:
                            await session.queue.put(response.model_dump(exclude_none=True))
                    except Exception as e:
                        # Clean up session on error
                        async with self.sessions_lock:
                            if session_id in self.sessions:
                                del self.sessions[session_id]
                        # Clean up write stream
                        if session_id in self.mcp_server.write_streams:
                            del self.mcp_server.write_streams[session_id]
                        return {
                            "status": "error",
                            "message": f"Failed to initialize: {e!s}",
                        }

                    return {"status": "ok", "session_id": session_id}

                # Get session with lock
                async with self.sessions_lock:
                    if not session_id or session_id not in self.sessions:
                        return {
                            "status": "error",
                            "message": "Invalid or expired session ID",
                        }
                    session = self.sessions[session_id]

                session.touch()

                try:
                    response = await self.mcp_server.handle_message(body, user_id=session_id)
                    if response:
                        await session.queue.put(response.model_dump(exclude_none=True))
                    return {"status": "ok"}
                except Exception as e:
                    logger.exception(f"Error processing request: {e}")
                    return {
                        "status": "error",
                        "message": f"Failed to process request: {e!s}",
                    }

            except Exception as e:
                logger.exception(f"Unexpected error in SSE POST: {e}")
                return {"status": "error", "message": "Internal server error"}
