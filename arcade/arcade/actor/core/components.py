from typing import Any

from arcade.actor.core.common import Actor, ActorComponent, RequestData, Router
from arcade.core.schema import InvokeToolRequest, InvokeToolResponse, ToolDefinition


class CatalogComponent(ActorComponent):
    def __init__(self, actor: Actor) -> None:
        self.actor = actor

    def register(self, router: Router) -> None:
        """
        Register the catalog route with the router.
        """
        router.add_route("tools", self, method="GET")

    async def __call__(self, request: RequestData) -> list[ToolDefinition]:
        """
        Handle the request to get the catalog.
        """
        return self.actor.get_catalog()


class InvokeToolComponent(ActorComponent):
    def __init__(self, actor: Actor) -> None:
        self.actor = actor

    def register(self, router: Router) -> None:
        """
        Register the invoke tool route with the router.
        """
        router.add_route("tools/invoke", self, method="POST")

    async def __call__(self, request: RequestData) -> InvokeToolResponse:
        """
        Handle the request to invoke a tool.
        """
        invoke_tool_request_data = request.body_json
        invoke_tool_request = InvokeToolRequest.model_validate(invoke_tool_request_data)
        return await self.actor.invoke_tool(invoke_tool_request)


class HealthCheckComponent(ActorComponent):
    def __init__(self, actor: Actor) -> None:
        self.actor = actor

    def register(self, router: Router) -> None:
        """
        Register the health check route with the router.
        """
        router.add_route("health", self, method="GET")

    async def __call__(self, request: RequestData) -> dict[str, Any]:
        """
        Handle the request for a health check.
        """
        return self.actor.health_check()
