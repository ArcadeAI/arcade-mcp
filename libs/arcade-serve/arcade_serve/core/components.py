import os
from typing import Any

from arcade_core.schema import (
    ToolCallRequest,
    ToolCallResponse,
    ToolContext,
    ToolMetadataItem,
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
            "catalog",
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
        Handle the request to get the catalog of tools.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("GetCatalog"):
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


class LocalContextCallToolComponent(CallToolComponent):
    """
    Enhanced CallToolComponent that applies local context from worker.toml
    to tool invocations for local development.
    """

    def __init__(self, worker: Worker, local_context: dict[str, Any] | None = None) -> None:
        super().__init__(worker)
        self.local_context = local_context or {}

    async def __call__(self, request: RequestData) -> ToolCallResponse:
        """
        Handle the request to call (invoke) a tool with local context applied.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("CallTool"):
            call_tool_request_data = request.body_json
            call_tool_request = ToolCallRequest.model_validate(call_tool_request_data)

            # Apply local context to the tool context if available
            if self.local_context:
                self._apply_local_context(call_tool_request.context)

            return await self.worker.call_tool(call_tool_request)

    def _apply_local_context(self, tool_context: ToolContext) -> None:
        """
        Apply local context configuration to the tool context.

        This method sets up user IDs and metadata for local development.
        Priority order:
        1. Values already in the context (from the request)
        2. Environment variables (ARCADE_USER_ID, ARCADE_USER_EMAIL, etc.)
        3. worker.toml local_context configuration

        Args:
            tool_context: The tool context to update
        """
        # Set user_id (priority: existing > env > config)
        if not tool_context.user_id:
            tool_context.user_id = os.environ.get("ARCADE_USER_ID") or self.local_context.get(
                "user_id"
            )

        # Initialize metadata if needed
        if not tool_context.metadata:
            tool_context.metadata = []

        # Additional metadata from environment
        if os.environ.get("ARCADE_USER_EMAIL"):
            # Check if not already in metadata
            existing_keys = {item.key.lower() for item in tool_context.metadata}
            if "user_email" not in existing_keys:
                tool_context.metadata.append(
                    ToolMetadataItem(key="user_email", value=os.environ.get("ARCADE_USER_EMAIL"))
                )

        # Apply any additional metadata from local_context
        local_metadata = self.local_context.get("metadata", {})
        existing_keys = {item.key.lower() for item in tool_context.metadata}

        for key, value in local_metadata.items():
            # Don't override existing metadata
            if key.lower() not in existing_keys:
                tool_context.metadata.append(ToolMetadataItem(key=key, value=str(value)))


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
