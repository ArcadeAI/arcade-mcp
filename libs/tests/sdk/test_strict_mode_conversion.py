"""
Comprehensive tests for OpenAI strict mode schema conversion.

These tests verify that _convert_to_strict_mode_schema properly converts
MCP tool schemas to OpenAI's strict mode format.

OpenAI Strict Mode Requirements:
1. additionalProperties: false - REQUIRED at ALL object levels
2. properties: {} - REQUIRED for all object types (even if empty)
3. required: [] - REQUIRED, must list ALL properties
4. Optional parameters use type union with null (e.g., ["string", "null"])
5. Unsupported keywords: minimum, maximum, pattern, format, nullable
"""

import json
from typing import Any

import pytest
from arcade_evals.registry import (
    _MAX_SCHEMA_DEPTH,
    MCPToolRegistry,
    SchemaConversionError,
    StrictModeParametersSchema,
    StrictModeToolSchema,
    _convert_to_strict_mode_schema,
)

# ----------------------------------------------------------------------------
# Test: Basic Strict Mode Requirements
# ----------------------------------------------------------------------------


class TestStrictModeBasicRequirements:
    """Test that basic OpenAI strict mode requirements are met."""

    def test_empty_properties_has_required_fields(self) -> None:
        """Test schema with empty properties has all required fields."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # Must have all required fields for strict mode
        assert result["type"] == "object"
        assert "properties" in result
        assert result["properties"] == {}
        assert "required" in result
        assert result["required"] == []
        assert result["additionalProperties"] is False

    def test_missing_properties_key_is_added(self) -> None:
        """Test that missing properties key is added."""
        input_schema: dict[str, Any] = {"type": "object"}

        result = _convert_to_strict_mode_schema(input_schema)

        assert "properties" in result
        assert result["properties"] == {}
        assert "required" in result
        assert result["required"] == []

    def test_additional_properties_always_false(self) -> None:
        """Test that additionalProperties is always set to False."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,  # Should be overwritten
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["additionalProperties"] is False

    def test_all_properties_in_required_array(self) -> None:
        """Test that ALL properties are added to required array."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "required_param": {"type": "string"},
                "optional_param": {"type": "number"},
            },
            "required": ["required_param"],  # Only one marked required
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # Both should be in required array
        assert "required_param" in result["required"]
        assert "optional_param" in result["required"]
        assert len(result["required"]) == 2


# ----------------------------------------------------------------------------
# Test: Optional Parameter Handling
# ----------------------------------------------------------------------------


class TestOptionalParameterHandling:
    """Test that optional parameters are properly converted."""

    def test_optional_param_gets_null_type(self) -> None:
        """Test optional parameters get null added to type."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "optional_string": {"type": "string"},
            },
            "required": [],  # None required = all optional
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["optional_string"]["type"] == ["string", "null"]

    def test_required_param_keeps_original_type(self) -> None:
        """Test required parameters keep their original type."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "required_string": {"type": "string"},
            },
            "required": ["required_string"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["required_string"]["type"] == "string"

    def test_mixed_required_and_optional(self) -> None:
        """Test mix of required and optional parameters."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "owner": {"type": "string"},
                "repo": {"type": "string"},
                "state": {"type": "string", "enum": ["open", "closed", "all"]},
                "per_page": {"type": "integer"},
            },
            "required": ["owner", "repo"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # Required params keep original type
        assert result["properties"]["owner"]["type"] == "string"
        assert result["properties"]["repo"]["type"] == "string"

        # Optional params get null type
        assert result["properties"]["state"]["type"] == ["string", "null"]
        assert result["properties"]["per_page"]["type"] == ["integer", "null"]

        # All params in required array
        assert len(result["required"]) == 4

    def test_array_type_gets_null_added(self) -> None:
        """Test that array types (unions) get null added properly."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "mixed_type": {"type": ["string", "number"]},
            },
            "required": [],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["mixed_type"]["type"] == ["string", "number", "null"]

    def test_null_not_duplicated(self) -> None:
        """Test that null is not added if already present."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "already_nullable": {"type": ["string", "null"]},
            },
            "required": [],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # Should not have duplicate null
        assert result["properties"]["already_nullable"]["type"] == ["string", "null"]
        assert result["properties"]["already_nullable"]["type"].count("null") == 1


# ----------------------------------------------------------------------------
# Test: Nested Object Handling
# ----------------------------------------------------------------------------


