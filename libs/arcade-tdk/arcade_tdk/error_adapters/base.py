from __future__ import annotations

from typing import Protocol, runtime_checkable

from arcade_tdk.errors import ToolRuntimeError


@runtime_checkable
class ErrorAdapter(Protocol):
    """
    Plugin that translates vendor-specific exceptions / responses into
    the appropriate Arcade Errors.
    """

    slug: str  # for logging & metrics

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        """
        Translate an exception raised by an SDK, HTTP client, etc.
        into a `ToolRuntimeError` subclass.
        """
        ...
