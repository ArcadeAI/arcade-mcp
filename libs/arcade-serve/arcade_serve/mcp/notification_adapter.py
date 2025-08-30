"""
MCP Notification Adapter

Bridges the arcade_tdk NotificationBackend protocol to the MCP NotificationManager.
"""

from typing import Any

from arcade_tdk import LogLevel

from arcade_serve.mcp.notification_manager import NotificationManager
from arcade_serve.mcp.types import LogLevel as MCPLogLevel

# Log level priority for filtering (higher number = higher severity)
LOG_LEVEL_PRIORITY = {
    "debug": 0,
    "info": 1,
    "notice": 2,
    "warning": 3,
    "error": 4,
    "critical": 5,
    "alert": 6,
    "emergency": 7,
}


class MCPNotificationBackend:
    """
    Adapter that implements the arcade_tdk NotificationBackend protocol
    by forwarding calls to the MCP NotificationManager.
    """

    def __init__(
        self,
        notification_manager: NotificationManager,
        user_id: str,
        min_log_level: str = "info",
    ):
        """
        Initialize the MCP notification backend.

        Args:
            notification_manager: The MCP notification manager
            user_id: The user/client ID for this connection
            min_log_level: Minimum log level to send (default: info)
        """
        self.notification_manager = notification_manager
        self.user_id = user_id
        self.min_log_level = min_log_level

    def set_min_log_level(self, level: str) -> None:
        """Update the minimum log level."""
        self.min_log_level = level

    def _should_send_log(self, level: str) -> bool:
        """Check if a log level should be sent based on minimum level."""
        log_priority = LOG_LEVEL_PRIORITY.get(level, 0)
        min_priority = LOG_LEVEL_PRIORITY.get(self.min_log_level, 0)
        return log_priority >= min_priority

    async def send_log(
        self,
        level: LogLevel,
        message: str,
        data: Any = None,
        logger_name: str | None = None,
    ) -> None:
        """Send a log notification via MCP."""
        # Check if we should send this log level
        if not self._should_send_log(level.value):
            return

        # Convert LogLevel enum to MCP LogLevel
        mcp_level = MCPLogLevel(level.value)

        # Format the data according to MCP spec
        # The 'data' field should contain the actual log data,
        # which can be a string message or structured data
        log_data = data if data is not None else message

        await self.notification_manager.notify_message(
            level=mcp_level,
            data=log_data,
            logger_name=logger_name,
            client_ids=[self.user_id],
        )

    async def send_progress(
        self,
        progress_token: str,
        progress: float,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        """Send a progress notification via MCP."""
        await self.notification_manager.notify_progress(
            progress_token=progress_token,
            progress=progress,
            total=total,
            message=message,
            client_ids=[self.user_id],
            debounce_ms=0,  # Disable debouncing for progress notifications
        )

    async def send_resource_updated(
        self,
        uri: str,
        timestamp: str | None = None,
    ) -> None:
        """Send a resource updated notification via MCP."""
        await self.notification_manager.notify_resource_updated(
            uri=uri,
            timestamp=timestamp,
            client_ids=[self.user_id],
        )

    async def send_resource_list_changed(self) -> None:
        """Send a resource list changed notification via MCP."""
        await self.notification_manager.notify_resource_list_changed(
            client_ids=[self.user_id],
        )
