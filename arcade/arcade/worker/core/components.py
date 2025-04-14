from typing import Any, Optional, Protocol

from fastapi import FastAPI
from opentelemetry import trace

from arcade.core.catalog import ToolCatalog
from arcade.core.schema import ToolCallRequest, ToolCallResponse, ToolDefinition
from arcade.worker.core.common import RequestData, Router, Worker, WorkerComponent


class Component(Protocol):
    """Protocol for worker components that are not route-based."""

    def initialize(self) -> None:
        """Initialize the component."""
        pass


class ComponentProvider(Protocol):
    """Protocol for component providers that create components."""

    def get_component(
        self, app: FastAPI, catalog: ToolCatalog, **kwargs: Any
    ) -> Optional[Component]:
        """Get a component instance.

        Args:
            app: The FastAPI app to add routes to
            catalog: The tool catalog to serve
            **kwargs: Additional configuration options

        Returns:
            A component instance or None if the component should not be created
        """
        ...


class CatalogComponent(WorkerComponent):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """
        Register the catalog route with the router.
        """
        router.add_route("tools", self, method="GET")

    async def __call__(self, request: RequestData) -> list[ToolDefinition]:
        """
        Handle the request to get the catalog.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("Catalog"):
            return self.worker.get_catalog()


class CallToolComponent(WorkerComponent):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """
        Register the call tool route with the router.
        """
        router.add_route("tools/invoke", self, method="POST")

    async def __call__(self, request: RequestData) -> ToolCallResponse:
        """
        Handle the request to call (invoke) a tool.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("CallTool"):
            call_tool_request_data = request.body_json
            call_tool_request = ToolCallRequest.model_validate(call_tool_request_data)
            return await self.worker.call_tool(call_tool_request)


class HealthCheckComponent(WorkerComponent):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """
        Register the health check route with the router.
        """
        router.add_route("health", self, method="GET", require_auth=False)

    async def __call__(self, request: RequestData) -> dict[str, Any]:
        """
        Handle the request for a health check.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("HealthCheck"):
            return self.worker.health_check()
