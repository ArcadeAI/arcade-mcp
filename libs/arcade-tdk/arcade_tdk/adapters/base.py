# arcade_tdk/adapters/base.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

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

    def from_response(self, resp: Any) -> ToolRuntimeError | None:
        """
        Translate a successful response from a SDK, HTTP client, etc.
        that encloses an error into a `ToolRuntimeError` subclass.
        """
        ...
