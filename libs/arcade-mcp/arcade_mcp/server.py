"""Main Server class for arcade-mcp."""

# standard library
import asyncio
import inspect
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import toml  # TODO debate
from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.config import config
from arcade_core.toolkit import Toolkit
from dotenv import load_dotenv
from fastapi import FastAPI

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
        auth_disabled: bool = True,
        local_context: dict[str, Any] | None = None,
        app: FastAPI | None = None,
    ):
        """
        Initialize the MCP server.

        Args:
            name: Server name (defaults to package name)
            version: Server version (defaults to package version)
            auth_disabled: Whether to disable authentication (default: True for local development)
            local_context: Local context configuration
            app: FastAPI app to use
        """
        self.name = name or self._get_default_name()
        self.version = version or self._get_default_version()
        self.auth_disabled = auth_disabled
        self.local_context = local_context or {}
        self.app = app
        self.catalog = ToolCatalog()
        self._toolkits: list[Toolkit] = []
        self._tools: list[Callable] = []
        self._auto_discovered = False

        # Load .env file if it exists
        self._load_env()

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

    def _auto_discover_toolkit(self) -> None:
        """Auto-discover toolkits from (1) cwd, (2) pyproject packages, (3) installed."""
        if self._auto_discovered:
            return

        cwd = Path.cwd()
        discovered: list[Toolkit] = []
        seen: set[str] = set()

        def _add_toolkit(tk: Toolkit) -> None:
            if tk.package_name not in seen:
                self.add_toolkit(tk)
                discovered.append(tk)
                seen.add(tk.package_name)

        # (1) CWD
        try:
            if (cwd / "pyproject.toml").is_file():
                tk = Toolkit.from_directory(cwd)
                _add_toolkit(tk)
                logger.info(
                    f"Auto-discovered local toolkit '{tk.name}' with "
                    f"{sum(len(tools) for tools in tk.tools.values())} tools"
                )
        except Exception as e:
            logger.debug(f"Failed to load local toolkit from {cwd}: {e}")

        # (2) Pyproject-declared packages
        try:
            if toml and (cwd / "pyproject.toml").is_file():
                data = toml.load(cwd / "pyproject.toml")

                # project.name → try src/<name> and <name>
                pkg_name = (data.get("project") or {}).get("name")
                if isinstance(pkg_name, str) and pkg_name:
                    for base in (cwd / "src", cwd):
                        candidate = base / pkg_name
                        try:
                            if candidate.is_dir():
                                tk = Toolkit.from_directory(candidate)
                                _add_toolkit(tk)
                        except Exception as e:
                            logger.debug(f"Skipped candidate {candidate}: {e}")

                # setuptools find.include patterns
                includes = (
                    (data.get("tool") or {})
                    .get("setuptools", {})
                    .get("packages", {})
                    .get("find", {})
                    .get("include", [])
                )
                if isinstance(includes, list):
                    for inc in includes:
                        # try both src/ and flat layouts
                        for base in (cwd / "src", cwd):
                            candidate = base / str(inc).replace("*", "")
                            try:
                                if candidate.is_dir():
                                    tk = Toolkit.from_directory(candidate)
                                    _add_toolkit(tk)
                            except Exception as e:
                                logger.debug(f"Skipped include '{inc}' at {candidate}: {e}")
        except Exception as e:
            logger.debug(f"Failed parsing pyproject packages: {e}")

        # (3) Installed Arcade toolkits
        try:
            for tk in Toolkit.find_all_arcade_toolkits():
                _add_toolkit(tk)
        except Exception as e:
            logger.debug(f"Installed toolkit discovery failed: {e}")

        self._auto_discovered = True
        if discovered:
            logger.info(
                f"Auto-discovered {len(discovered)} toolkit(s): "
                f"{', '.join(t.package_name for t in discovered)}"
            )
        else:
            logger.debug("No toolkits found during auto-discovery")

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
        Add a single tool to the server. Local tools are grouped under the
        'Local' toolkit using the catalog's existing add_tool API.

        Args:
            tool: The tool function to add
        """
        # Register immediately under the synthetic 'Local' toolkit for clarity
        self.catalog.add_tool(tool, "Local")
        self._tools.append(tool)

        # Best-effort auth check for locally added tools
        try:
            # Wrap in a temporary ToolkitDefinition name for auth messages
            tmp_toolkit = Toolkit(
                name="Local",
                package_name="local",
                version="0.0.0",
                description="Locally defined tools",
                author=[],
                repository=None,
                homepage=None,
            )
            self._check_auth_requirements(tmp_toolkit)
        except Exception:
            # Do not block local dev on auth inspection failures
            pass

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
        if not config.api or not config.api.key:
            raise RuntimeError(
                "Tools using requires_auth require an Arcade account and the "
                "Arcade Cloud Service. Run 'arcade login' to continue."
            )

    def _log_tools(self) -> None:
        """Log all tools being served, grouped by toolkit (including 'Local')."""
        logger.info(f"Starting {self.name} v{self.version} MCP server")

        # Group tools by toolkit name from the catalog
        grouped: dict[str, list[MaterializedTool]] = defaultdict(list)
        for mt in self.catalog:
            tk_name = mt.definition.toolkit.name or "Unknown"
            grouped[tk_name].append(mt)

        total_tools = 0
        for tk_name, mats in grouped.items():
            total_tools += len(mats)
            logger.info(f"Loaded toolkit '{tk_name}' ({len(mats)} tools)")
            for mt in mats:
                origin = mt.meta.module
                logger.info(f"  - {mt.name} (module: {origin})")

        if total_tools == 0:
            logger.warning("No tools loaded! Make sure your package has @tool decorated functions.")
        else:
            logger.info(f"Total tools available: {total_tools}")

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
        # Auto-discover toolkits only if neither explicit toolkits nor local tools were added
        if not self._toolkits and not self._tools:
            self._auto_discover_toolkit()

        # Log tools being served (but not for stdio to avoid interfering with protocol)
        if transport != "stdio":
            self._log_tools()

        # Select and run transport
        if transport == "stdio":
            transport_impl = StdioTransport(
                self.catalog,
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
                app=self.app,
            )
            asyncio.run(transport_impl.run())
        elif transport == "sse":
            transport_impl = SSETransport(
                self.catalog,
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
                app=self.app,
            )
            transport_impl.run(host=host, port=port, **kwargs)
        elif transport == "stream":
            transport_impl = StreamTransport(
                self.catalog,
                auth_disabled=self.auth_disabled,
                local_context=self.local_context,
                app=self.app,
            )
            transport_impl.run(host=host, port=port, **kwargs)
        else:
            raise ValueError(f"Unknown transport '{transport}'. Choose from: stdio, sse, stream")
