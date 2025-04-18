from opentelemetry import trace

from arcade.worker.core.common import (
    CatalogResponse,
    HealthCheckResponse,
    MetricsResponse,
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
            tags=["base"],
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
            tags=["base"],
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
            tags=["base"],
        )

    async def __call__(self, request: RequestData) -> HealthCheckResponse:
        """
        Handle the request for a health check.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("HealthCheck"):
            return self.worker.health_check()


class MetricsComponent(WorkerComponent):
    def __init__(self, worker: Worker) -> None:
        self.worker = worker

    def register(self, router: Router) -> None:
        """
        Register the prometheus metrics route with the router.
        """
        router.add_route(
            "metrics",
            self,
            method="GET",
            require_auth=False,
            response_type=MetricsResponse,
            operation_id="get_metrics",
            description="Get the worker performance metrics",
            tags=["base"],
        )

    async def __call__(self, request: RequestData) -> str:
        """
        Handle the request for prometheus metrics.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("Metrics"):
            return await self.worker.get_metrics()
