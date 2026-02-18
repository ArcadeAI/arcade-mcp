import datetime

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError
from arcade_core.metadata import (
    _INDETERMINATE_OPERATIONS,
    _MUTATING_OPERATIONS,
    _READ_ONLY_OPERATIONS,
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)
from arcade_tdk import tool


class TestEnumCoverage:
    """
    Tests to ensure all enum values are accounted for in validation helper sets.

    These tests will fail if new enum values are added without updating the
    corresponding helper sets, ensuring future maintainers don't forget to
    categorize new values.
    """

    def test_all_operations_are_categorized(self):
        """Every Operation must be in _READ_ONLY_OPERATIONS, _MUTATING_OPERATIONS, or _INDETERMINATE_OPERATIONS."""
        all_operations = set(Operation)
        categorized_operations = (
            _READ_ONLY_OPERATIONS | _MUTATING_OPERATIONS | _INDETERMINATE_OPERATIONS
        )

        # Check that every operation is categorized
        uncategorized = all_operations - categorized_operations
        assert not uncategorized, (
            f"The following Operation values are not categorized in _READ_ONLY_OPERATIONS, "
            f"_MUTATING_OPERATIONS, or _INDETERMINATE_OPERATIONS: {uncategorized}. "
            f"Please add them to the appropriate set in arcade_core/metadata.py"
        )

        # Check that there are no extra operations in the sets that don't exist in the enum
        extra = categorized_operations - all_operations
        assert not extra, (
            f"The following values are in _READ_ONLY_OPERATIONS, _MUTATING_OPERATIONS, or "
            f"_INDETERMINATE_OPERATIONS but don't exist in the Operation enum: {extra}"
        )

    def test_operation_categories_are_disjoint(self):
        """_READ_ONLY_OPERATIONS, _MUTATING_OPERATIONS, and _INDETERMINATE_OPERATIONS should not overlap."""
        ro_mut = _READ_ONLY_OPERATIONS & _MUTATING_OPERATIONS
        assert not ro_mut, (
            f"The following Operation values appear in both _READ_ONLY_OPERATIONS and "
            f"_MUTATING_OPERATIONS: {ro_mut}. An operation should be in exactly one category."
        )

        ro_ind = _READ_ONLY_OPERATIONS & _INDETERMINATE_OPERATIONS
        assert not ro_ind, (
            f"The following Operation values appear in both _READ_ONLY_OPERATIONS and "
            f"_INDETERMINATE_OPERATIONS: {ro_ind}. An operation should be in exactly one category."
        )

        mut_ind = _MUTATING_OPERATIONS & _INDETERMINATE_OPERATIONS
        assert not mut_ind, (
            f"The following Operation values appear in both _MUTATING_OPERATIONS and "
            f"_INDETERMINATE_OPERATIONS: {mut_ind}. An operation should be in exactly one category."
        )


