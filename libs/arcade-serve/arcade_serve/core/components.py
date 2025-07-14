from typing import Any

from opentelemetry import trace

from arcade_serve.core.common import (
    CatalogResponse,
    HealthCheckResponse,
    RequestData,
    Router,
    ToolCallRequest,
    ToolCallResponse,
    Worker,
    WorkerComponent,
)


class CatalogComponent(WorkerComponent):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """
        Register the catalog route with the router.
        """
        router.add_route(
            "tools",
            self,
            method="GET",
            response_type=CatalogResponse,
            operation_id="get_catalog",
            description="Get the catalog of tools",
            summary="Get the catalog of tools",
            tags=["Arcade"],
        )

    async def __call__(self, request: RequestData) -> CatalogResponse:
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
        router.add_route(
            "tools/invoke",
            self,
            method="POST",
            response_type=ToolCallResponse,
            operation_id="call_tool",
            description="Call a tool",
            summary="Call a tool",
            tags=["Arcade"],
        )

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
        router.add_route(
            "health",
            self,
            method="GET",
            response_type=HealthCheckResponse,
            operation_id="health_check",
            description="Health check",
            summary="Health check",
            tags=["Arcade"],
            require_auth=False,
        )

    async def __call__(self, request: RequestData) -> HealthCheckResponse:
        """
        Handle the request to check the health of the worker.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("HealthCheck"):
            return self.worker.health_check()


class SchemaComponent(WorkerComponent):
    """Component for exposing tool schemas including input and output types."""

    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """Register the schema route with the router."""
        router.add_route(
            "tools/{tool_name}/schema",
            self,
            method="GET",
            response_type=dict,
            operation_id="get_tool_schema",
            description="Get the input and output schema for a specific tool",
            summary="Get tool schema",
            tags=["Arcade"],
        )

    async def __call__(self, request: RequestData) -> dict[str, Any]:
        """Handle the request to get a tool's schema."""
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("GetToolSchema"):
            # Extract tool name from path
            path_parts = request.path.strip("/").split("/")
            if len(path_parts) < 3:
                raise ValueError("Invalid path format")

            tool_name = path_parts[2]  # /tools/{tool_name}/schema
            return self.worker.get_tool_schema(tool_name)
