import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError
from arcade_core.metadata import (
    _CLOSED_WORLD_SYSTEM_TYPES,
    _MUTATING_VERBS,
    _READ_ONLY_VERBS,
    Behavior,
    Classification,
    Domain,
    SystemType,
    ToolMetadata,
    Verb,
)
from arcade_tdk import tool


class TestEnumCoverage:
    """
    Tests to ensure all enum values are accounted for in validation helper sets.

    These tests will fail if new enum values are added without updating the
    corresponding helper sets, ensuring future maintainers don't forget to
    categorize new values.
    """

    def test_all_verbs_are_categorized(self):
        """Every Verb must be in either _READ_ONLY_VERBS or _MUTATING_VERBS."""
        all_verbs = set(Verb)
        categorized_verbs = _READ_ONLY_VERBS | _MUTATING_VERBS

        # Check that every verb is categorized
        uncategorized = all_verbs - categorized_verbs
        assert not uncategorized, (
            f"The following Verb values are not categorized in _READ_ONLY_VERBS or "
            f"_MUTATING_VERBS: {uncategorized}. Please add them to the appropriate set "
            f"in arcade_core/metadata.py"
        )

        # Check that there are no extra verbs in the sets that don't exist in the enum
        extra = categorized_verbs - all_verbs
        assert not extra, (
            f"The following values are in _READ_ONLY_VERBS or _MUTATING_VERBS but "
            f"don't exist in the Verb enum: {extra}"
        )

    def test_verb_categories_are_disjoint(self):
        """_READ_ONLY_VERBS and _MUTATING_VERBS should not overlap."""
        overlap = _READ_ONLY_VERBS & _MUTATING_VERBS
        assert not overlap, (
            f"The following Verb values appear in both _READ_ONLY_VERBS and "
            f"_MUTATING_VERBS: {overlap}. A verb should be in exactly one category."
        )

    def test_closed_world_system_types_are_valid(self):
        """All values in _CLOSED_WORLD_SYSTEM_TYPES must be valid SystemType values."""
        all_system_types = set(SystemType)
        invalid = _CLOSED_WORLD_SYSTEM_TYPES - all_system_types
        assert not invalid, (
            f"The following values are in _CLOSED_WORLD_SYSTEM_TYPES but don't exist "
            f"in the SystemType enum: {invalid}"
        )

    def test_in_process_is_closed_world(self):
        """IN_PROCESS should be the only closed-world system type."""
        assert SystemType.IN_PROCESS in _CLOSED_WORLD_SYSTEM_TYPES, (
            "SystemType.IN_PROCESS must be in _CLOSED_WORLD_SYSTEM_TYPES"
        )
        # Note: We intentionally don't require other system types to be excluded,
        # as new closed-world system types could theoretically be added in the future.