class TestToolMetadataValidation:
    """Test strict mode validation rules for ToolMetadata."""

    def test_valid_metadata_passes(self):
        """Valid metadata with consistent values should not raise."""
        metadata = ToolMetadata(
            classification=Classification(
                service_domains=[ServiceDomain.EMAIL],
            ),
            behavior=Behavior(
                operations=[Operation.CREATE],
                read_only=False,
                destructive=False,
                open_world=True,
            ),
        )
        assert metadata is not None

    def test_mutating_operation_with_read_only_raises(self):
        """Mutating operations with read_only=True should raise when validated."""
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.CREATE], read_only=True),
        )
        with pytest.raises(
            ToolDefinitionError, match="mutating operation.*but is marked read_only=True"
        ):
            metadata.validate_for_tool()

    def test_opaque_with_read_only_raises(self):
        """OPAQUE operation with read_only=True should raise when validated."""
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.OPAQUE], read_only=True),
        )
        with pytest.raises(
            ToolDefinitionError, match="OPAQUE operation but is marked read_only=True"
        ):
            metadata.validate_for_tool()

    def test_delete_without_destructive_raises(self):
        """DELETE operation without destructive=True should raise when validated."""
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.DELETE], destructive=False),
        )
        with pytest.raises(
            ToolDefinitionError, match="'DELETE' operation.*but is not marked destructive=True"
        ):
            metadata.validate_for_tool()

    def test_service_domain_with_open_world_false_raises(self):
        """ServiceDomain present with open_world=False should raise when validated."""
        metadata = ToolMetadata(
            classification=Classification(service_domains=[ServiceDomain.EMAIL]),
            behavior=Behavior(open_world=False),
        )
        with pytest.raises(
            ToolDefinitionError, match="ServiceDomain.*but is marked open_world=False"
        ):
            metadata.validate_for_tool()

    def test_strict_false_bypasses_validation(self):
        """Setting strict=False should bypass all validation rules."""
        # This would normally raise due to contradiction
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.CREATE], read_only=True),
            strict=False,
        )
        # No error should be raised when validate_for_tool is called
        metadata.validate_for_tool()  # Should not raise
        assert metadata is not None

    def test_error_message_includes_operation_name(self):
        """Error messages should include the operation name for debugging."""
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.CREATE], read_only=True),
        )
        with pytest.raises(ToolDefinitionError, match="Tool has the mutating operation"):
            metadata.validate_for_tool()

    def test_read_only_operation_with_read_only_true_passes(self):
        """READ operation with read_only=True should pass validation."""
        metadata = ToolMetadata(
            behavior=Behavior(operations=[Operation.READ], read_only=True),
        )
        assert metadata is not None
        assert metadata.behavior.read_only is True

    def test_multiple_service_domains_allowed(self):
        """Tools can have multiple service domains."""
        metadata = ToolMetadata(
            classification=Classification(
                service_domains=[ServiceDomain.CLOUD_STORAGE, ServiceDomain.DOCUMENTS],
            ),
            behavior=Behavior(operations=[Operation.READ], read_only=True, open_world=True),
        )
        assert len(metadata.classification.service_domains) == 2

    def test_extras_accepts_json_native_values(self):
        """Extras field accepts JSON-native key/value pairs."""
        metadata = ToolMetadata(
            extras={"idp": "entraID", "requires_mfa": True, "max_requests": 100},
        )
        assert metadata.extras["idp"] == "entraID"
        assert metadata.extras["requires_mfa"] is True
        assert metadata.extras["max_requests"] == 100


