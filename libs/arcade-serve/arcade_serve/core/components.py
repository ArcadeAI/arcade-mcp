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
            require_auth=False,
            response_type=HealthCheckResponse,
            operation_id="health_check",
            description="Check the health of the worker",
            summary="Check the health of the worker",
            tags=["Arcade"],
        )

    async def __call__(self, request: RequestData) -> HealthCheckResponse:
        """
        Handle the request for a health check.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("HealthCheck"):
            return self.worker.health_check()
