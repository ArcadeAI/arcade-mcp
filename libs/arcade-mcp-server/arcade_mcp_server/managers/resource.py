"""
Resource Manager

Async-safe resources with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from arcade_mcp_server.exceptions import NotFoundError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import (
    BlobResourceContents,
    Resource,
    ResourceContents,
    ResourceTemplate,
    TextResourceContents,
)

logger = logging.getLogger("arcade.mcp.managers.resource")


class ResourceManager(ComponentManager[str, Resource]):
    """
    Manages resources for the MCP server.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__("resource")
        self._templates: dict[str, ResourceTemplate] = {}
        self._resource_handlers: dict[str, Callable[[str], Any]] = {}

    async def list_resources(self) -> list[Resource]:
        return await self.registry.list()

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        return [self._templates[k] for k in sorted(self._templates.keys())]

    async def read_resource(self, uri: str) -> list[ResourceContents]:
        handler = self._resource_handlers.get(uri)
        if handler:
            result = handler(uri)
            if hasattr(result, "__await__"):
                result = await result
            if isinstance(result, str):
                return [TextResourceContents(uri=uri, text=result)]
            elif isinstance(result, dict):
                if "text" in result:
                    return [TextResourceContents(uri=uri, text=result["text"])]
                if "blob" in result:
                    return [BlobResourceContents(uri=uri, blob=result["blob"])]
                return [ResourceContents(uri=uri)]
            elif isinstance(result, list):
                return result
            else:
                return [TextResourceContents(uri=uri, text=str(result))]

        try:
            _ = await self.registry.get(uri)
        except KeyError as _e:
            raise NotFoundError(
                f"✗ Resource not found: '{uri}'\n\n"
                f"  The requested resource does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available resources with resources/list\n"
                f"  2. Check for typos in the resource URI\n"
                f"  3. Verify the resource was registered with the server"
            )

        return [TextResourceContents(uri=uri, text="")]  # static placeholder

    async def add_resource(
        self, resource: Resource, handler: Callable[[str], Any] | None = None
    ) -> None:
        await self.registry.upsert(resource.uri, resource)
        if handler:
            self._resource_handlers[resource.uri] = handler

    async def remove_resource(self, uri: str) -> Resource:
        try:
            removed = await self.registry.remove(uri)
        except KeyError as _e:
            raise NotFoundError(
                f"✗ Resource not found: '{uri}'\n\n"
                f"  The requested resource does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available resources with resources/list\n"
                f"  2. Check for typos in the resource URI\n"
                f"  3. Verify the resource was registered with the server"
            )
        self._resource_handlers.pop(uri, None)
        return removed

    async def update_resource(
        self, uri: str, resource: Resource, handler: Callable[[str], Any] | None = None
    ) -> Resource:
        try:
            await self.registry.remove(uri)
        except KeyError:
            raise NotFoundError(
                f"✗ Resource not found: '{uri}'\n\n"
                f"  The requested resource does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available resources with resources/list\n"
                f"  2. Check for typos in the resource URI\n"
                f"  3. Verify the resource was registered with the server"
            )
        await self.registry.upsert(resource.uri, resource)
        if handler:
            self._resource_handlers[resource.uri] = handler
        return resource

    async def add_template(self, template: ResourceTemplate) -> None:
        self._templates[template.uriTemplate] = template

    async def remove_template(self, uri_template: str) -> ResourceTemplate:
        if uri_template not in self._templates:
            raise NotFoundError(
                f"✗ Resource template not found: '{uri_template}'\n\n"
                f"  The requested resource template does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available resource templates with resources/templates/list\n"
                f"  2. Check for typos in the template URI\n"
                f"  3. Verify the template was registered with the server"
            )
        return self._templates.pop(uri_template)