class TestExtrasJsonSafety:
    """Test that ToolMetadata.extras enforces JSON-native types at all depths.

    JSON-native types: str, int, float, bool, None, dict (str keys), list.

    Top-level non-string keys are caught at construction time (field_validator).
    Nested keys and non-JSON-native values are caught at registration time
    (validate_for_tool) where the tool name is available for error context.
    """

    @pytest.mark.parametrize(
        "extras",
        [
            pytest.param(None, id="none"),
            pytest.param({}, id="empty_dict"),
            pytest.param(
                {"string": "hello", "int": 42, "float": 3.14, "bool": True, "null": None},
                id="flat_json_native_values",
            ),
            pytest.param({"config": {"api_key": "abc", "retries": 3}}, id="nested_dict"),
            pytest.param({"tags": ["a", "b"], "counts": [1, 2, 3]}, id="lists"),
            pytest.param(
                {"l1": {"l2": [{"l3": [1, "two", None, True, 3.0]}]}},
                id="deeply_nested",
            ),
            pytest.param(
                {"empty_dict": {}, "empty_list": [], "nested": {"also_empty": []}},
                id="empty_nested_structures",
            ),
        ],
    )
    def test_valid_json_safe_extras(self, extras: dict | None):
        metadata = ToolMetadata(extras=extras)
        assert metadata.extras == extras
        metadata.validate_for_tool()

    # --- Top-level non-string keys: caught at construction time ---

    @pytest.mark.parametrize(
        "extras",
        [
            pytest.param({3: "three"}, id="int_key"),
            pytest.param({True: "yes"}, id="bool_key"),
            pytest.param({None: "null key"}, id="none_key"),
        ],
    )
    def test_non_string_top_level_key_rejected_at_construction(self, extras: dict):
        with pytest.raises(ToolDefinitionError, match="must be strings"):
            ToolMetadata(extras=extras)

    # --- Nested non-string keys + non-JSON values: caught by validate_for_tool ---

    @pytest.mark.parametrize(
        "extras, match",
        [
            # Non-string keys nested in dicts/lists
            pytest.param({"o": {42: "v"}}, "must be strings", id="int_key_nested"),
            pytest.param({"o": {True: "v"}}, "must be strings", id="bool_key_nested"),
            pytest.param({"o": {(1, 2): "v"}}, "must be strings", id="tuple_key_nested"),
            pytest.param({"a": {"b": {42: "v"}}}, "must be strings", id="int_key_deep"),
            pytest.param({"items": [{True: "v"}]}, "must be strings", id="bool_key_in_list"),
            # Non-JSON-native values at top level
            pytest.param({"v": datetime.datetime(2023, 1, 1)}, "JSON-safe", id="datetime_value"),
            pytest.param({"v": datetime.date(2023, 1, 1)}, "JSON-safe", id="date_value"),
            pytest.param({"v": datetime.timedelta(seconds=60)}, "JSON-safe", id="timedelta_value"),
            pytest.param({"v": {1, 2, 3}}, "JSON-safe", id="set_value"),
            pytest.param({"v": frozenset([1, 2])}, "JSON-safe", id="frozenset_value"),
            pytest.param({"v": (1, 2)}, "JSON-safe", id="tuple_value"),
            pytest.param({"v": b"hello"}, "JSON-safe", id="bytes_value"),
            # Non-JSON-native values nested
            pytest.param(
                {"o": {"i": datetime.datetime(2023, 1, 1)}},
                "JSON-safe",
                id="datetime_nested_in_dict",
            ),
            pytest.param({"items": [1, "ok", {3, 4}]}, "JSON-safe", id="set_nested_in_list"),
            pytest.param(
                {"a": [{"b": [datetime.date(2023, 1, 1)]}]},
                "JSON-safe",
                id="date_deeply_nested",
            ),
        ],
    )
    def test_rejects_non_json_safe_extras_at_validation(self, extras: dict, match: str):
        metadata = ToolMetadata(extras=extras)
        with pytest.raises(ToolDefinitionError, match=match):
            metadata.validate_for_tool()

    # --- Error message quality ---

    def test_error_includes_path_for_nested_violations(self):
        metadata = ToolMetadata(extras={"outer": {42: "bad"}})
        with pytest.raises(ToolDefinitionError, match=r"extras\['outer'\]"):
            metadata.validate_for_tool()

        metadata = ToolMetadata(extras={"outer": datetime.datetime(2023, 1, 1)})
        with pytest.raises(ToolDefinitionError, match=r"extras\['outer'\]"):
            metadata.validate_for_tool()

    def test_error_includes_type_name(self):
        metadata = ToolMetadata(extras={"ts": datetime.datetime(2023, 1, 1)})
        with pytest.raises(ToolDefinitionError, match="datetime"):
            metadata.validate_for_tool()

    def test_error_reports_all_violations(self):
        metadata = ToolMetadata(extras={"ok_key": {True: "bool key"}, "bad": (1, 2)})
        with pytest.raises(ToolDefinitionError) as exc_info:
            metadata.validate_for_tool()
        msg = str(exc_info.value)
        assert "True" in msg
        assert "tuple" in msg


class TestToolDecoratorWithMetadata:
    """Test @tool decorator with metadata parameter."""

    def test_decorator_accepts_metadata(self):
        """Decorator should store metadata as __tool_metadata__ attribute."""

        @tool(
            desc="Test tool",
            metadata=ToolMetadata(
                classification=Classification(service_domains=[ServiceDomain.MESSAGING]),
                behavior=Behavior(operations=[Operation.CREATE], open_world=True),
            ),
        )
        def my_tool() -> str:
            return "test"

        assert hasattr(my_tool, "__tool_metadata__")
        assert my_tool.__tool_metadata__.classification.service_domains == [ServiceDomain.MESSAGING]

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
                    service_domains=[ServiceDomain.MESSAGING],
                ),
                behavior=Behavior(
                    operations=[Operation.CREATE],
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
        assert definition.metadata.classification.service_domains == [ServiceDomain.MESSAGING]
        assert definition.metadata.behavior.operations == [Operation.CREATE]
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
