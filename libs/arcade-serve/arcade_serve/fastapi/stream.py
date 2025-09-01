import asyncio
import contextlib
import json
import time
import uuid
from logging import getLogger
from typing import Any, Callable

from fastapi import Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcade_serve.core.common import (
    Router,
    Worker,
    WorkerComponent,
)
from arcade_serve.fastapi.auth import validate_engine_request
from arcade_serve.mcp.server import MCPServer

logger = getLogger("arcade.mcp")

SESSION_TIMEOUT_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL_SECONDS = 10  # Check every 10 seconds instead of 60
MAX_SESSIONS = 1000  # Maximum number of concurrent sessions


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


class StreamComponent(WorkerComponent):
    def __init__(self, worker: Worker, local_context: dict[str, Any] | None = None) -> None:
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
                    with contextlib.suppress(Exception):
                        await session.close()

                    async with self.sessions_lock:
                        self.sessions.pop(session_id, None)

                    # Clean up write stream
                    if session_id in self.mcp_server.write_streams:
                        del self.mcp_server.write_streams[session_id]

            except asyncio.CancelledError:
                # Cleanup task cancelled during shutdown
                break
            except Exception:
                logger.exception("Error in session cleanup")
                # Continue running even if there's an error

    def register(self, router: Router) -> None:
        """
        Register the MCP Stream route with the router.
        """
        # For MCP streaming, we need direct access to the FastAPI Request object,
        # so we bypass the normal router wrapper and register directly with FastAPI
        from arcade_serve.fastapi.worker import FastAPIRouter

        if isinstance(router, FastAPIRouter):
            auth_dependency = self.get_auth_dependency()
            # Register directly with FastAPI to avoid the RequestData wrapper

            dependencies = [Depends(auth_dependency)] if not self.worker.disable_auth else []

            router.app.add_api_route(
                "/mcp",
                self.__call__,
                methods=["POST"],
                response_class=StreamingResponse,
                dependencies=dependencies,
                operation_id="mcp_stream",
                description="MCP HTTPS Stream",
                summary="MCP HTTPS Stream",
                tags=["MCP"],
            )
        else:
            # Fallback to normal registration (though this won't work properly)
            router.add_route(
                "mcp",
                self,
                method="POST",
                response_class=StreamingResponse,
                operation_id="mcp_stream",
                description="MCP HTTPS Stream",
                summary="MCP HTTPS Stream",
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

    async def __call__(self, request: Request) -> StreamingResponse:
        """
        Handle the request to stream the response.
        """
        # Validate request before processing
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return StreamingResponse(
                iter([
                    json.dumps({
                        "error": "Content-Type must be application/json",
                        "status": "error",
                    })
                    + "\n"
                ]),
                media_type="application/json",
                status_code=400,
            )

        # Read request body BEFORE creating StreamingResponse
        try:
            body_bytes = await request.body()
        except Exception:
            logger.exception("Error reading request body")
            return StreamingResponse(
                iter([
                    json.dumps({
                        "error": "Failed to read request body",
                        "status": "error",
                    })
                    + "\n"
                ]),
                media_type="application/json",
                status_code=400,
            )

        session_id = str(uuid.uuid4())
        session = Session(session_id)

        # Add session with lock
        async with self.sessions_lock:
            self.sessions[session_id] = session

        # Create write stream adapter for streaming
        class StreamWriteStream:
            def __init__(self, session: Session):
                self.session = session

            async def send(self, message: str) -> None:
                # Parse message and put in queue as dict
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                    else:
                        data = message
                    await self.session.queue.put(data)
                except Exception:
                    logger.exception("Error sending stream notification")

        # Register write stream with MCP server
        self.mcp_server.write_streams[session_id] = StreamWriteStream(session)

        async def stream_generator():
            # Give the processing task a moment to start
            await asyncio.sleep(0.1)
            try:
                while True:
                    try:
                        # Use timeout to detect stalled connections
                        message = await asyncio.wait_for(session.queue.get(), timeout=60.0)
                        if message is None:  # Sentinel value
                            break
                        # Always emit a single JSON object per line
                        yield json.dumps(message) + "\n"
                    except asyncio.TimeoutError:
                        # Send keepalive message
                        yield (json.dumps({"type": "ping", "timestamp": time.time()}) + "\n")
                        continue
            except asyncio.CancelledError:
                # Client disconnected
                pass
            except Exception:
                logger.exception("Stream error")
                yield json.dumps({"error": "Stream error", "status": "error"}) + "\n"
            finally:
                # Clean up session on disconnect
                async with self.sessions_lock:
                    if session_id in self.sessions:
                        del self.sessions[session_id]

                # Clean up write stream
                if session_id in self.mcp_server.write_streams:
                    del self.mcp_server.write_streams[session_id]

        async def process_request(body_bytes: bytes):
            try:
                if len(body_bytes) > 1024 * 1024:  # 1MB limit
                    await session.queue.put({
                        "error": "Request body too large (max 1MB)",
                        "status": "error",
                    })
                    await session.close()
                    return

                try:
                    body = json.loads(body_bytes)
                except json.JSONDecodeError as e:
                    await session.queue.put({
                        "error": f"Invalid JSON: {e!s}",
                        "status": "error",
                    })
                    await session.close()
                    return

                # Validate required fields
                if "method" not in body:
                    await session.queue.put({
                        "error": "Missing 'method' field in request",
                        "status": "error",
                    })
                    await session.close()
                    return

                # Process the request
                try:
                    response = await self.mcp_server.handle_message(body, user_id=session_id)
                    if response:
                        # Handle both dict and Pydantic model responses
                        if hasattr(response, "model_dump"):
                            response_data = response.model_dump(exclude_none=True)
                        else:
                            response_data = response
                        await session.queue.put(response_data)
                except Exception as e:
                    logger.exception("Error processing message")
                    await session.queue.put({
                        "error": f"Failed to process request: {e!s}",
                        "status": "error",
                    })

            except asyncio.CancelledError:
                # Request processing cancelled
                pass
            except Exception:
                logger.exception("Unexpected error in request processing")
                await session.queue.put({
                    "error": "Internal server error",
                    "status": "error",
                })
            finally:
                # Signal the end of the stream
                await session.close()

        # Start processing the request in the background with the pre-read body
        processing_task = asyncio.create_task(process_request(body_bytes))

        # Monitor for early client disconnection
        async def monitor_disconnect():
            try:
                # Wait for client disconnect signal
                await request.is_disconnected()
                processing_task.cancel()
            except Exception:
                logger.exception("Unexpected error in monitor_disconnect")

        asyncio.run_coroutine_threadsafe(monitor_disconnect(), asyncio.get_running_loop())

        return StreamingResponse(
            stream_generator(),
            media_type="application/json",
            headers={
                "X-Session-ID": session_id,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
