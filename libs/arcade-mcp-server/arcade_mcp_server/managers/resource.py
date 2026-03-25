"""
Resource Manager

Async-safe resources with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import base64
import contextlib
import logging
import re
from pathlib import Path
from typing import Any, Callable, Literal

from arcade_mcp_server.exceptions import NotFoundError, ResourceError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import (
    BlobResourceContents,
    Resource,
    ResourceContents,
    ResourceTemplate,
    TextResourceContents,
)

logger = logging.getLogger("arcade.mcp.managers.resource")

DuplicatePolicy = Literal["warn", "error", "replace", "ignore"]


def _is_template_uri(uri: str) -> bool:
    """Return True if *uri* contains RFC 6570-style template variables."""
    return "{" in uri


def _template_to_regex(template: str) -> re.Pattern[str]:
    """Convert a URI template to a compiled regex with named groups.

    ``{param}``  -> ``(?P<param>[^/]+)``
    ``{param*}`` -> ``(?P<param>.+)``  (wildcard / greedy)
    """
    pattern = re.escape(template)
    # Wildcard parameters first (e.g. {path*})
    pattern = re.sub(
        r"\\{(\w+)\\\*\\}",
        lambda m: f"(?P<{m.group(1)}>.+)",
        pattern,
    )
    # Simple parameters (e.g. {city})
    pattern = re.sub(
        r"\\{(\w+)\\}",
        lambda m: f"(?P<{m.group(1)}>[^/]+)",
        pattern,
    )
    return re.compile(f"^{pattern}$")


class ResourceManager(ComponentManager[str, Resource]):
    """
    Manages resources for the MCP server.
    """

    def __init__(
        self,
        duplicate_policy: DuplicatePolicy = "warn",
    ) -> None:
        super().__init__("resource")
        self._templates: dict[str, ResourceTemplate] = {}
        self._resource_handlers: dict[str, Callable[[str], Any]] = {}
        self._template_handlers: dict[str, Callable[..., Any]] = {}
        self._template_patterns: dict[str, re.Pattern[str]] = {}
        self.duplicate_policy: DuplicatePolicy = duplicate_policy

    async def list_resources(self) -> list[Resource]:
        return await self.registry.list()

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        return [self._templates[k] for k in sorted(self._templates.keys())]

    async def read_resource(self, uri: str) -> list[ResourceContents]:
        handler = self._resource_handlers.get(uri)
        if handler:
            # Look up the registered resource's mimeType so we can propagate it
            mime_type: str | None = None
            try:
                registered: Resource = await self.registry.get(uri)
                mime_type = registered.mimeType
            except KeyError:
                pass

            result = handler(uri)
            if hasattr(result, "__await__"):
                result = await result
            return self._coerce_result(uri, mime_type, result)

        # Try template matching before giving up
        for tmpl_str, pattern in self._template_patterns.items():
            match = pattern.match(uri)
            if match:
                params = match.groupdict()
                tmpl_handler = self._template_handlers[tmpl_str]
                mime_type = self._templates[tmpl_str].mimeType
                result = tmpl_handler(uri, **params)
                if hasattr(result, "__await__"):
                    result = await result
                return self._coerce_result(uri, mime_type, result)

        try:
            _ = await self.registry.get(uri)
        except KeyError as _e:
            raise NotFoundError(f"Resource '{uri}' not found")

        return [TextResourceContents(uri=uri, text="")]  # static placeholder

    @staticmethod
    def _coerce_result(uri: str, mime_type: str | None, result: Any) -> list[ResourceContents]:
        """Convert a handler return value into a list of ResourceContents."""
        if isinstance(result, bytes):
            blob = base64.b64encode(result).decode("ascii")
            return [BlobResourceContents(uri=uri, mimeType=mime_type, blob=blob)]
        elif isinstance(result, str):
            return [TextResourceContents(uri=uri, mimeType=mime_type, text=result)]
        elif isinstance(result, dict):
            if "text" in result:
                return [TextResourceContents(uri=uri, mimeType=mime_type, text=result["text"])]
            if "blob" in result:
                return [BlobResourceContents(uri=uri, mimeType=mime_type, blob=result["blob"])]
            return [ResourceContents(uri=uri, mimeType=mime_type)]
        elif isinstance(result, list):
            return result
        else:
            return [TextResourceContents(uri=uri, mimeType=mime_type, text=str(result))]

    async def add_resource(
        self, resource: Resource, handler: Callable[[str], Any] | None = None
    ) -> None:
        # Duplicate-detection
        existing: Resource | None = None
        with contextlib.suppress(KeyError):
            existing = await self.registry.get(resource.uri)

        if existing is not None:
            if self.duplicate_policy == "error":
                raise ResourceError(f"Resource '{resource.uri}' already registered")
            elif self.duplicate_policy == "ignore":
                return
            elif self.duplicate_policy == "warn":
                logger.warning(f"Replacing duplicate resource '{resource.uri}'")
            # "replace" and "warn" both fall through to upsert

        await self.registry.upsert(resource.uri, resource)
        if handler:
            self._resource_handlers[resource.uri] = handler

    async def remove_resource(self, uri: str) -> Resource:
        try:
            removed = await self.registry.remove(uri)
        except KeyError as _e:
            raise NotFoundError(f"Resource '{uri}' not found")
        self._resource_handlers.pop(uri, None)
        return removed

    async def update_resource(
        self, uri: str, resource: Resource, handler: Callable[[str], Any] | None = None
    ) -> Resource:
        try:
            await self.registry.remove(uri)
        except KeyError:
            raise NotFoundError(f"Resource '{uri}' not found")
        await self.registry.upsert(resource.uri, resource)
        if handler:
            self._resource_handlers[resource.uri] = handler
        return resource

    async def add_template(self, template: ResourceTemplate) -> None:
        self._templates[template.uriTemplate] = template

    async def add_template_with_handler(
        self, template: ResourceTemplate, handler: Callable[..., Any]
    ) -> None:
        """Store a template together with its handler and compiled regex."""
        self._templates[template.uriTemplate] = template
        self._template_handlers[template.uriTemplate] = handler
        self._template_patterns[template.uriTemplate] = _template_to_regex(template.uriTemplate)

    async def remove_template(self, uri_template: str) -> ResourceTemplate:
        if uri_template not in self._templates:
            raise NotFoundError(f"Resource template '{uri_template}' not found")
        self._template_handlers.pop(uri_template, None)
        self._template_patterns.pop(uri_template, None)
        return self._templates.pop(uri_template)

    async def add_text_resource(
        self,
        uri: str,
        text: str,
        *,
        name: str | None = None,
        description: str | None = None,
        mime_type: str = "text/plain",
    ) -> None:
        """Convenience: register a static text resource."""
        resource = Resource(uri=uri, name=name or uri, description=description, mimeType=mime_type)
        await self.add_resource(resource, handler=lambda _uri: text)

    async def add_file_resource(
        self,
        uri: str,
        path: str | Path,
        *,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> None:
        """Convenience: register a file-backed resource."""
        resource = Resource(uri=uri, name=name or uri, description=description, mimeType=mime_type)
        file_path = Path(path)

        def _read_file(_uri: str) -> str | bytes:
            if not file_path.exists():
                raise NotFoundError(f"File not found: {file_path}")
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return file_path.read_bytes()

        await self.add_resource(resource, handler=_read_file)
