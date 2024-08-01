import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable

from arcade.core.catalog import ToolCatalog, Toolkit
from arcade.core.executor import ToolExecutor
from arcade.core.schema import (
    InvokeToolError,
    InvokeToolOutput,
    InvokeToolRequest,
    InvokeToolResponse,
    ToolContext,
    ToolDefinition,
)


class ActorComponent(ABC):
    @abstractmethod
    def register(self, router: Any) -> None:
        """
        Register the component with the given router.
        """
        pass

    @abstractmethod
    async def __call__(self, request: Any) -> Any:
        """
        Handle the request.
        """
        pass


class BaseActor:
    base_path = "/actor"  # By default, prefix all our routes with /actor

    def __init__(self) -> None:
        """
        Initialize the BaseActor with an empty ToolCatalog.
        """
        self.catalog = ToolCatalog()

    def get_catalog(self) -> list[ToolDefinition]:
        """
        Get the catalog as a list of ToolDefinitions.
        """
        return [tool.definition for tool in self.catalog]

    def register_tool(self, tool: Callable) -> None:
        """
        Register a tool to the catalog.
        """
        self.catalog.add_tool(tool)

    def register_toolkit(self, toolkit: Toolkit) -> None:
        """
        Register a toolkit to the catalog.
        """
        self.catalog.add_toolkit(toolkit)

    async def invoke_tool(self, tool_request: InvokeToolRequest) -> InvokeToolResponse:
        """
        Invoke a tool using the ToolExecutor.
        """
        tool_name = tool_request.tool.name
        tool = self.catalog.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in catalog.")

        materialized_tool = self.catalog[tool_name]

        start_time = time.time()

        response = await ToolExecutor.run(
            func=materialized_tool.tool,
            definition=materialized_tool.definition,
            input_model=materialized_tool.input_model,
            output_model=materialized_tool.output_model,
            context=tool_request.context or ToolContext(),
            **tool_request.inputs or {},
        )
        if response.code == 200:
            # TODO remove ignore
            output = InvokeToolOutput(value=response.data.result)  # type: ignore[union-attr]
        else:
            output = InvokeToolOutput(error=InvokeToolError(message=response.msg))

        end_time = time.time()  # End time in seconds
        duration_ms = (end_time - start_time) * 1000  # Convert to milliseconds

        return InvokeToolResponse(
            invocation_id=tool_request.invocation_id,
            duration=duration_ms,
            finished_at=datetime.now().isoformat(),
            success=response.code == 200,
            output=output,
        )

    def health_check(self) -> dict[str, Any]:
        """
        Provide a health check that serves as a heartbeat of actor health.
        """
        return {"status": "ok", "tool_count": len(self.catalog.tools.keys())}

    def register_routes(self, router: Any) -> None:
        """
        Register the necessary routes to the application.
        """
        catalog_component = CatalogComponent(self)
        invoke_tool_component = InvokeToolComponent(self)
        health_check_component = HealthCheckComponent(self)

        catalog_component.register(router)
        invoke_tool_component.register(router)
        health_check_component.register(router)


class CatalogComponent(ActorComponent):
    def __init__(self, actor: BaseActor) -> None:
        self.actor = actor

    def register(self, router: Any) -> None:
        """
        Register the catalog route with the router.
        """
        router.add_route(f"{self.actor.base_path}/tools", self, methods=["GET"])

    async def __call__(self, request: Any) -> list[ToolDefinition]:
        """
        Handle the request to get the catalog.
        """
        return self.actor.get_catalog()


class InvokeToolComponent(ActorComponent):
    def __init__(self, actor: BaseActor) -> None:
        self.actor = actor

    def register(self, router: Any) -> None:
        """
        Register the invoke tool route with the router.
        """
        router.add_route(f"{self.actor.base_path}/tools/invoke", self, methods=["POST"])

    async def __call__(self, request: Any) -> InvokeToolResponse:
        """
        Handle the request to invoke a tool.
        """
        invoke_tool_request_data = await request.json()
        invoke_tool_request = InvokeToolRequest.model_validate(invoke_tool_request_data)
        return await self.actor.invoke_tool(invoke_tool_request)


class HealthCheckComponent(ActorComponent):
    def __init__(self, actor: BaseActor) -> None:
        self.actor = actor

    def register(self, router: Any) -> None:
        """
        Register the health check route with the router.
        """
        router.add_route(f"{self.actor.base_path}/health", self, methods=["GET"])

    async def __call__(self, request: Any) -> dict[str, Any]:
        """
        Handle the request for a health check.
        """
        return self.actor.health_check()
