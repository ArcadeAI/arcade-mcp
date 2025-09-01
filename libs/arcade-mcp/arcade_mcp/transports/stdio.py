"""Standard I/O transport for MCP."""

import logging
import sys
from typing import Any

from arcade_core.catalog import ToolCatalog
from arcade_serve.mcp.stdio import StdioServer
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class StdioTransport:
    """
    Standard I/O transport for MCP.

    This transport reads from stdin and writes to stdout, suitable for
    VS Code and command-line MCP clients.
    """

    def __init__(
        self,
        catalog: ToolCatalog,
        auth_disabled: bool = False,
        local_context: dict[str, Any] | None = None,
        app: FastAPI | None = None,
    ):
        """
        Initialize the stdio transport.

        Args:
            catalog: Tool catalog to serve
            auth_disabled: Whether authentication is disabled
            local_context: Local context configuration
            app: Optional FastAPI app to maintain a consistent constructor signature
        """
        self.app = app
        self.server = StdioServer(
            catalog,
            auth_disabled=auth_disabled,
            local_context=local_context,
        )

    async def run(self) -> None:
        """Run the stdio server."""
        # Configure logging to stderr to avoid interfering with stdio protocol
        self._configure_logging()

        logger.info("Starting MCP stdio server")
        try:
            await self.server.run()
        except KeyboardInterrupt:
            logger.info("MCP stdio server stopped by user")
        except Exception:
            logger.exception("Error running MCP stdio server")
            raise
        finally:
            logger.info("MCP stdio server shutting down")

    def _configure_logging(self) -> None:
        """Configure logging to use stderr."""
        # Remove all existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add stderr handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
