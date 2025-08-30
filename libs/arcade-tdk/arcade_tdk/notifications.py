"""
Arcade TDK Notifications

Implementation of notification functionality for tools.
Provides concrete implementations of the arcade_core notification protocols.
"""

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from arcade_core.notifications import ProgressContext as ProgressContextProtocol


class LogLevel(str, Enum):
    """Log levels for tool logging."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class NotificationBackend(Protocol):
    """Protocol for notification backends."""

    async def send_log(
        self,
        level: LogLevel,
        message: str,
        data: Any = None,
        logger_name: str | None = None,
    ) -> None:
        """Send a log notification."""
        ...

    async def send_progress(
        self,
        progress_token: str,
        progress: float,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        """Send a progress notification."""
        ...

    async def send_resource_updated(
        self,
        uri: str,
        timestamp: str | None = None,
    ) -> None:
        """Send a resource updated notification."""
        ...

    async def send_resource_list_changed(self) -> None:
        """Send a resource list changed notification."""
        ...


class NoOpBackend:
    """No-op notification backend for when notifications are disabled."""

    async def send_log(self, *args, **kwargs) -> None:
        pass

    async def send_progress(self, *args, **kwargs) -> None:
        pass

    async def send_resource_updated(self, *args, **kwargs) -> None:
        pass

    async def send_resource_list_changed(self) -> None:
        pass


@dataclass
class ProgressContext:
    """
    Context manager for tracking progress of operations.

    Example:
        async with context.notify.progress() as progress:
            for i, file in enumerate(files):
                await process_file(file)
                await progress.update(i + 1, len(files))
    """

    backend: NotificationBackend
    progress_token: str | None  # Can be None if client didn't provide one
    message: str | None
    start_time: float
    total: int | None = None
    _current: int = 0

    async def update(
        self,
        current: int,
        total: int | None = None,
        message: str | None = None,
    ) -> None:
        """
        Update progress.

        Args:
            current: Current progress value
            total: Total value (updates the total if provided)
            message: Optional progress message
        """
        # Only send progress if we have a progress token
        if not self.progress_token:
            return

        self._current = current
        if total is not None:
            self.total = total

        progress = current / self.total if self.total else float(current)

        await self.backend.send_progress(
            progress_token=self.progress_token,
            progress=progress,
            total=float(self.total) if self.total else None,
            message=message or self.message,
        )

    async def increment(self, message: str | None = None) -> None:
        """Increment progress by 1."""
        await self.update(self._current + 1, message=message)

    async def complete(self, message: str | None = None) -> None:
        """Mark the operation as complete."""
        if self.total:
            await self.update(self.total, message=message or "Complete")

    async def __aenter__(self):
        """Start tracking progress."""
        # Only send initial progress if we have a token
        if self.progress_token:
            await self.backend.send_progress(
                progress_token=self.progress_token,
                progress=0.0,
                total=float(self.total) if self.total else None,
                message=self.message or "Starting...",
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete progress tracking."""
        if exc_type is None and self.progress_token:
            await self.complete()


class ToolLogger:
    """
    Logger implementation for tools.

    Provides methods for different log levels:
    - debug: Detailed debugging information
    - info: General informational messages
    - warning: Warning conditions
    - error: Error conditions
    """

    def __init__(self, backend: NotificationBackend, tool_name: str | None = None):
        """
        Initialize the tool logger.

        Args:
            backend: The notification backend
            tool_name: Name of the tool for context
        """
        self._backend = backend
        self._tool_name = tool_name

    async def debug(self, message: str, data: Any = None) -> None:
        """Log a debug message."""
        await self._log(LogLevel.DEBUG, message, data)

    async def info(self, message: str, data: Any = None) -> None:
        """Log an info message."""
        await self._log(LogLevel.INFO, message, data)

    async def notice(self, message: str, data: Any = None) -> None:
        """Log a notice message."""
        await self._log(LogLevel.NOTICE, message, data)

    async def warning(self, message: str, data: Any = None) -> None:
        """Log a warning message."""
        await self._log(LogLevel.WARNING, message, data)

    async def error(self, message: str, data: Any = None) -> None:
        """Log an error message."""
        await self._log(LogLevel.ERROR, message, data)

    async def critical(self, message: str, data: Any = None) -> None:
        """Log a critical message."""
        await self._log(LogLevel.CRITICAL, message, data)

    async def _log(self, level: LogLevel, message: str, data: Any = None) -> None:
        """Internal method to send log messages."""
        # According to MCP spec, the 'data' field contains the actual log data
        # If data is provided, use it as the log data
        # Otherwise, use the message string as the log data
        log_data = data if data is not None else message

        await self._backend.send_log(
            level=level,
            message=message,  # This is used for backend's internal use
            data=log_data,  # This is what gets sent in the notification
            logger_name=self._tool_name,
        )


class ToolNotifier:
    """
    Notification implementation for tools.

    Provides methods for:
    - Progress tracking
    - Resource update notifications
    """

    def __init__(
        self, backend: NotificationBackend, progress_token: str | None = None
    ):
        """
        Initialize the tool notifier.

        Args:
            backend: The notification backend
            progress_token: Progress token from client request (if any)
        """
        self._backend = backend
        self._progress_token = progress_token

    def progress(
        self,
        message: str | None = None,
        total: int | None = None,
    ) -> ProgressContext:
        """
        Create a progress tracking context.

        Args:
            message: Initial progress message
            total: Total number of items (if known)

        Returns:
            A ProgressContext for tracking progress

        Example:
            async with context.notify.progress("Processing...", total=100) as p:
                for i in range(100):
                    await do_work()
                    await p.update(i + 1)
        """
        return ProgressContext(
            backend=self._backend,
            progress_token=self._progress_token,
            message=message,
            start_time=time.time(),
            total=total,
        )

    async def resource_updated(self, uri: str, timestamp: str | None = None) -> None:
        """
        Notify that a resource has been updated.

        Args:
            uri: The resource URI
            timestamp: Optional update timestamp
        """
        await self._backend.send_resource_updated(uri=uri, timestamp=timestamp)

    async def resource_list_changed(self) -> None:
        """Notify that the resource list has changed."""
        await self._backend.send_resource_list_changed()


def create_tool_logger(
    backend: NotificationBackend | None = None, tool_name: str | None = None
) -> ToolLogger:
    """
    Create a tool logger.

    Args:
        backend: The notification backend (uses NoOp if None)
        tool_name: Name of the tool for context

    Returns:
        A ToolLogger instance
    """
    return ToolLogger(backend or NoOpBackend(), tool_name)


def create_tool_notifier(
    backend: NotificationBackend | None = None, progress_token: str | None = None
) -> ToolNotifier:
    """
    Create a tool notifier.

    Args:
        backend: The notification backend (uses NoOp if None)
        progress_token: Progress token from client request

    Returns:
        A ToolNotifier instance
    """
    return ToolNotifier(backend or NoOpBackend(), progress_token)
