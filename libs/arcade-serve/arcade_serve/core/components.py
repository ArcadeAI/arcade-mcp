from arcade_core.schema import (
    ToolCallRequest,
    ToolCallResponse,
)
from opentelemetry import trace

from arcade_serve.core.common import (
    CatalogResponse,
    HealthCheckResponse,
    RequestData,
    Router,
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
        with tracer.start_as_current_span("CallTool") as current_span:
            call_tool_request_data = request.body_json
            call_tool_request = ToolCallRequest.model_validate(call_tool_request_data)

            current_span.set_attribute("tool_name", str(call_tool_request.tool.name))
            current_span.set_attribute("toolkit_version", str(call_tool_request.tool.version))
            current_span.set_attribute("toolkit_name", str(call_tool_request.tool.toolkit))
            if hasattr(self.worker, "environment"):
                current_span.set_attribute("environment", self.worker.environment)

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
        return self.worker.health_check()