class TestNestedObjectHandling:
    """Test that nested objects are processed recursively."""

    def test_nested_object_gets_additional_properties_false(self) -> None:
        """Test nested objects get additionalProperties: false."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "inner": {"type": "string"},
                    },
                },
            },
            "required": ["nested"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["additionalProperties"] is False
        assert result["properties"]["nested"]["additionalProperties"] is False

    def test_nested_object_gets_required_array(self) -> None:
        """Test nested objects get required array with all properties."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "field1": {"type": "string"},
                        "field2": {"type": "number"},
                    },
                    "required": ["field1"],  # Only field1 marked required
                },
            },
            "required": ["nested"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        nested = result["properties"]["nested"]
        assert "field1" in nested["required"]
        assert "field2" in nested["required"]

    def test_deeply_nested_objects(self) -> None:
        """Test deeply nested objects are all processed."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "level3": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "required": ["level1"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # All levels should have additionalProperties: false
        assert result["additionalProperties"] is False
        level1 = result["properties"]["level1"]
        assert level1["additionalProperties"] is False
        level2 = level1["properties"]["level2"]
        assert level2["additionalProperties"] is False


# ----------------------------------------------------------------------------
# Test: Array Handling
# ----------------------------------------------------------------------------


class TestArrayHandling:
    """Test that arrays with object items are processed."""

    def test_array_with_object_items(self) -> None:
        """Test array items that are objects get processed."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["items"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        items_schema = result["properties"]["items"]["items"]
        assert items_schema["additionalProperties"] is False
        assert "properties" in items_schema
        assert "required" in items_schema

    def test_array_with_primitive_items(self) -> None:
        """Test array with primitive items is not modified."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["tags"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["tags"]["items"]["type"] == "string"


# ----------------------------------------------------------------------------
# Test: Schema Combiners (anyOf, oneOf, allOf)
# ----------------------------------------------------------------------------


class TestSchemaCombinersHandling:
    """Test that anyOf, oneOf, allOf are processed."""

    def test_anyof_with_objects(self) -> None:
        """Test anyOf with object schemas are processed."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "data": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        {"type": "string"},
                    ]
                },
            },
            "required": ["data"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        anyof = result["properties"]["data"]["anyOf"]
        # First option (object) should be processed
        assert anyof[0]["additionalProperties"] is False
        # Second option (string) should be unchanged
        assert anyof[1]["type"] == "string"


# ----------------------------------------------------------------------------
# Test: Original Schema Not Mutated
# ----------------------------------------------------------------------------


class TestOriginalSchemaNotMutated:
    """Test that the original schema is not mutated."""

    def test_original_schema_unchanged(self) -> None:
        """Test that original schema is not modified."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": [],
        }

        original_json = json.dumps(input_schema, sort_keys=True)

        _convert_to_strict_mode_schema(input_schema)

        after_json = json.dumps(input_schema, sort_keys=True)
        assert original_json == after_json


# ----------------------------------------------------------------------------
# Test: MCPToolRegistry Integration
# ----------------------------------------------------------------------------


class TestMCPToolRegistryIntegration:
    """Test that MCPToolRegistry produces valid OpenAI strict mode schemas."""

    def test_registry_produces_strict_mode_schema(self) -> None:
        """Test registry output has all strict mode requirements."""
        tool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                },
                "required": [],
            },
        }

        registry = MCPToolRegistry([tool])
        openai_tools = registry.list_tools_for_model("openai")

        assert len(openai_tools) == 1
        tool_schema = openai_tools[0]

        # Verify structure
        assert tool_schema["type"] == "function"
        assert tool_schema["function"]["strict"] is True

        params = tool_schema["function"]["parameters"]
        assert params["type"] == "object"
        assert params["additionalProperties"] is False
        assert "properties" in params
        assert "required" in params

    def test_registry_empty_properties_tool(self) -> None:
        """Test registry handles tools with empty properties."""
        tool = {
            "name": "no_params_tool",
            "description": "Tool with no parameters",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        }

        registry = MCPToolRegistry([tool])
        openai_tools = registry.list_tools_for_model("openai")

        params = openai_tools[0]["function"]["parameters"]
        assert params["properties"] == {}
        assert params["required"] == []
        assert params["additionalProperties"] is False


# ----------------------------------------------------------------------------
# Test: Real-World MCP Tool Examples
# ----------------------------------------------------------------------------


class TestRealWorldMCPTools:
    """Test with real-world MCP tool schemas."""

    def test_github_get_review_workload(self) -> None:
        """Test GitHub GetReviewWorkload tool (no parameters)."""
        tool = {
            "name": "Github_GetReviewWorkload",
            "description": "Get pull requests awaiting review by the authenticated user.",
            "inputSchema": {"type": "object", "properties": {}},
        }

        registry = MCPToolRegistry([tool])
        openai_tools = registry.list_tools_for_model("openai")

        params = openai_tools[0]["function"]["parameters"]
        assert params == {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

    def test_github_list_pull_requests(self) -> None:
        """Test GitHub ListPullRequests tool (mixed required/optional)."""
        tool = {
            "name": "Github_ListPullRequests",
            "description": "List pull requests in a GitHub repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "State filter",
                    },
                    "per_page": {"type": "integer", "description": "Results per page"},
                },
                "required": ["owner", "repo"],
            },
        }

        registry = MCPToolRegistry([tool])
        openai_tools = registry.list_tools_for_model("openai")

        params = openai_tools[0]["function"]["parameters"]

        # Required params keep type
        assert params["properties"]["owner"]["type"] == "string"
        assert params["properties"]["repo"]["type"] == "string"

        # Optional params get null type
        assert params["properties"]["state"]["type"] == ["string", "null"]
        assert params["properties"]["per_page"]["type"] == ["integer", "null"]

        # All in required array
        assert set(params["required"]) == {"owner", "repo", "state", "per_page"}

    def test_tool_with_nested_object_parameter(self) -> None:
        """Test tool with nested object in parameters."""
        tool = {
            "name": "create_record",
            "description": "Create a record with metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "created_by": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["created_by"],
                    },
                },
                "required": ["name", "metadata"],
            },
        }

        registry = MCPToolRegistry([tool])
        openai_tools = registry.list_tools_for_model("openai")

        params = openai_tools[0]["function"]["parameters"]

        # Root level
        assert params["additionalProperties"] is False

        # Nested metadata object
        metadata = params["properties"]["metadata"]
        assert metadata["additionalProperties"] is False
        assert "created_by" in metadata["required"]
        assert "tags" in metadata["required"]

        # tags is optional in original, should get null type
        assert metadata["properties"]["tags"]["type"] == ["array", "null"]


# ----------------------------------------------------------------------------
# Test: Type Validation
# ----------------------------------------------------------------------------


class TestTypeValidation:
    """Test that output matches expected types."""

    def test_output_is_strict_mode_parameters_schema(self) -> None:
        """Test that output conforms to StrictModeParametersSchema."""
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        result = _convert_to_strict_mode_schema(input_schema)

        # Verify required keys exist
        assert "type" in result
        assert "properties" in result
        assert "required" in result
        assert "additionalProperties" in result

        # Verify types
        assert result["type"] == "object"
        assert isinstance(result["properties"], dict)
        assert isinstance(result["required"], list)
        assert result["additionalProperties"] is False


# ----------------------------------------------------------------------------
# Test: Infinite Loop Protection
# ----------------------------------------------------------------------------


class TestStrictModeConfiguration:
    """Test the strict_mode configuration option."""

    def test_mcp_registry_strict_mode_default_true(self) -> None:
        """Test that strict_mode defaults to True."""
        registry = MCPToolRegistry([])
        assert registry.strict_mode is True

    def test_mcp_registry_strict_mode_false(self) -> None:
        """Test creating registry with strict_mode=False."""
        tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "integer", "minimum": 0}},
                "required": [],
            },
        }
        registry = MCPToolRegistry([tool], strict_mode=False)
        assert registry.strict_mode is False

        tools = registry.list_tools_for_model("openai")

        # Without strict mode, schema should be unchanged
        assert "strict" not in tools[0]["function"]
        assert "minimum" in tools[0]["function"]["parameters"]["properties"]["x"]
        assert "additionalProperties" not in tools[0]["function"]["parameters"]

    def test_mcp_registry_strict_mode_true(self) -> None:
        """Test creating registry with strict_mode=True."""
        tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "integer", "minimum": 0}},
                "required": [],
            },
        }
        registry = MCPToolRegistry([tool], strict_mode=True)

        tools = registry.list_tools_for_model("openai")

        # With strict mode, schema should be converted
        assert tools[0]["function"]["strict"] is True
        assert "minimum" not in tools[0]["function"]["parameters"]["properties"]["x"]
        assert tools[0]["function"]["parameters"]["additionalProperties"] is False

    def test_mcp_registry_strict_mode_setter(self) -> None:
        """Test changing strict_mode after creation."""
        tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {"type": "object", "properties": {}},
        }
        registry = MCPToolRegistry([tool], strict_mode=False)
        assert registry.strict_mode is False

        registry.strict_mode = True
        assert registry.strict_mode is True

        tools = registry.list_tools_for_model("openai")
        assert tools[0]["function"]["strict"] is True

    def test_composite_registry_strict_mode_default_true(self) -> None:
        """Test that CompositeMCPRegistry strict_mode defaults to True."""
        from arcade_evals.registry import CompositeMCPRegistry

        composite = CompositeMCPRegistry(tool_lists={"server": []})
        assert composite.strict_mode is True

    def test_composite_registry_strict_mode_propagates_to_tool_lists(self) -> None:
        """Test that strict_mode is propagated to registries created from tool_lists."""
        from arcade_evals.registry import CompositeMCPRegistry

        tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "integer", "minimum": 0}},
                "required": [],
            },
        }

        # With strict_mode=False
        composite = CompositeMCPRegistry(tool_lists={"server": [tool]}, strict_mode=False)

        tools = composite.list_tools_for_model("openai")
        assert "strict" not in tools[0]["function"]
        assert "minimum" in tools[0]["function"]["parameters"]["properties"]["x"]

    def test_composite_registry_respects_existing_registry_strict_mode(self) -> None:
        """Test that pre-existing registries keep their own strict_mode setting."""
        from arcade_evals.registry import CompositeMCPRegistry

        tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "integer", "minimum": 0}},
                "required": [],
            },
        }

        # Create registry with strict_mode=False
        registry = MCPToolRegistry([tool], strict_mode=False)

        # Pass to composite with strict_mode=True (should not affect pre-existing registry)
        composite = CompositeMCPRegistry(registries={"server": registry}, strict_mode=True)

        tools = composite.list_tools_for_model("openai")
        # The registry's strict_mode=False should be respected
        assert "strict" not in tools[0]["function"]


class TestInfiniteLoopProtection:
    """Test that deeply nested or circular schemas are handled safely."""

    def test_max_depth_constant_exists(self) -> None:
        """Test that MAX_SCHEMA_DEPTH constant is defined."""
        assert _MAX_SCHEMA_DEPTH > 0
        assert _MAX_SCHEMA_DEPTH == 50  # Default value

    def test_deeply_nested_schema_within_limit(self) -> None:
        """Test that schemas within depth limit are processed."""
        # Create a schema with 10 levels of nesting (well within limit)
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        current = schema
        for i in range(10):
            current["properties"] = {
                f"level{i}": {
                    "type": "object",
                    "properties": {},
                }
            }
            current = current["properties"][f"level{i}"]

        # Should not raise
        result = _convert_to_strict_mode_schema(schema)
        assert result["additionalProperties"] is False

    def test_exceeds_max_depth_raises_error(self) -> None:
        """Test that schemas exceeding max depth raise SchemaConversionError."""
        # Create a schema that exceeds the max depth
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        current = schema
        for i in range(_MAX_SCHEMA_DEPTH + 5):
            current["properties"] = {
                f"level{i}": {
                    "type": "object",
                    "properties": {},
                }
            }
            current = current["properties"][f"level{i}"]

        with pytest.raises(SchemaConversionError, match="maximum depth"):
            _convert_to_strict_mode_schema(schema)

    def test_error_message_is_descriptive(self) -> None:
        """Test that the error message mentions circular references."""
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        current = schema
        for i in range(_MAX_SCHEMA_DEPTH + 1):
            current["properties"] = {f"level{i}": {"type": "object", "properties": {}}}
            current = current["properties"][f"level{i}"]

        with pytest.raises(SchemaConversionError) as exc_info:
            _convert_to_strict_mode_schema(schema)

        assert "circular reference" in str(exc_info.value).lower()

    def test_array_nesting_counts_toward_depth(self) -> None:
        """Test that array item nesting also counts toward depth."""
        # Create nested arrays with objects
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        current = schema
        for i in range(_MAX_SCHEMA_DEPTH + 5):
            current["properties"] = {
                f"items{i}": {
                    "type": "array",
                    "items": {"type": "object", "properties": {}},
                }
            }
            current = current["properties"][f"items{i}"]["items"]

        with pytest.raises(SchemaConversionError):
            _convert_to_strict_mode_schema(schema)
