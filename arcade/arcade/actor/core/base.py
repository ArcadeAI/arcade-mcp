import time
from datetime import datetime
from typing import Any, Callable, ClassVar

from arcade.actor.core.common import Actor, Router
from arcade.actor.core.components import (
    ActorComponent,
    CallToolComponent,
    CatalogComponent,
    HealthCheckComponent,
)
from arcade.core.catalog import ToolCatalog, Toolkit
from arcade.core.executor import ToolExecutor
from arcade.core.schema import (
    ToolCallRequest,
    ToolCallResponse,
    ToolDefinition,
)


class BaseActor(Actor):
    """
    A base actor class that provides a default implementation for registering tools and invoking them.
    Actor implementations for specific web frameworks will inherit from this class.
    """

    base_path = "/actor"  # By default, prefix all our routes with /actor

    default_components: ClassVar[tuple[type[ActorComponent], ...]] = (
        CatalogComponent,
        CallToolComponent,
        HealthCheckComponent,
    )

    def __init__(self, secret: str, disable_auth: bool = False) -> None:
        """
        Initialize the BaseActor with an empty ToolCatalog.
        """
        self.catalog = ToolCatalog()
        self.disable_auth = disable_auth
        self.secret = secret

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

    async def call_tool(self, tool_request: ToolCallRequest) -> ToolCallResponse:
        """
        Call (invoke) a tool using the ToolExecutor.
        """
        tool_name = tool_request.tool.name
        tool = self.catalog.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in catalog.")

        materialized_tool = self.catalog[tool_name]

        start_time = time.time()

        output = await ToolExecutor.run(
            func=materialized_tool.tool,
            definition=materialized_tool.definition,
            input_model=materialized_tool.input_model,
            output_model=materialized_tool.output_model,
            context=tool_request.context,
            **tool_request.inputs or {},
        )

        end_time = time.time()  # End time in seconds
        duration_ms = (end_time - start_time) * 1000  # Convert to milliseconds

        return ToolCallResponse(
            invocation_id=tool_request.invocation_id or "",
            duration=duration_ms,
            finished_at=datetime.now().isoformat(),
            success=not output.error,
            output=output,
        )

    def health_check(self) -> dict[str, Any]:
        """
        Provide a health check that serves as a heartbeat of actor health.
        """
        return {"status": "ok", "tool_count": len(self.catalog.tools.keys())}

    def register_routes(self, router: Router) -> None:
        """
        Register the necessary routes to the application.
        """
        for component_cls in self.default_components:
            component_cls(self).register(router)
