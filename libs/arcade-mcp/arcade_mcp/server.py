"""Main Server class for arcade-mcp."""

import asyncio
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

from arcade_core.catalog import ToolCatalog
from arcade_core.toolkit import Toolkit
from dotenv import load_dotenv

from arcade_mcp.transports import SSETransport, StdioTransport, StreamTransport

logger = logging.getLogger(__name__)


class Server:
    """
    MCP Server that can run with different transports.
    
    Example:
        from arcade_mcp import Server
        from my_toolkit import tools
        
        server = Server()
        server.add_toolkit(tools)
        
        if __name__ == "__main__":
            server.run(transport="stream")
    """
    
    def __init__(
        self,
        *,
        name: str | None = None,
        version: str | None = None,
        auth_disabled: bool = False,
        local_context: dict[str, Any] | None = None,
    ):
        """
        Initialize the MCP server.
        
        Args:
            name: Server name (defaults to package name)
            version: Server version (defaults to package version)
            auth_disabled: Whether to disable authentication
            local_context: Local context configuration
        """
        self.name = name or self._get_default_name()
        self.version = version or self._get_default_version()
        self.auth_disabled = auth_disabled
        self.local_context = local_context or {}
        self.catalog = ToolCatalog()
        self._toolkits: list[Toolkit] = []
        self._tools: list[Any] = []
        
        # Load .env file if it exists
        self._load_env()
        
        # Auto-discover tools in the current package
        self._auto_discover_tools()
    
    def _get_default_name(self) -> str:
        """Get default server name from package."""
        # Try to get the package name from the calling module
        frame = inspect.currentframe()
        if frame and frame.f_back:
            module = inspect.getmodule(frame.f_back)
            if module and module.__package__:
                return module.__package__
        return "arcade-mcp-server"
    
    def _get_default_version(self) -> str:
        """Get default server version."""
        return "1.0.0"
    
    def _load_env(self) -> None:
        """Load .env file from the current directory."""
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logger.info(f"Loaded environment from {env_path}")
    
    def _auto_discover_tools(self) -> None:
        """Auto-discover tools in the current package."""
        # Try to import tools from the calling module's package
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            module = inspect.getmodule(frame.f_back.f_back)
            if module and module.__package__:
                try:
                    # Try to import tools module from the package
                    tools_module_name = f"{module.__package__}.tools"
                    tools_module = __import__(tools_module_name, fromlist=["*"])
                    
                    # Look for toolkit or tools
                    for name in dir(tools_module):
                        obj = getattr(tools_module, name)
                        if isinstance(obj, Toolkit):
                            self.add_toolkit(obj)
                            logger.info(f"Auto-discovered toolkit: {obj.name}")
                        elif hasattr(obj, "_arcade_tool") and callable(obj):
                            self._tools.append(obj)
                            logger.info(f"Auto-discovered tool: {name}")
                except ImportError:
                    # No tools module found, that's okay
                    pass
    
    def add_toolkit(self, toolkit: Toolkit) -> None:
        """
        Add a toolkit to the server.
        
        Args:
            toolkit: The toolkit to add
        """
        self._toolkits.append(toolkit)
        self.catalog.add_toolkit(toolkit)
        
        # Check for auth requirements
        self._check_auth_requirements(toolkit)
    
    def add_tool(self, tool: Callable) -> None:
        """
        Add a single tool to the server.
        
        Args:
            tool: The tool function to add
        """
        self._tools.append(tool)
        # Tools will be added to catalog when creating toolkit
    
    def _check_auth_requirements(self, toolkit: Toolkit) -> None:
        """Check if any tools require authentication."""
        for tools_dict in toolkit.tools.values():
            for tool in tools_dict:
                if hasattr(tool, "_arcade_tool_decorator"):
                    decorator = tool._arcade_tool_decorator
                    if decorator.get("requires_auth"):
                        self._ensure_auth_configured()
    
    def _ensure_auth_configured(self) -> None:
        """Ensure authentication is properly configured."""
        if self.auth_disabled:
            return
            
        # Check if user is logged in to Arcade
        try:
            from arcade_core.config import config
            if not config.api or not config.api.key:
                raise RuntimeError(
                    "Tools using requires_auth require an Arcade account and the "
                    "Arcade Cloud Service. Run 'arcade login' to continue."
                )
        except Exception:
            raise RuntimeError(
                "Tools using requires_auth require an Arcade account and the "
                "Arcade Cloud Service. Run 'arcade login' to continue."
            )
    
    def run(
        self,
        transport: str = "stream",
        host: str = "0.0.0.0",
        port: int = 8000,
        **kwargs: Any,
    ) -> None:
        """
        Run the server with the specified transport.
        
        Args:
            transport: Transport type ("stream", "sse", or "stdio")
            host: Host to bind to (for stream/sse transports)
            port: Port to bind to (for stream/sse transports)
            **kwargs: Additional transport-specific options
        """
        # Create a temporary toolkit from individual tools if any
        if self._tools and not self._toolkits:
            # Create a toolkit from the tools
            toolkit = self._create_toolkit_from_tools()
            self.add_toolkit(toolkit)
        
        # Select and run transport
        if transport == "stdio":
            transport_impl = StdioTransport(
                self.catalog, 
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
            )
            asyncio.run(transport_impl.run())
        elif transport == "sse":
            transport_impl = SSETransport(
                self.catalog,
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
            )
            transport_impl.run(host=host, port=port, **kwargs)
        elif transport == "stream":
            transport_impl = StreamTransport(
                self.catalog,
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
            )
            transport_impl.run(host=host, port=port, **kwargs)
        else:
            raise ValueError(
                f"Unknown transport '{transport}'. "
                "Choose from: stdio, sse, stream"
            )
    
    def _create_toolkit_from_tools(self) -> Toolkit:
        """Create a toolkit from individual tools."""
        # Import here to avoid circular dependency
        from arcade_core.toolkit import tool_to_materialized_tool
        
        toolkit = Toolkit(
            name=self.name,
            package_name=self.name.replace("-", "_"),
        )
        
        # Convert tool functions to MaterializedTools and add to toolkit
        for tool_func in self._tools:
            try:
                materialized = tool_to_materialized_tool(tool_func)
                if materialized:
                    # Add to toolkit's tools dictionary
                    tool_name = materialized.name
                    if tool_name not in toolkit.tools:
                        toolkit.tools[tool_name] = []
                    toolkit.tools[tool_name].append(materialized)
            except Exception as e:
                logger.warning(f"Failed to add tool {tool_func.__name__}: {e}")
        
        return toolkit