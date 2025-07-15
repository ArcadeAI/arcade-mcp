from abc import ABC, abstractmethod
from typing import Any, Callable

from arcade_core.schema import ToolCallRequest, ToolCallResponse, ToolDefinition
from pydantic import BaseModel

CatalogResponse = list[ToolDefinition]
HealthCheckResponse = dict[str, str]
JSONResponse = dict[str, Any]
ResponseData = CatalogResponse | ToolCallResponse | HealthCheckResponse


class RequestData(BaseModel):
    """
    The raw data for a request to a worker.
    This is not intended to represent everything about an HTTP request,
    but just the essential info a framework integration will need to extract from the request.
    """

    path: str
    """The path of the request."""
    method: str
    """The method of the request."""
    body_json: JSONResponse | None = None
    """The deserialized body of the request (e.g. JSON)"""


class Router(ABC):
    """
    A router is responsible for adding routes to the underlying framework hosting the worker.
    """

    @abstractmethod
    def add_route(
        self,
        endpoint_path: str,
        handler: Callable,
        method: str,
        require_auth: bool = True,
        response_type: type[ResponseData] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a route to the router.
        """
        pass


class Worker(ABC):
    """
    A Worker represents a collection of tools that is hosted inside a web framework
    and can be called by an Engine.
    """

    @abstractmethod
    def get_catalog(self) -> CatalogResponse:
        """
        Get the catalog of tools available in the worker.
        """
        pass

    @abstractmethod
    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """
        Send a request to call a tool to the Worker
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthCheckResponse:
        """
        Perform a health check of the worker
        """
        pass


class WorkerComponent(ABC):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    @abstractmethod
    def register(self, router: Router) -> None:
        """
        Register the component with the given router.
        """
        pass

    @abstractmethod
    async def __call__(self, request: RequestData) -> ResponseData:
        """
        Handle the request.
        """
        pass
