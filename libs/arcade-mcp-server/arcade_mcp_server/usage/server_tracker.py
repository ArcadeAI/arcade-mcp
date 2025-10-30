import platform
import sys
import time
from importlib import metadata

from arcade_core.usage import UsageIdentity, UsageService, is_tracking_enabled
from arcade_core.usage.constants import (
    PROP_DEVICE_TIMESTAMP,
    PROP_OS_RELEASE,
    PROP_OS_TYPE,
    PROP_RUNTIME_LANGUAGE,
    PROP_RUNTIME_VERSION,
)

from arcade_mcp_server.usage.constants import (
    EVENT_MCP_SERVER_STARTED,
    EVENT_MCP_TOOL_CALLED,
    PROP_FAILURE_REASON,
    PROP_HOST,
    PROP_IS_EXECUTION_SUCCESS,
    PROP_MCP_SERVER_VERSION,
    PROP_PORT,
    PROP_TOOL_COUNT,
    PROP_TRANSPORT,
)


class ServerTracker:
    """Tracks MCP server events for usage analytics.

    To opt out, set the ARCADE_USAGE_TRACKING environment variable to 0.
    """

    def __init__(self) -> None:
        self.usage_service = UsageService()
        self.identity = UsageIdentity()
        self._mcp_server_version: str | None = None
        self._runtime_version: str | None = None

    @property
    def mcp_server_version(self) -> str:
        """Get the version of arcade_mcp_server package"""
        if self._mcp_server_version is None:
            try:
                self._mcp_server_version = metadata.version("arcade-mcp-server")
            except Exception:
                self._mcp_server_version = "unknown"
        return self._mcp_server_version

    @property
    def runtime_version(self) -> str:
        """Get the version of the Python runtime"""
        if self._runtime_version is None:
            version_info = sys.version_info
            self._runtime_version = (
                f"{version_info.major}.{version_info.minor}.{version_info.micro}"
            )
        return self._runtime_version

    @property
    def user_id(self) -> str:
        """Get the distinct_id based on developer's authentication state"""
        return self.identity.get_distinct_id()

    def track_server_start(
        self,
        transport: str,
        host: str | None,
        port: int | None,
        tool_count: int,
    ) -> None:
        """Track MCP server start event.

        Args:
            transport: The transport type ("http" or "stdio")
            host: The host address (None for stdio)
            port: The port number (None for stdio)
            tool_count: The number of tools available at server start
        """
        if not is_tracking_enabled():
            return

        # Check if aliasing needed (user authenticated but not yet linked)
        if self.identity.should_alias():
            principal_id = self.identity.get_principal_id()
            if principal_id:
                self.usage_service.alias(
                    previous_id=self.identity.anon_id, distinct_id=principal_id
                )
                self.identity.set_linked_principal_id(principal_id)

        properties: dict[str, str | int | float] = {
            PROP_TRANSPORT: transport,
            PROP_TOOL_COUNT: tool_count,
            PROP_MCP_SERVER_VERSION: self.mcp_server_version,
            PROP_RUNTIME_LANGUAGE: "python",
            PROP_RUNTIME_VERSION: self.runtime_version,
            PROP_OS_TYPE: platform.system(),
            PROP_OS_RELEASE: platform.release(),
            PROP_DEVICE_TIMESTAMP: time.monotonic(),
        }

        # HTTP Streamable specific props
        if host is not None:
            properties[PROP_HOST] = host
        if port is not None:
            properties[PROP_PORT] = port

        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(
            EVENT_MCP_SERVER_STARTED, self.user_id, properties=properties, is_anon=is_anon
        )

    def track_tool_call(
        self,
        success: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Track MCP tool call event.

        Args:
            success: Whether the tool call succeeded (True) or failed (False)
            reason: The reason for the failure (if any)
        """
        if not is_tracking_enabled():
            return

        properties: dict[str, str | int | float | bool | None] = {
            PROP_IS_EXECUTION_SUCCESS: success,
            PROP_FAILURE_REASON: failure_reason if not success else None,
            PROP_MCP_SERVER_VERSION: self.mcp_server_version,
            PROP_RUNTIME_LANGUAGE: "python",
            PROP_RUNTIME_VERSION: self.runtime_version,
            PROP_OS_TYPE: platform.system(),
            PROP_OS_RELEASE: platform.release(),
            PROP_DEVICE_TIMESTAMP: time.monotonic(),
        }

        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(
            EVENT_MCP_TOOL_CALLED, self.user_id, properties=properties, is_anon=is_anon
        )
