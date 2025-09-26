"""Lifespan management for MCP server.

Provides a clean interface for managing server lifecycle with proper
resource initialization and cleanup.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Callable

from arcade_mcp_server.exceptions import LifespanError

logger = logging.getLogger("arcade.mcp")

LifespanResult = dict[str, Any]


@asynccontextmanager
async def default_lifespan(server: Any) -> AsyncIterator[LifespanResult]:
    """Default lifespan that does basic startup/shutdown logging."""
    logger.info(f"Starting MCP server: {getattr(server, 'name', 'unknown')}")

    # Startup
    try:
        yield {}
    finally:
        # Shutdown
        logger.info(f"Stopping MCP server: {getattr(server, 'name', 'unknown')}")


class LifespanManager:
    """Manages server lifecycle with proper resource management.

    This class wraps a lifespan context manager and provides a clean
    interface for server startup and shutdown operations.
    """

    def __init__(
        self,
        server: Any,
        lifespan: Callable[[Any], AbstractAsyncContextManager[LifespanResult]] | None = None,
    ):
        """Initialize lifespan manager.

        Args:
            server: The server instance
            lifespan: Optional custom lifespan function
        """
        self.server = server
        self.lifespan = lifespan or default_lifespan
        self._stack: Any | None = None
        self._context: LifespanResult | None = None
        self._started = False

    async def startup(self) -> LifespanResult:
        """Run startup phase of lifespan."""
        if self._started:
            raise LifespanError("Lifespan already started")

        self._started = True

        self._stack = asyncio.create_task(self._run_lifespan())

        # Wait for startup to complete
        while self._context is None and not self._stack.done():
            await asyncio.sleep(0.01)

        if self._stack.done() and self._context is None:
            # Lifespan failed during startup
            try:
                await self._stack
            except Exception as e:
                raise LifespanError(f"Lifespan startup failed: {e}") from e

        if self._context is None:
            raise LifespanError("Lifespan startup failed")
        return self._context

    async def shutdown(self) -> None:
        """Run shutdown phase of lifespan."""
        if not self._started:
            return

        self._started = False

        if self._stack and not self._stack.done():
            # Trigger shutdown by cancelling the lifespan task
            self._stack.cancel()
            try:
                await self._stack
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Error during lifespan shutdown")

        self._context = None
        self._stack = None

    async def _run_lifespan(self) -> None:
        """Run the lifespan context manager."""
        try:
            async with self.lifespan(self.server) as context:
                self._context = context
                # Keep running until cancelled
                while True:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Normal shutdown
            self._context = None
            raise
        except Exception:
            # Abnormal shutdown
            self._context = None
            logger.exception("Error in lifespan")
            raise

    async def __aenter__(self) -> LifespanResult:
        """Async context manager entry."""
        return await self.startup()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()


def compose_lifespans(
    *lifespans: Callable[[Any], AbstractAsyncContextManager[LifespanResult]],
) -> Callable[[Any], AbstractAsyncContextManager[LifespanResult]]:
    """Compose multiple lifespan functions into one.

    Each lifespan's context is merged into a single dict.
    Lifespans are started in order and stopped in reverse order.
    """

    @asynccontextmanager
    async def composed(server: Any) -> AsyncIterator[LifespanResult]:
        contexts: list[tuple[AbstractAsyncContextManager[LifespanResult], LifespanResult]] = []
        merged: LifespanResult = {}

        # Start lifespans in order (sequential for compatibility)
        for lifespan in lifespans:
            ctx_mgr = lifespan(server)
            context = await ctx_mgr.__aenter__()
            contexts.append((ctx_mgr, context))

            # Merge context if it's a dict
            merged.update(context)

        try:
            yield merged
        finally:
            # Stop lifespans in reverse order
            for ctx_mgr, _ in reversed(contexts):
                try:
                    await ctx_mgr.__aexit__(None, None, None)
                except Exception:
                    logger.exception("Error stopping lifespan")

    return composed
