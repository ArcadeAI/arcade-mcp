"""
Tool Manager

Async-safe tool management with pre-converted MCPTool DTOs and executable materials.
"""

from __future__ import annotations

from typing import Any, TypedDict

from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.schema import ToolDefinition

from arcade_mcp_server.convert import build_input_schema_from_definition
from arcade_mcp_server.exceptions import NotFoundError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import MCPTool, ToolAnnotations


class ManagedTool(TypedDict):
    dto: MCPTool
    materialized: MaterializedTool


Key = str  # fully qualified tool name


class ToolManager(ComponentManager[Key, ManagedTool]):
    """Tool manager storing both DTO and materialized artifacts."""

    def __init__(self) -> None:
        super().__init__("tool")
        self._sanitized_to_key: dict[str, str] = {}

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return name.replace(".", "_")

    @staticmethod
    def _build_arcade_meta(definition: ToolDefinition) -> dict[str, Any] | None:
        """Build the _meta.arcade structure from tool definition.

        Structure mirrors Arcade format:
        - requirements: Authorization, secrets, and metadata requirements (top-level)
        - metadata: Container for classification, behavior, and extras
          - classification: Domains and system types for tool discovery
          - behavior: Verbs and all behavior flags (read_only, destructive, etc.)
          - extras: Arbitrary key/values for custom logic
        """
        arcade_meta: dict[str, Any] = {}

        # Add requirements at top level (not inside metadata)
        requirements = definition.requirements
        if requirements.authorization or requirements.secrets or requirements.metadata:
            arcade_meta["requirements"] = requirements.model_dump(exclude_none=True)

        # Build metadata container (mirrors Arcade format structure)
        tool_metadata = definition.metadata
        if tool_metadata:
            metadata_container: dict[str, Any] = {}

            # Add classification
            if tool_metadata.classification:
                classification = tool_metadata.classification
                classification_meta: dict[str, Any] = {}
                if classification.domains:
                    classification_meta["domains"] = [d.value for d in classification.domains]
                if classification.system_types:
                    classification_meta["system_types"] = [
                        st.value for st in classification.system_types
                    ]
                if classification_meta:
                    metadata_container["classification"] = classification_meta

            # Add behavior with all fields (not just verbs)
            if tool_metadata.behavior:
                behavior = tool_metadata.behavior
                behavior_meta: dict[str, Any] = {}
                if behavior.verbs:
                    behavior_meta["verbs"] = [v.value for v in behavior.verbs]
                if behavior.read_only is not None:
                    behavior_meta["read_only"] = behavior.read_only
                if behavior.destructive is not None:
                    behavior_meta["destructive"] = behavior.destructive
                if behavior.idempotent is not None:
                    behavior_meta["idempotent"] = behavior.idempotent
                if behavior.open_world is not None:
                    behavior_meta["open_world"] = behavior.open_world
                if behavior_meta:
                    metadata_container["behavior"] = behavior_meta

            # Add extras
            if tool_metadata.extras:
                metadata_container["extras"] = tool_metadata.extras

            # Only add metadata container if it has content
            if metadata_container:
                arcade_meta["metadata"] = metadata_container

        return arcade_meta if arcade_meta else None

    def _to_dto(self, materialized_tool: MaterializedTool) -> MCPTool:
        """Convert a MaterializedTool to an MCPTool DTO."""
        definition = materialized_tool.definition

        # Get title from __tool_name__ which preserves:
        # - Explicit @tool(name="...") as-is
        # - Function name converted to PascalCase
        title = getattr(materialized_tool.tool, "__tool_name__", definition.name)
        tool_metadata = definition.metadata
        if tool_metadata and tool_metadata.behavior:
            behavior = tool_metadata.behavior
            annotations = ToolAnnotations(
                title=title,
                readOnlyHint=behavior.read_only,
                destructiveHint=behavior.destructive,
                idempotentHint=behavior.idempotent,
                openWorldHint=behavior.open_world,
            )
        else:
            # Even without behavior metadata, we can still set the title annotation
            annotations = ToolAnnotations(title=title)

        arcade_meta = self._build_arcade_meta(definition)
        meta = {"arcade": arcade_meta} if arcade_meta else None

        return MCPTool(
            name=self._sanitize_name(definition.fully_qualified_name),
            title=title,
            description=definition.description,
            inputSchema=build_input_schema_from_definition(definition),
            annotations=annotations,
            meta=meta,
        )

    async def load_from_catalog(self, catalog: ToolCatalog) -> None:
        pairs: list[tuple[Key, ManagedTool]] = []
        for t in catalog:
            fq = t.definition.fully_qualified_name
            pairs.append((fq, {"dto": self._to_dto(t), "materialized": t}))
            self._sanitized_to_key[self._sanitize_name(fq)] = fq
        await self.registry.bulk_load(pairs)

    async def list_tools(self) -> list[MCPTool]:
        records = await self.registry.list()
        return [r["dto"] for r in records]

    async def get_tool(self, name: str) -> MaterializedTool:
        # Try exact key first (dotted FQN)
        try:
            rec = await self.registry.get(name)
            return rec["materialized"]
        except KeyError:
            # Fallback: resolve sanitized name
            key = self._sanitized_to_key.get(name)
            if key is None:
                raise NotFoundError(f"Tool {name} not found")
            rec = await self.registry.get(key)
            return rec["materialized"]

    async def add_tool(self, tool: MaterializedTool) -> None:
        key = tool.definition.fully_qualified_name
        await self.registry.upsert(key, {"dto": self._to_dto(tool), "materialized": tool})
        self._sanitized_to_key[self._sanitize_name(key)] = key

    async def update_tool(self, tool: MaterializedTool) -> None:
        key = tool.definition.fully_qualified_name
        await self.registry.upsert(key, {"dto": self._to_dto(tool), "materialized": tool})
        self._sanitized_to_key[self._sanitize_name(key)] = key

    async def remove_tool(self, name: str) -> MaterializedTool:
        # Accept either exact or sanitized name
        key = name
        if key not in (await self.registry.keys()):
            key = self._sanitized_to_key.get(name, name)
        try:
            rec = await self.registry.remove(key)
        except KeyError as _e:
            raise NotFoundError(f"Tool {name} not found")
        # Clean mapping if present
        sanitized = self._sanitize_name(key)
        if sanitized in self._sanitized_to_key:
            del self._sanitized_to_key[sanitized]
        return rec["materialized"]
