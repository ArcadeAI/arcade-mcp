"""
Tests for ToolCallOutput schema validation with complex types.
"""

import pytest
from arcade_core.schema import ToolCallError, ToolCallLog, ToolCallOutput
from pydantic import ValidationError


class TestToolCallOutputValidation:
    """Test ToolCallOutput validation with various data types."""

    def test_basic_types(self):
        """Test that basic types are validated correctly."""
        # String
        output = ToolCallOutput(value="test string")
        assert output.value == "test string"

        # Integer
        output = ToolCallOutput(value=42)
        assert output.value == 42

        # Float
        output = ToolCallOutput(value=3.14)
        assert output.value == 3.14

        # Boolean
        output = ToolCallOutput(value=True)
        assert output.value is True

        # None
        output = ToolCallOutput(value=None)
        assert output.value is None

    def test_dict_types(self):
        """Test that dict types are validated correctly."""
        # Simple dict
        output = ToolCallOutput(value={"key": "value"})
        assert output.value == {"key": "value"}

        # Nested dict
        output = ToolCallOutput(value={"outer": {"inner": "value"}})
        assert output.value == {"outer": {"inner": "value"}}

        # Empty dict
        output = ToolCallOutput(value={})
        assert output.value == {}

        # Dict with mixed types
        output = ToolCallOutput(
            value={
                "string": "text",
                "number": 123,
                "float": 45.6,
                "bool": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            }
        )
        assert output.value["string"] == "text"
        assert output.value["number"] == 123
        assert output.value["list"] == [1, 2, 3]

    def test_list_types(self):
        """Test that list types are validated correctly."""
        # List of strings (original type)
        output = ToolCallOutput(value=["a", "b", "c"])
        assert output.value == ["a", "b", "c"]

        # List of integers
        output = ToolCallOutput(value=[1, 2, 3])
        assert output.value == [1, 2, 3]

        # List of dicts (TypedDict at runtime)
        output = ToolCallOutput(value=[{"id": 1, "name": "first"}, {"id": 2, "name": "second"}])
        assert output.value == [{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]

        # Mixed type list
        output = ToolCallOutput(value=[1, "two", 3.0, True, None, {"key": "value"}])
        assert len(output.value) == 6
        assert output.value[5] == {"key": "value"}

        # Empty list
        output = ToolCallOutput(value=[])
        assert output.value == []

        # Nested lists
        output = ToolCallOutput(value=[[1, 2], [3, 4], [5, 6]])
        assert output.value == [[1, 2], [3, 4], [5, 6]]

    def test_complex_nested_structures(self):
        """Test complex nested structures that might come from TypedDict."""
        # Simulate a complex API response structure
        complex_data = {
            "status": "success",
            "data": {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "roles": ["admin", "user"],
                        "metadata": {"last_login": "2024-01-01", "active": True},
                    },
                    {
                        "id": 2,
                        "name": "Bob",
                        "roles": ["user"],
                        "metadata": {"last_login": "2024-01-02", "active": False},
                    },
                ],
                "total": 2,
                "page_info": {"page": 1, "per_page": 10, "has_next": False},
            },
            "errors": [],
        }

        output = ToolCallOutput(value=complex_data)
        assert output.value == complex_data
        assert output.value["data"]["users"][0]["name"] == "Alice"
        assert output.value["data"]["page_info"]["has_next"] is False

    def test_error_and_logs_with_value(self):
        """Test that error and logs can coexist with different value types."""
        # With dict value and logs
        output = ToolCallOutput(
            value={"result": "success"},
            logs=[
                ToolCallLog(message="Processing started", level="info"),
                ToolCallLog(message="Deprecation warning", level="warning", subtype="deprecation"),
            ],
        )
        assert output.value == {"result": "success"}
        assert len(output.logs) == 2

        # With list value and error
        output = ToolCallOutput(
            error=ToolCallError(
                message="Partial failure",
                developer_message="Some items failed to process",
                can_retry=True,
            )
        )
        assert output.error.message == "Partial failure"
        assert output.value is None

    def test_unsupported_types_still_fail(self):
        """Test that truly unsupported types still fail validation."""

        # Custom object (not dict, list, or basic type)
        class CustomClass:
            def __init__(self):
                self.data = "test"

        # This should fail because CustomClass instance is not a supported type
        # Note: This test is about Pydantic validation, not the output factory
        # The output factory would catch this earlier
        with pytest.raises(ValidationError):
            # Directly creating with an unsupported type should fail
            ToolCallOutput(value=CustomClass())

    def test_very_large_structures(self):
        """Test that large structures are handled properly."""
        # Large list of dicts
        large_list = [{"id": i, "value": f"item_{i}"} for i in range(1000)]
        output = ToolCallOutput(value=large_list)
        assert len(output.value) == 1000
        assert output.value[500]["id"] == 500

        # Deeply nested structure
        deep_dict = {"level1": {"level2": {"level3": {"level4": {"level5": "deep_value"}}}}}
        output = ToolCallOutput(value=deep_dict)
        assert output.value["level1"]["level2"]["level3"]["level4"]["level5"] == "deep_value"

    def test_json_serializable(self):
        """Test that all supported types are JSON serializable."""
        import json

        test_cases = [
            {"type": "string"},
            ["list", "of", "strings"],
            [{"id": 1}, {"id": 2}],
            {"nested": {"data": [1, 2, 3]}},
            123,
            45.6,
            True,
            None,
        ]

        for test_value in test_cases:
            output = ToolCallOutput(value=test_value)
            # This should not raise an exception
            json_str = json.dumps(output.model_dump())
            # And we should be able to parse it back
            parsed = json.loads(json_str)
            assert parsed["value"] == test_value
