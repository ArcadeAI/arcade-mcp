"""Tests for tool metadata serialization to MCP format."""

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.metadata import (
    Behavior,
    Classification,
    Domain,
    SystemType,
    ToolMetadata,
    Verb,
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
                    verbs=[Verb.CREATE],
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
        """_meta.arcade should include classification with domains and systemTypes."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(
                    domains=[Domain.MESSAGING, Domain.WORKFLOW],
                    system_types=[SystemType.SAAS_API],
                ),
                behavior=Behavior(
                    verbs=[Verb.EXECUTE],
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
        assert "classification" in dto.meta["arcade"]
        assert dto.meta["arcade"]["classification"]["domains"] == ["messaging", "workflow"]
        assert dto.meta["arcade"]["classification"]["systemTypes"] == ["saas_api"]

    def test_meta_arcade_includes_verbs(self, tool_manager: ToolManager):
        """_meta.arcade.behavior should include verbs as lowercase strings."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                behavior=Behavior(verbs=[Verb.CREATE, Verb.UPDATE]),
            ),
        )
        def upsert_record() -> str:
            """Upsert a record."""
            return "upserted"

        materialized = self._create_materialized_tool(upsert_record)
        dto = tool_manager._to_dto(materialized)

        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "behavior" in dto.meta["arcade"]
        assert dto.meta["arcade"]["behavior"]["verbs"] == ["create", "update"]

    def test_meta_arcade_includes_extras(self, tool_manager: ToolManager):
        """_meta.arcade should include extras dict unchanged."""

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
        assert "extras" in dto.meta["arcade"]
        assert dto.meta["arcade"]["extras"] == {
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
                    domains=[Domain.MESSAGING],
                    system_types=[SystemType.SAAS_API],
                ),
                behavior=Behavior(
                    verbs=[Verb.EXECUTE],
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

        # Verify _meta.arcade structure
        assert dto.meta is not None
        assert "arcade" in dto.meta
        arcade = dto.meta["arcade"]

        assert arcade["classification"]["domains"] == ["messaging"]
        assert arcade["classification"]["systemTypes"] == ["saas_api"]
        assert arcade["behavior"]["verbs"] == ["execute"]
        assert arcade["extras"] == {"idp": "entraID", "requires_mfa": True}

    def test_metadata_with_only_classification(self, tool_manager: ToolManager):
        """Tools with only classification should serialize correctly."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(
                    domains=[Domain.SEARCH],
                    system_types=[SystemType.WEB],
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

        # _meta.arcade should have classification but not behavior
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "classification" in dto.meta["arcade"]
        assert "behavior" not in dto.meta["arcade"]

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

        # _meta.arcade should have only extras
        assert dto.meta is not None
        assert "arcade" in dto.meta
        assert "classification" not in dto.meta["arcade"]
        assert "behavior" not in dto.meta["arcade"]
        assert dto.meta["arcade"]["extras"] == {"custom_key": "custom_value"}

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
                    domains=[Domain.MESSAGING],
                    system_types=[SystemType.SAAS_API],
                ),
                behavior=Behavior(
                    verbs=[Verb.EXECUTE],
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

        # Verify all fields are present in _meta.arcade
        assert dto.meta is not None
        assert "arcade" in dto.meta
        arcade = dto.meta["arcade"]

        assert "requirements" in arcade
        assert "classification" in arcade
        assert "behavior" in arcade
        assert "extras" in arcade

        # Verify specific values
        assert arcade["requirements"]["authorization"]["id"] == "google"
        assert arcade["classification"]["domains"] == ["messaging"]
        assert arcade["behavior"]["verbs"] == ["execute"]
        assert arcade["extras"] == {"idp": "google"}
