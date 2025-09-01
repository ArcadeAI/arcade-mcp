"""HTTPS streaming transport for MCP."""

import logging
from typing import Any

import uvicorn
from arcade_core.catalog import ToolCatalog
from arcade_serve.fastapi.stream import StreamComponent
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class StreamTransport:
    """
    HTTPS streaming transport for MCP.

    This is the default transport that works with Claude Desktop, Claude Code,
    and Cursor. It provides an HTTPS endpoint with streaming responses.

    Args:
        catalog: Tool catalog to serve
        auth_disabled: Whether authentication is disabled
        local_context: Local context configuration
        app: FastAPI app to use
    """

    def __init__(
        self,
        catalog: ToolCatalog,
        auth_disabled: bool = False,
        local_context: dict[str, Any] | None = None,
        app: FastAPI | None = None,
    ):
        """
        Initialize the stream transport.

        Args:
            catalog: Tool catalog to serve
            auth_disabled: Whether authentication is disabled
            local_context: Local context configuration
            app: FastAPI app to use
        """
        self.catalog = catalog
        self.auth_disabled = auth_disabled
        self.local_context = local_context
        self.app = app

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        reload: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Run the streaming server.

        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Whether to enable auto-reload
            **kwargs: Additional uvicorn options
        """
        if self.app is None:
            # Create FastAPI app
            self.app = FastAPI(
                title="Arcade MCP Server",
                description="MCP server with HTTPS streaming transport",
                version="1.0.0",
            )

        # Create worker with Stream component
        worker = FastAPIWorker(
            app=self.app,
            disable_auth=self.auth_disabled,
        )

        # Set the catalog on the worker directly
        worker.catalog = self.catalog

        # Register Stream component with local context
        worker.register_component(StreamComponent, local_context=self.local_context)

        # Configure logging
        log_level = kwargs.pop("log_level", "info")

        logger.info(f"Starting MCP streaming server on {host}:{port}")

        # Run with uvicorn
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            **kwargs,
        )
