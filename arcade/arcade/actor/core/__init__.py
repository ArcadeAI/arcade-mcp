from abc import ABC, abstractmethod
from typing import Any, Callable

from arcade.core.schema import InvokeToolRequest, InvokeToolResponse, ToolDefinition


class Router(ABC):
    """
    A router is responsible for adding routes to the underlying framework hosting the actor.
    """

    @abstractmethod
    def add_route(self, endpoint_path: str, handler: Callable, method: str) -> None:
        """
        Add a route to the router.
        """
        pass


class Actor(ABC):
    """
    An Actor represents a collection of tools that is hosted inside a web framework
    and can be invoked by an Engine.
    """

    @abstractmethod
    def get_catalog(self) -> list[ToolDefinition]:
        pass

    @abstractmethod
    async def invoke_tool(self, request: InvokeToolRequest) -> InvokeToolResponse:
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        pass