class TestToolMetadataValidation:
    """Test strict mode validation rules for ToolMetadata."""

    def test_valid_metadata_passes(self):
        """Valid metadata with consistent values should not raise."""
        metadata = ToolMetadata(
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
        )
        assert metadata is not None

    def test_mutating_verb_with_read_only_raises(self):
        """Mutating verbs with read_only=True should raise when validated."""
        metadata = ToolMetadata(
            behavior=Behavior(verbs=[Verb.CREATE], read_only=True),
        )
        with pytest.raises(
            ToolDefinitionError, match="mutating verb.*but is marked read_only=True"
        ):
            metadata.validate_for_tool()

    def test_delete_without_destructive_raises(self):
        """DELETE verb without destructive=True should raise when validated."""
        metadata = ToolMetadata(
            behavior=Behavior(verbs=[Verb.DELETE], destructive=False),
        )
        with pytest.raises(
            ToolDefinitionError, match="'DELETE' verb.*but is not marked destructive=True"
        ):
            metadata.validate_for_tool()

    def test_in_process_with_open_world_raises(self):
        """IN_PROCESS only system type with open_world=True should raise when validated."""
        metadata = ToolMetadata(
            classification=Classification(system_types=[SystemType.IN_PROCESS]),
            behavior=Behavior(open_world=True),
        )
        with pytest.raises(
            ToolDefinitionError, match="closed-world system type.*but is marked open_world=True"
        ):
            metadata.validate_for_tool()

    def test_remote_system_without_open_world_raises(self):
        """Remote system types (SAAS_API, etc.) without open_world=True should raise when validated."""
        metadata = ToolMetadata(
            classification=Classification(system_types=[SystemType.SAAS_API]),
            behavior=Behavior(open_world=False),
        )
        with pytest.raises(
            ToolDefinitionError, match="remote system type.*but is marked open_world=False"
        ):
            metadata.validate_for_tool()

    def test_strict_false_bypasses_validation(self):
        """Setting strict=False should bypass all validation rules."""
        # This would normally raise due to contradiction
        metadata = ToolMetadata(
            behavior=Behavior(verbs=[Verb.CREATE], read_only=True),
            strict=False,
        )
        # No error should be raised when validate_for_tool is called
        metadata.validate_for_tool()  # Should not raise
        assert metadata is not None

    def test_error_message_includes_tool_name(self):
        """Error messages should include the tool name for debugging."""
        metadata = ToolMetadata(
            behavior=Behavior(verbs=[Verb.CREATE], read_only=True),
        )
        with pytest.raises(ToolDefinitionError, match="Tool has the mutating verb"):
            metadata.validate_for_tool()

    def test_read_only_verb_with_read_only_true_passes(self):
        """READ verb with read_only=True should pass validation."""
        metadata = ToolMetadata(
            behavior=Behavior(verbs=[Verb.READ], read_only=True),
        )
        assert metadata is not None
        assert metadata.behavior.read_only is True

    def test_multiple_domains_allowed(self):
        """Tools can have multiple domains."""
        metadata = ToolMetadata(
            classification=Classification(
                domains=[Domain.CODE, Domain.SEARCH],
                system_types=[SystemType.SAAS_API],
            ),
            behavior=Behavior(verbs=[Verb.READ], read_only=True, open_world=True),
        )
        assert len(metadata.classification.domains) == 2

    def test_multiple_system_types_allowed(self):
        """Tools can have multiple system types."""
        metadata = ToolMetadata(
            classification=Classification(
                domains=[Domain.CODE],
                system_types=[SystemType.SAAS_API, SystemType.FILE_SYSTEM],
            ),
            behavior=Behavior(verbs=[Verb.READ], read_only=True, open_world=True),
        )
        assert len(metadata.classification.system_types) == 2

    def test_extras_accepts_arbitrary_dict(self):
        """Extras field accepts arbitrary key/value pairs."""
        metadata = ToolMetadata(
            extras={"idp": "entraID", "requires_mfa": True, "max_requests": 100},
        )
        assert metadata.extras["idp"] == "entraID"
        assert metadata.extras["requires_mfa"] is True
        assert metadata.extras["max_requests"] == 100


class TestToolDecoratorWithMetadata:
    """Test @tool decorator with metadata parameter."""

    def test_decorator_accepts_metadata(self):
        """Decorator should store metadata as __tool_metadata__ attribute."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(domains=[Domain.MESSAGING]),
                behavior=Behavior(verbs=[Verb.EXECUTE]),
            ),
        )
        def my_tool() -> str:
            return "test"

        assert hasattr(my_tool, "__tool_metadata__")
        assert my_tool.__tool_metadata__.classification.domains == [Domain.MESSAGING]

    def test_decorator_without_metadata_is_backward_compatible(self):
        """Decorator should work without metadata (existing tools unchanged)."""

        @tool(desc="Test tool")
        def my_tool() -> str:
            return "test"

        assert getattr(my_tool, "__tool_metadata__", None) is None


class TestToolDefinitionWithMetadata:
    """Test ToolDefinition includes metadata from decorator."""

    def test_tool_definition_includes_metadata(self):
        """ToolDefinition.metadata should be populated from decorator."""

        @tool(
            desc="Send a message",
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
                extras={"idp": "entraID"},
            ),
        )
        def send_message() -> str:
            """Send a message."""
            return "sent"

        definition = ToolCatalog.create_tool_definition(
            send_message, toolkit_name="TestToolkit", toolkit_version="1.0.0"
        )

        assert definition.metadata is not None
        assert definition.metadata.classification.domains == [Domain.MESSAGING]
        assert definition.metadata.behavior.verbs == [Verb.EXECUTE]
        assert definition.metadata.extras == {"idp": "entraID"}

    def test_tool_definition_without_metadata_is_none(self):
        """ToolDefinition.metadata should be None when not provided."""

        @tool(desc="Simple tool")
        def simple_tool() -> str:
            """A simple tool."""
            return "done"

        definition = ToolCatalog.create_tool_definition(
            simple_tool, toolkit_name="TestToolkit", toolkit_version="1.0.0"
        )

        assert definition.metadata is None
