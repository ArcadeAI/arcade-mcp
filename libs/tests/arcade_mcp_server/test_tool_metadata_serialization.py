"""Tests for tool metadata serialization to MCP format."""

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)
from arcade_mcp_server.managers.tool import ToolManager
from arcade_tdk import tool
from arcade_tdk.auth import OAuth2


class TestToolMetadataSerialization:
    """Test serialization of ToolMetadata to MCP format."""

    @pytest.fixture
    def tool_manager(self) -> ToolManager:
        return ToolManager()

    def _create_materialized_tool(self, tool_func) -> MaterializedTool:
        """Helper to create a MaterializedTool from a decorated function."""
        definition = ToolCatalog.create_tool_definition(
            tool_func, toolkit_name="Test", toolkit_version="1.0.0"
        )
        input_model, output_model = create_func_models(tool_func)
        return MaterializedTool(
            tool=tool_func,
            definition=definition,
            meta=ToolMeta(module="test"),
            input_model=input_model,
            output_model=output_model,
        )

    def test_annotations_computed_from_behavior(self, tool_manager: ToolManager):
        """Annotations should be computed from behavior fields."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                behavior=Behavior(
                    operations=[Operation.CREATE],
                    read_only=False,
                    destructive=False,
                    idempotent=True,
                    open_world=True,
                ),
            ),
        )
        def create_item() -> str:
            """Create an item."""
            return "created"

        materialized = self._create_materialized_tool(create_item)
        dto = tool_manager._to_dto(materialized)

        assert dto.annotations is not None
        assert dto.annotations.title == "CreateItem"
        assert dto.annotations.readOnlyHint is False
        assert dto.annotations.destructiveHint is False
        assert dto.annotations.idempotentHint is True
        assert dto.annotations.openWorldHint is True

    def test_meta_arcade_includes_classification(self, tool_manager: ToolManager):
        """_meta.arcade.metadata should include classification with service_domains."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(
                    service_domains=[ServiceDomain.MESSAGING, ServiceDomain.DOCUMENTS],
                ),
                behavior=Behavior(
                    operations=[Operation.CREATE],
                    open_world=True,
                ),
            ),
        )
        def forward_message() -> str:
            """Forward a message."""
            return "forwarded"

        materialized = self._create_materialized_tool(forward_message)
        dto = tool_manager._to_dto(materialized)

        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "metadata" in dto.meta["arcade"]
        assert "classification" in dto.meta["arcade"]["metadata"]
        assert dto.meta["arcade"]["metadata"]["classification"]["service_domains"] == [
            "messaging",
            "documents",
        ]

    def test_meta_arcade_includes_operations(self, tool_manager: ToolManager):
        """_meta.arcade.metadata.behavior should include operations as lowercase strings."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                behavior=Behavior(operations=[Operation.CREATE, Operation.UPDATE]),
            ),
        )
        def upsert_record() -> str:
            """Upsert a record."""
            return "upserted"

        materialized = self._create_materialized_tool(upsert_record)
        dto = tool_manager._to_dto(materialized)

        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "metadata" in dto.meta["arcade"]
        assert "behavior" in dto.meta["arcade"]["metadata"]
        assert dto.meta["arcade"]["metadata"]["behavior"]["operations"] == ["create", "update"]

    def test_meta_arcade_includes_extras(self, tool_manager: ToolManager):
        """_meta.arcade.metadata should include extras dict unchanged."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                extras={"idp": "entraID", "requires_mfa": True, "max_requests": 100},
            ),
        )
        def secure_action() -> str:
            """Perform secure action."""
            return "done"

        materialized = self._create_materialized_tool(secure_action)
        dto = tool_manager._to_dto(materialized)

        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "metadata" in dto.meta["arcade"]
        assert "extras" in dto.meta["arcade"]["metadata"]
        assert dto.meta["arcade"]["metadata"]["extras"] == {
            "idp": "entraID",
            "requires_mfa": True,
            "max_requests": 100,
        }

    def test_tool_without_metadata_still_works(self, tool_manager: ToolManager):
        """Tools without metadata should still serialize correctly with title."""

        @tool(desc="Test tool")
        def simple_tool() -> str:
            """Simple tool."""
            return "simple"

        materialized = self._create_materialized_tool(simple_tool)
        dto = tool_manager._to_dto(materialized)

        # Should have title in annotations even without behavior
        assert dto.annotations is not None
        assert dto.annotations.title == "SimpleTool"
        # Hint fields should be None
        assert dto.annotations.readOnlyHint is None
        assert dto.annotations.destructiveHint is None
        assert dto.annotations.idempotentHint is None
        assert dto.annotations.openWorldHint is None
        # Should not have arcade meta without metadata
        assert dto.meta is None or "arcade" not in dto.meta

    def test_full_metadata_serialization(self, tool_manager: ToolManager):
        """Test complete metadata serialization with all fields."""

        @tool(
            desc="Send an email using the Gmail API",
            metadata=ToolMetadata(
                classification=Classification(
                    service_domains=[ServiceDomain.EMAIL],
                ),
                behavior=Behavior(
                    operations=[Operation.CREATE],
                    read_only=False,
                    destructive=False,
                    idempotent=False,
                    open_world=True,
                ),
                extras={"idp": "entraID", "requires_mfa": True},
            ),
        )
        def send_email() -> str:
            """Send an email."""
            return "sent"

        materialized = self._create_materialized_tool(send_email)
        dto = tool_manager._to_dto(materialized)

        # Verify annotations
        assert dto.annotations is not None
        assert dto.annotations.title == "SendEmail"
        assert dto.annotations.readOnlyHint is False
        assert dto.annotations.destructiveHint is False
        assert dto.annotations.idempotentHint is False
        assert dto.annotations.openWorldHint is True

        # Verify _meta.arcade structure (mirrors Arcade format)
        assert dto.meta is not None
        assert "arcade" in dto.meta
        arcade = dto.meta["arcade"]

        assert "metadata" in arcade
        metadata = arcade["metadata"]

        assert metadata["classification"]["service_domains"] == ["email"]
        assert metadata["behavior"]["operations"] == ["create"]
        assert metadata["behavior"]["read_only"] is False
        assert metadata["behavior"]["destructive"] is False
        assert metadata["behavior"]["idempotent"] is False
        assert metadata["behavior"]["open_world"] is True
        assert metadata["extras"] == {"idp": "entraID", "requires_mfa": True}

    def test_metadata_with_only_classification(self, tool_manager: ToolManager):
        """Tools with only classification should serialize correctly."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(
                    service_domains=[ServiceDomain.WEB_SCRAPING],
                ),
            ),
        )
        def search_web() -> str:
            """Search the web."""
            return "results"

        materialized = self._create_materialized_tool(search_web)
        dto = tool_manager._to_dto(materialized)

        # Annotations should still have title
        assert dto.annotations is not None
        assert dto.annotations.title == "SearchWeb"
        # Hint fields should be None without behavior
        assert dto.annotations.readOnlyHint is None

        # _meta.arcade.metadata should have classification but not behavior
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "metadata" in dto.meta["arcade"]
        assert "classification" in dto.meta["arcade"]["metadata"]
        assert "behavior" not in dto.meta["arcade"]["metadata"]

    def test_metadata_with_only_extras(self, tool_manager: ToolManager):
        """Tools with only extras should serialize correctly."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                extras={"custom_key": "custom_value"},
            ),
        )
        def custom_tool() -> str:
            """Custom tool."""
            return "custom"

        materialized = self._create_materialized_tool(custom_tool)
        dto = tool_manager._to_dto(materialized)

        # _meta.arcade.metadata should have only extras
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "metadata" in dto.meta["arcade"]
        assert "classification" not in dto.meta["arcade"]["metadata"]
        assert "behavior" not in dto.meta["arcade"]["metadata"]
        assert dto.meta["arcade"]["metadata"]["extras"] == {"custom_key": "custom_value"}

    def test_meta_arcade_includes_requirements(self, tool_manager: ToolManager):
        """_meta.arcade should include requirements when tool has auth."""

        @tool(
            desc="Tool requiring OAuth",
            requires_auth=OAuth2(
                id="google",
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            ),
        )
        def authenticated_tool() -> str:
            """Tool requiring authentication."""
            return "authenticated"

        materialized = self._create_materialized_tool(authenticated_tool)
        dto = tool_manager._to_dto(materialized)

        # _meta.arcade should have requirements
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "requirements" in dto.meta["arcade"]
        assert "authorization" in dto.meta["arcade"]["requirements"]
        assert dto.meta["arcade"]["requirements"]["authorization"]["id"] == "google"

    def test_meta_arcade_includes_secrets_requirements(self, tool_manager: ToolManager):
        """_meta.arcade should include requirements when tool has secrets."""

        @tool(
            desc="Tool requiring secrets",
            requires_secrets=["API_KEY", "API_SECRET"],
        )
        def secret_tool() -> str:
            """Tool requiring secrets."""
            return "secret"

        materialized = self._create_materialized_tool(secret_tool)
        dto = tool_manager._to_dto(materialized)

        # _meta.arcade should have requirements
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "requirements" in dto.meta["arcade"]
        assert "secrets" in dto.meta["arcade"]["requirements"]
        secrets_req = dto.meta["arcade"]["requirements"]["secrets"]
        assert "API_KEY" in [s["key"] for s in secrets_req]
        assert "API_SECRET" in [s["key"] for s in secrets_req]

    def test_full_metadata_with_requirements(self, tool_manager: ToolManager):
        """Test complete serialization with both metadata and requirements."""

        @tool(
            desc="Full featured tool",
            requires_auth=OAuth2(
                id="google",
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            ),
            metadata=ToolMetadata(
                classification=Classification(
                    service_domains=[ServiceDomain.EMAIL],
                ),
                behavior=Behavior(
                    operations=[Operation.CREATE],
                    read_only=False,
                    destructive=False,
                    open_world=True,
                ),
                extras={"idp": "google"},
            ),
        )
        def full_tool() -> str:
            """Full featured tool."""
            return "full"

        materialized = self._create_materialized_tool(full_tool)
        dto = tool_manager._to_dto(materialized)

        # Verify structure: requirements at top level, metadata container for rest
        assert dto.meta is not None
        assert "arcade" in dto.meta
        arcade = dto.meta["arcade"]

        # Requirements at top level of arcade
        assert "requirements" in arcade
        assert arcade["requirements"]["authorization"]["id"] == "google"

        # metadata container holds classification, behavior, extras
        assert "metadata" in arcade
        metadata = arcade["metadata"]

        assert "classification" in metadata
        assert "behavior" in metadata
        assert "extras" in metadata

        # Verify specific values
        assert metadata["classification"]["service_domains"] == ["email"]
        assert metadata["behavior"]["operations"] == ["create"]
        assert metadata["behavior"]["read_only"] is False
        assert metadata["behavior"]["destructive"] is False
        assert metadata["behavior"]["open_world"] is True
        assert metadata["extras"] == {"idp": "google"}
