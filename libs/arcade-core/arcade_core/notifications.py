"""
Notification protocols and no-op implementations for arcade_core.

This module defines the base protocols for notifications without
depending on arcade_tdk, avoiding circular dependencies.
"""

from types import TracebackType
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolLogger(Protocol):
    """Protocol for tool logging functionality."""

    async def debug(self, message: str, data: Any = None) -> None:
        """Log a debug message."""
        ...

    async def info(self, message: str, data: Any = None) -> None:
        """Log an info message."""
        ...

    async def notice(self, message: str, data: Any = None) -> None:
        """Log a notice message."""
        ...

    async def warning(self, message: str, data: Any = None) -> None:
        """Log a warning message."""
        ...

    async def error(self, message: str, data: Any = None) -> None:
        """Log an error message."""
        ...

    async def critical(self, message: str, data: Any = None) -> None:
        """Log a critical message."""
        ...


@runtime_checkable
class ProgressContext(Protocol):
    """Protocol for progress tracking context."""

    async def update(
        self, current: int, total: int | None = None, message: str | None = None
    ) -> None:
        """Update progress."""
        ...

    async def increment(self, message: str | None = None) -> None:
        """Increment progress by 1."""
        ...

    async def complete(self, message: str | None = None) -> None:
        """Mark the operation as complete."""
        ...

    async def __aenter__(self) -> "ProgressContext":
        """Enter the progress context."""
        ...

    async def __aexit__(
        self,
        exc_type: BaseException | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the progress context."""
        ...


@runtime_checkable
class ToolNotifier(Protocol):
    """Protocol for tool notification functionality."""

    def progress(
        self,
        message: str | None = None,
        total: int | None = None,
        progress_token: str | None = None,
    ) -> ProgressContext:
        """Create a progress tracking context."""
        ...

    async def resource_updated(self, uri: str, timestamp: str | None = None) -> None:
        """Notify that a resource has been updated."""
        ...

    async def resource_list_changed(self) -> None:
        """Notify that the resource list has changed."""
        ...


class NoOpProgressContext:
    """No-op implementation of progress context."""

    async def update(
        self, current: int, total: int | None = None, message: str | None = None
    ) -> None:
        pass

    async def increment(self, message: str | None = None) -> None:
        pass

    async def complete(self, message: str | None = None) -> None:
        pass

    async def __aenter__(self) -> "NoOpProgressContext":
        return self

    async def __aexit__(
        self,
        exc_type: BaseException | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


class NoOpLogger:
    """No-op implementation of ToolLogger."""

    async def debug(self, message: str, data: Any = None) -> None:
        pass

    async def info(self, message: str, data: Any = None) -> None:
        pass

    async def notice(self, message: str, data: Any = None) -> None:
        pass

    async def warning(self, message: str, data: Any = None) -> None:
        pass

    async def error(self, message: str, data: Any = None) -> None:
        pass

    async def critical(self, message: str, data: Any = None) -> None:
        pass


class NoOpNotifier:
    """No-op implementation of ToolNotifier."""

    def progress(
        self,
        message: str | None = None,
        total: int | None = None,
        progress_token: str | None = None,
    ) -> ProgressContext:
        return NoOpProgressContext()

    async def resource_updated(self, uri: str, timestamp: str | None = None) -> None:
        pass

    async def resource_list_changed(self) -> None:
        pass
