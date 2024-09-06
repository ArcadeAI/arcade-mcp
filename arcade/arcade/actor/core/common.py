from abc import ABC, abstractmethod
from typing import Any, Callable

from pydantic import BaseModel

from arcade.core.schema import ToolCallRequest, ToolCallResponse, ToolDefinition


class RequestData(BaseModel):
    """
    The raw data for a request to an actor.
    This is not intended to represent everything about an HTTP request,
    but just the essential info a framework integration will need to extract from the request.
    """

    path: str
    """The path of the request."""
    method: str
    """The method of the request."""
    body_json: dict | None = None
    """The deserialized body of the request (e.g. JSON)"""


class Router(ABC):
    """
    A router is responsible for adding routes to the underlying framework hosting the actor.
    """

    @abstractmethod
    def add_route(
        self, endpoint_path: str, handler: Callable, method: str, require_auth: bool = True
    ) -> None:
        """
        Add a route to the router.
        """
        pass


class Actor(ABC):
    """
    An Actor represents a collection of tools that is hosted inside a web framework
    and can be called by an Engine.
    """

    @abstractmethod
    def get_catalog(self) -> list[ToolDefinition]:
        """
        Get the catalog of tools available in the actor.
        """
        pass

    @abstractmethod
    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """
        Send a request to call a tool to the Actor
        """
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Perform a health check of the actor
        """
        pass


class ActorComponent(ABC):
    def __init__(self, actor: Actor) -> None:
        self.actor = actor

    @abstractmethod
    def register(self, router: Router) -> None:
        """
        Register the component with the given router.
        """
        pass

    @abstractmethod
    async def __call__(self, request: RequestData) -> Any:
        """
        Handle the request.
        """
        pass
