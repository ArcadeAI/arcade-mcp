"""
Arcade Core Runtime Context Protocols

Defines the developer-facing, transport-agnostic runtime context interfaces
(namespaced APIs: logs, progress, resources, tools, prompts, sampling, UI,
notifications) and the top-level ModelContext Protocol that aggregates them.

Implementations live in runtime packages (e.g., arcade_mcp_server); tool authors should
use `arcade_mcp_server.Context` for concrete usage.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class LogsContext(Protocol):
    async def debug(self, message: str, **kwargs: dict[str, Any]) -> None: ...

    async def info(self, message: str, **kwargs: dict[str, Any]) -> None: ...

    async def warning(self, message: str, **kwargs: dict[str, Any]) -> None: ...

    async def error(self, message: str, **kwargs: dict[str, Any]) -> None: ...


class ProgressContext(Protocol):
    async def report(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None: ...


class ResourcesContext(Protocol):
    async def list_(self) -> list[Any]: ...

    async def get(self, uri: str) -> Any: ...

    async def read(self, uri: str) -> list[Any]: ...

    async def list_roots(self) -> list[Any]: ...

    async def list_templates(self) -> list[Any]: ...


class ToolsContext(Protocol):
    async def list_(self) -> list[Any]: ...

    async def call_raw(self, name: str, params: dict[str, Any]) -> BaseModel: ...


class PromptsContext(Protocol):
    async def list_(self) -> list[Any]: ...

    async def get(self, name: str, arguments: dict[str, str] | None = None) -> Any: ...


class SamplingContext(Protocol):
    async def create_message(
        self,
        messages: str | list[str | Any],
        system_prompt: str | None = None,
        include_context: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model_preferences: Any | None = None,
    ) -> Any: ...


class UIContext(Protocol):
    async def elicit(self, message: str, schema: dict[str, Any] | None = None) -> Any: ...


class NotificationsToolsContext(Protocol):
    async def list_changed(self) -> None: ...


class NotificationsResourcesContext(Protocol):
    async def list_changed(self) -> None: ...


class NotificationsPromptsContext(Protocol):
    async def list_changed(self) -> None: ...


class NotificationsContext(Protocol):
    @property
    def tools(self) -> NotificationsToolsContext: ...

    @property
    def resources(self) -> NotificationsResourcesContext: ...

    @property
    def prompts(self) -> NotificationsPromptsContext: ...


@runtime_checkable
class ModelContext(Protocol):
    @property
    def log(self) -> LogsContext: ...

    @property
    def progress(self) -> ProgressContext: ...

    @property
    def resources(self) -> ResourcesContext: ...

    @property
    def tools(self) -> ToolsContext: ...

    @property
    def prompts(self) -> PromptsContext: ...

    @property
    def sampling(self) -> SamplingContext: ...

    @property
    def ui(self) -> UIContext: ...

    @property
    def notifications(self) -> NotificationsContext: ...

    @property
    def request_id(self) -> str | None: ...

    @property
    def session_id(self) -> str | None: ...
