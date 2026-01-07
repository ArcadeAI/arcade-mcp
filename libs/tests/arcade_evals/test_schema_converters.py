"""Tests for MCP tool schema converters (OpenAI and Anthropic formats)."""

import pytest
from arcade_evals._evalsuite._anthropic_schema import (
    convert_mcp_to_anthropic_tool,
    convert_mcp_tools_to_anthropic,
)
from arcade_evals._evalsuite._openai_schema import (
    SchemaConversionError,
    convert_to_strict_mode_schema,
)
from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestOpenAISchemaConversion:
    """Tests for OpenAI strict mode schema conversion."""

    def test_basic_schema_conversion(self):
        """Test basic schema conversion to OpenAI strict mode."""
        input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        assert result["type"] == "object"
        assert result["additionalProperties"] is False
        assert "query" in result["properties"]
        assert result["required"] == ["query"]

    def test_optional_params_get_null_union(self):
        """Test that optional parameters get null union type."""
        input_schema = {
            "type": "object",
            "properties": {
                "required_param": {"type": "string"},
                "optional_param": {"type": "integer"},
            },
            "required": ["required_param"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        # Required param should have single type
        assert result["properties"]["required_param"]["type"] == "string"

        # Optional param should have null union
        assert result["properties"]["optional_param"]["type"] == ["integer", "null"]

        # Both should be in required (OpenAI strict mode requirement)
        assert set(result["required"]) == {"required_param", "optional_param"}

    def test_unsupported_keywords_stripped(self):
        """Test that unsupported JSON Schema keywords are stripped."""
        input_schema = {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "default": 10,
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": "^[a-z]+$",
                    "format": "hostname",
                },
            },
            "required": ["count", "name"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        # These keywords should be stripped
        count_prop = result["properties"]["count"]
        assert "minimum" not in count_prop
        assert "maximum" not in count_prop
        assert "default" not in count_prop

        name_prop = result["properties"]["name"]
        assert "minLength" not in name_prop
        assert "maxLength" not in name_prop
        assert "pattern" not in name_prop
        assert "format" not in name_prop

    def test_enum_values_converted_to_strings(self):
        """Test that enum values are converted to strings."""
        input_schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [1, 2, "three"],
                },
            },
            "required": ["status"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["status"]["enum"] == ["1", "2", "three"]

    def test_integer_enum_type_changed_to_string(self):
        """Test that integer enums have their type changed to string.

        OpenAI strict mode validates enum values against the declared type.
        When enum values are converted to strings, the type must also change.

        Example error without fix:
        "enum value 0 does not validate against {'type': ['integer', 'null']}"
        """
        input_schema = {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "integer",
                    "enum": [0, 1, 2, 3, 4],
                    "description": "Priority: 0=none, 1=urgent, 2=high, 3=medium, 4=low",
                },
            },
            "required": ["priority"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        # Enum values should be strings
        assert result["properties"]["priority"]["enum"] == ["0", "1", "2", "3", "4"]
        # Type should be changed to string to match
        assert result["properties"]["priority"]["type"] == "string"

    def test_optional_integer_enum_type_changed_to_string_null_union(self):
        """Test that optional integer enums get type ["string", "null"].

        When an integer enum is optional:
        1. Enum values are converted to strings
        2. Type changes from "integer" to ["string", "null"]

        This fixes: "enum value 0 does not validate against {'type': ['integer', 'null']}"
        """
        input_schema = {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "integer",
                    "enum": [0, 1, 2, 3, 4],
                },
            },
            "required": [],  # priority is optional
        }

        result = convert_to_strict_mode_schema(input_schema)

        # Enum values should be strings
        assert result["properties"]["priority"]["enum"] == ["0", "1", "2", "3", "4"]
        # Type should be ["string", "null"] for optional param
        assert result["properties"]["priority"]["type"] == ["string", "null"]

    def test_string_enum_type_unchanged(self):
        """Test that string enums keep their type as string."""
        input_schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"],
                },
            },
            "required": ["status"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        # Enum values unchanged
        assert result["properties"]["status"]["enum"] == ["active", "inactive", "pending"]
        # Type remains string
        assert result["properties"]["status"]["type"] == "string"

    def test_boolean_enum_type_changed_to_string(self):
        """Test that boolean enums have their type changed to string."""
        input_schema = {
            "type": "object",
            "properties": {
                "flag": {
                    "type": "boolean",
                    "enum": [True, False],
                },
            },
            "required": ["flag"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        # Boolean values converted to strings
        assert result["properties"]["flag"]["enum"] == ["True", "False"]
        # Type changed to string
        assert result["properties"]["flag"]["type"] == "string"

    def test_enum_with_list_type_no_null(self):
        """Test that enums with list type but no null are converted to single string type."""
        input_schema = {
            "type": "object",
            "properties": {
                "priority": {
                    "type": ["integer"],
                    "enum": [1, 2, 3],
                },
            },
            "required": ["priority"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        assert result["properties"]["priority"]["enum"] == ["1", "2", "3"]
        # Should be "string", not ["string"]
        assert result["properties"]["priority"]["type"] == "string"

    def test_nested_object_enum_type_conversion(self):
        """Test that enum type conversion works in nested objects."""
        input_schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "integer",
                            "enum": [1, 2, 3],
                        },
                    },
                    "required": ["level"],
                },
            },
            "required": ["config"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        nested = result["properties"]["config"]["properties"]["level"]
        assert nested["enum"] == ["1", "2", "3"]
        assert nested["type"] == "string"

    def test_nested_object_gets_strict_mode(self):
        """Test that nested objects also get strict mode treatment."""
        input_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["user"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        nested = result["properties"]["user"]
        assert nested["additionalProperties"] is False
        # Both should be in required for nested object too
        assert set(nested["required"]) == {"name", "age"}
        # age is optional so should have null union
        assert nested["properties"]["age"]["type"] == ["integer", "null"]

    def test_array_items_processed(self):
        """Test that array items schema is processed."""
        input_schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "minimum": 0},
                        },
                        "required": ["id"],
                    },
                },
            },
            "required": ["items"],
        }

        result = convert_to_strict_mode_schema(input_schema)

        array_items = result["properties"]["items"]["items"]
        assert array_items["additionalProperties"] is False
        # minimum should be stripped from nested object property
        assert "minimum" not in array_items["properties"]["id"]

    def test_empty_schema(self):
        """Test conversion of empty schema."""
        input_schema = {"type": "object", "properties": {}}

        result = convert_to_strict_mode_schema(input_schema)

        assert result["type"] == "object"
        assert result["properties"] == {}
        assert result["additionalProperties"] is False
        assert result["required"] == []

    def test_max_depth_protection(self):
        """Test that deeply nested schemas raise an error."""
        # Create a deeply nested schema that exceeds max depth
        schema: dict = {"type": "object", "properties": {}}
        current = schema
        for i in range(60):  # Exceeds _MAX_SCHEMA_DEPTH of 50
            current["properties"] = {"nested": {"type": "object", "properties": {}}}
            current["required"] = ["nested"]
            current = current["properties"]["nested"]

        with pytest.raises(SchemaConversionError, match="maximum depth"):
            convert_to_strict_mode_schema(schema)


class TestAnthropicSchemaConversion:
    """Tests for Anthropic schema conversion."""

    def test_basic_conversion(self):
        """Test basic MCP to Anthropic tool conversion."""
        mcp_tool = {
            "name": "search_files",
            "description": "Search for files",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["name"] == "search_files"
        assert result["description"] == "Search for files"
        assert "input_schema" in result
        assert "inputSchema" not in result
        # Schema should be unchanged
        assert result["input_schema"]["properties"]["query"]["type"] == "string"

    def test_schema_preserved_as_is(self):
        """Test that the schema is preserved without modifications."""
        mcp_tool = {
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 10,
                    },
                },
                "required": ["count"],
            },
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        # Unlike OpenAI, these keywords should be preserved
        schema = result["input_schema"]
        assert schema["properties"]["count"]["minimum"] == 0
        assert schema["properties"]["count"]["maximum"] == 100
        assert schema["properties"]["count"]["default"] == 10

    def test_tool_name_dots_normalized_to_underscores(self):
        """Test that dots in tool names are converted to underscores.

        Anthropic tool names must match pattern: ^[a-zA-Z0-9_-]{1,64}$
        Dots are not allowed, so they must be converted.
        """
        mcp_tool = {
            "name": "Google.Search",
            "description": "Search Google",
            "inputSchema": {"type": "object", "properties": {}},
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["name"] == "Google_Search"

    def test_tool_name_hyphens_preserved(self):
        """Test that hyphens in tool names are preserved (they're valid)."""
        mcp_tool = {
            "name": "search-files",
            "description": "Search files",
            "inputSchema": {"type": "object", "properties": {}},
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["name"] == "search-files"

    def test_tool_name_multiple_dots(self):
        """Test that multiple dots are all converted to underscores."""
        mcp_tool = {
            "name": "Google.Gmail.Send.Email",
            "description": "Send email",
            "inputSchema": {"type": "object", "properties": {}},
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["name"] == "Google_Gmail_Send_Email"

    def test_missing_description_defaults_to_empty(self):
        """Test that missing description defaults to empty string."""
        mcp_tool = {
            "name": "test",
            "inputSchema": {"type": "object", "properties": {}},
        }

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["description"] == ""

    def test_missing_schema_defaults_to_empty_object(self):
        """Test that missing inputSchema defaults to empty object schema."""
        mcp_tool = {"name": "test"}

        result = convert_mcp_to_anthropic_tool(mcp_tool)

        assert result["input_schema"] == {"type": "object", "properties": {}}

    def test_convert_multiple_tools(self):
        """Test converting a list of MCP tools."""
        mcp_tools = [
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"},
        ]

        result = convert_mcp_tools_to_anthropic(mcp_tools)

        assert len(result) == 2
        assert result[0]["name"] == "tool1"
        assert result[1]["name"] == "tool2"


class TestToolRegistryOpenAIFormat:
    """Tests for EvalSuiteToolRegistry OpenAI format output."""

    def test_list_tools_openai_format(self):
        """Test listing tools in OpenAI format."""
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "search",
            "description": "Search function",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        })

        tools = registry.list_tools_for_model("openai")

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "search"
        assert tool["function"]["strict"] is True
        assert tool["function"]["parameters"]["additionalProperties"] is False

    def test_list_tools_openai_without_strict_mode(self):
        """Test OpenAI format without strict mode."""
        registry = EvalSuiteToolRegistry(strict_mode=False)
        registry.add_tool({
            "name": "search",
            "description": "Search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                },
                "required": ["query"],
            },
        })

        tools = registry.list_tools_for_model("openai")

        tool = tools[0]
        # No strict flag when strict_mode is False
        assert "strict" not in tool["function"]
        # Schema keywords should be preserved when strict_mode is False
        assert tool["function"]["parameters"]["properties"]["query"]["minLength"] == 1


class TestToolRegistryAnthropicFormat:
    """Tests for EvalSuiteToolRegistry Anthropic format output."""

    def test_list_tools_anthropic_format(self):
        """Test listing tools in Anthropic format."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "search",
            "description": "Search function",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        })

        tools = registry.list_tools_for_model("anthropic")

        assert len(tools) == 1
        tool = tools[0]
        # Anthropic format - flat structure
        assert "type" not in tool
        assert "function" not in tool
        assert tool["name"] == "search"
        assert tool["description"] == "Search function"
        assert "input_schema" in tool

    def test_anthropic_format_preserves_schema(self):
        """Test that Anthropic format preserves JSON Schema keywords."""
        registry = EvalSuiteToolRegistry(strict_mode=True)  # strict_mode shouldn't affect Anthropic
        registry.add_tool({
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                },
                "required": ["count"],
            },
        })

        tools = registry.list_tools_for_model("anthropic")

        # Schema should be preserved as-is for Anthropic
        schema = tools[0]["input_schema"]
        assert schema["properties"]["count"]["minimum"] == 0
        assert schema["properties"]["count"]["maximum"] == 100

    def test_anthropic_format_no_null_union(self):
        """Test that Anthropic format doesn't add null union types."""
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "test",
            "description": "Test",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"},
                    "optional_param": {"type": "integer"},
                },
                "required": ["required_param"],  # optional_param is optional
            },
        })

        tools = registry.list_tools_for_model("anthropic")

        # Optional param should NOT have null union for Anthropic
        optional_type = tools[0]["input_schema"]["properties"]["optional_param"]["type"]
        assert optional_type == "integer"
        assert not isinstance(optional_type, list)

    def test_anthropic_format_normalizes_tool_names(self):
        """Test that Anthropic format normalizes tool names (dots to underscores)."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Google.Gmail.Send",
            "description": "Send email via Gmail",
            "inputSchema": {"type": "object", "properties": {}},
        })

        tools = registry.list_tools_for_model("anthropic")

        # Dots should be converted to underscores
        assert tools[0]["name"] == "Google_Gmail_Send"


class TestToolRegistryOpenAINameNormalization:
    """Tests for OpenAI format tool name normalization."""

    def test_openai_format_normalizes_tool_names(self):
        """Test that OpenAI format normalizes tool names (dots to underscores).

        OpenAI function names don't allow dots, so they must be converted.
        """
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "Google.Search",
            "description": "Search Google",
            "inputSchema": {"type": "object", "properties": {}},
        })

        tools = registry.list_tools_for_model("openai")

        # Dots should be converted to underscores
        assert tools[0]["function"]["name"] == "Google_Search"

    def test_openai_format_normalizes_multiple_dots(self):
        """Test that multiple dots are all converted to underscores for OpenAI."""
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "Google.Gmail.Send.Email",
            "description": "Send email",
            "inputSchema": {"type": "object", "properties": {}},
        })

        tools = registry.list_tools_for_model("openai")

        assert tools[0]["function"]["name"] == "Google_Gmail_Send_Email"

    def test_openai_format_preserves_underscores(self):
        """Test that underscores in tool names are preserved for OpenAI."""
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "search_files",
            "description": "Search files",
            "inputSchema": {"type": "object", "properties": {}},
        })

        tools = registry.list_tools_for_model("openai")

        assert tools[0]["function"]["name"] == "search_files"


class TestToolRegistryFormatComparison:
    """Tests comparing OpenAI and Anthropic format outputs."""

    def test_same_tool_different_formats(self):
        """Test that the same tool produces correct different formats."""
        registry = EvalSuiteToolRegistry(strict_mode=True)
        registry.add_tool({
            "name": "search",
            "description": "Search for items",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        })

        openai_tools = registry.list_tools_for_model("openai")
        anthropic_tools = registry.list_tools_for_model("anthropic")

        # OpenAI format
        openai_tool = openai_tools[0]
        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["strict"] is True
        openai_params = openai_tool["function"]["parameters"]
        assert openai_params["additionalProperties"] is False
        # limit should have null union in OpenAI
        assert openai_params["properties"]["limit"]["type"] == ["integer", "null"]
        # default should be stripped in OpenAI
        assert "default" not in openai_params["properties"]["limit"]

        # Anthropic format
        anthropic_tool = anthropic_tools[0]
        assert "type" not in anthropic_tool
        assert "function" not in anthropic_tool
        anthropic_schema = anthropic_tool["input_schema"]
        # limit should have simple type in Anthropic
        assert anthropic_schema["properties"]["limit"]["type"] == "integer"
        # default should be preserved in Anthropic
        assert anthropic_schema["properties"]["limit"]["default"] == 10

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "test"})

        with pytest.raises(ValueError, match="not supported"):
            registry.list_tools_for_model("invalid")  # type: ignore


class TestToolRegistryMultipleTools:
    """Tests for registry with multiple tools."""

    def test_multiple_tools_both_formats(self):
        """Test multiple tools converted to both formats."""
        registry = EvalSuiteToolRegistry()
        registry.add_tools([
            {"name": "tool1", "description": "First"},
            {"name": "tool2", "description": "Second"},
            {"name": "tool3", "description": "Third"},
        ])

        openai_tools = registry.list_tools_for_model("openai")
        anthropic_tools = registry.list_tools_for_model("anthropic")

        assert len(openai_tools) == 3
        assert len(anthropic_tools) == 3

        # Verify names are preserved
        openai_names = {t["function"]["name"] for t in openai_tools}
        anthropic_names = {t["name"] for t in anthropic_tools}
        assert openai_names == {"tool1", "tool2", "tool3"}
        assert anthropic_names == {"tool1", "tool2", "tool3"}


class TestToolNameResolution:
    """Tests for tool name resolution (handling Anthropic normalized names)."""

    def test_resolve_original_name(self):
        """Test that original names resolve correctly."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search"})

        assert registry.resolve_tool_name("Google.Search") == "Google.Search"

    def test_resolve_normalized_name(self):
        """Test that normalized names (underscores) resolve to original."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search"})

        # Anthropic returns "Google_Search" but tool is stored as "Google.Search"
        assert registry.resolve_tool_name("Google_Search") == "Google.Search"

    def test_resolve_unknown_name_returns_none(self):
        """Test that unknown names return None."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search"})

        assert registry.resolve_tool_name("Unknown.Tool") is None
        assert registry.resolve_tool_name("Unknown_Tool") is None

    def test_has_tool_with_normalized_name(self):
        """Test has_tool works with normalized names."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Slack.Post"})

        assert registry.has_tool("Slack.Post") is True
        assert registry.has_tool("Slack_Post") is True  # Normalized
        assert registry.has_tool("Unknown") is False

    def test_get_tool_schema_with_normalized_name(self):
        """Test get_tool_schema works with normalized names."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Email.Send",
            "description": "Send email",
            "inputSchema": {"type": "object", "properties": {"to": {"type": "string"}}},
        })

        # Original name
        schema = registry.get_tool_schema("Email.Send")
        assert schema is not None
        assert schema["name"] == "Email.Send"

        # Normalized name
        schema = registry.get_tool_schema("Email_Send")
        assert schema is not None
        assert schema["name"] == "Email.Send"

    def test_normalize_args_with_normalized_tool_name(self):
        """Test normalize_args works when called with normalized name."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Calendar.Create",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "duration": {"type": "integer", "default": 30},
                },
            },
        })

        # Call normalize_args with the Anthropic-returned name
        result = registry.normalize_args("Calendar_Create", {"title": "Meeting"})

        # Should apply defaults even though lookup was by normalized name
        assert result["title"] == "Meeting"
        assert result["duration"] == 30

    def test_normalize_args_replaces_null_with_default(self):
        """Test normalize_args replaces null (None) values with defaults.

        OpenAI strict mode sends null for optional parameters that weren't provided.
        This test verifies that null values are replaced with schema defaults.
        """
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "offset": {"type": "integer", "default": 0},
                },
            },
        })

        # OpenAI strict mode might send null for optional params
        result = registry.normalize_args("Search", {"query": "test", "limit": None, "offset": None})

        # Null values should be replaced with defaults
        assert result["query"] == "test"
        assert result["limit"] == 10
        assert result["offset"] == 0

    def test_normalize_args_preserves_explicit_values(self):
        """Test normalize_args preserves explicitly set values (non-null)."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        })

        # Explicit value should be preserved
        result = registry.normalize_args("Search", {"query": "test", "limit": 50})

        assert result["query"] == "test"
        assert result["limit"] == 50  # Not replaced with default

    def test_multiple_dots_in_name(self):
        """Test tools with multiple dots in name."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Gmail.Send"})

        # Should normalize all dots
        assert registry.resolve_tool_name("Google_Gmail_Send") == "Google.Gmail.Send"
        assert registry.has_tool("Google_Gmail_Send") is True

    def test_no_dot_in_name_no_mapping(self):
        """Test that tools without dots don't create unnecessary mappings."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "simple_tool"})

        # Direct lookup works
        assert registry.resolve_tool_name("simple_tool") == "simple_tool"
        # No false positives
        assert registry.resolve_tool_name("simple.tool") is None

    def test_mixed_tools_resolution(self):
        """Test registry with mix of dotted and non-dotted names."""
        registry = EvalSuiteToolRegistry()
        registry.add_tools([
            {"name": "Google.Search"},
            {"name": "simple_search"},
            {"name": "Slack.Channel.Create"},
        ])

        # All originals resolve
        assert registry.resolve_tool_name("Google.Search") == "Google.Search"
        assert registry.resolve_tool_name("simple_search") == "simple_search"
        assert registry.resolve_tool_name("Slack.Channel.Create") == "Slack.Channel.Create"

        # Normalized versions resolve to originals
        assert registry.resolve_tool_name("Google_Search") == "Google.Search"
        assert registry.resolve_tool_name("Slack_Channel_Create") == "Slack.Channel.Create"


class TestProcessToolCall:
    """Tests for EvalSuiteToolRegistry.process_tool_call combined method."""

    def test_process_tool_call_resolves_and_normalizes(self):
        """Test that process_tool_call resolves name and applies defaults."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Google.Search",
            "description": "Search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        })

        # Anthropic-style name with missing default arg
        resolved_name, args = registry.process_tool_call("Google_Search", {"query": "test"})

        assert resolved_name == "Google.Search"
        assert args == {"query": "test", "limit": 10}

    def test_process_tool_call_unknown_tool(self):
        """Test that unknown tools keep original name."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "KnownTool"})

        resolved_name, args = registry.process_tool_call("UnknownTool", {"arg": "value"})

        assert resolved_name == "UnknownTool"
        assert args == {"arg": "value"}

    def test_process_tool_call_no_defaults_needed(self):
        """Test when all args provided."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({
            "name": "Tool",
            "inputSchema": {
                "type": "object",
                "properties": {"a": {"type": "string", "default": "x"}, "b": {"type": "string"}},
            },
        })

        resolved_name, args = registry.process_tool_call("Tool", {"a": "provided", "b": "also"})

        assert resolved_name == "Tool"
        assert args == {"a": "provided", "b": "also"}


class TestToolRegistryErrors:
    """Tests for EvalSuiteToolRegistry error handling."""

    def test_duplicate_tool_registration_raises_error(self):
        """Test that registering the same tool twice raises ValueError."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search", "description": "Search"})

        with pytest.raises(ValueError) as exc_info:
            registry.add_tool({"name": "Google.Search", "description": "Search again"})

        assert "already registered" in str(exc_info.value)
        assert "Google.Search" in str(exc_info.value)

    def test_tool_without_name_raises_error(self):
        """Test that registering a tool without name raises ValueError."""
        registry = EvalSuiteToolRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.add_tool({"description": "No name tool"})

        assert "name" in str(exc_info.value).lower()

    def test_empty_registry_tool_count(self):
        """Test that empty registry has zero tools."""
        registry = EvalSuiteToolRegistry()
        assert registry.tool_count() == 0
        assert registry.tool_names() == []

    def test_empty_registry_list_tools(self):
        """Test that empty registry returns empty list for both formats."""
        registry = EvalSuiteToolRegistry()
        assert registry.list_tools_for_model("openai") == []
        assert registry.list_tools_for_model("anthropic") == []

    def test_invalid_format_raises_error(self):
        """Test that invalid tool format raises ValueError."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "test"})

        with pytest.raises(ValueError) as exc_info:
            registry.list_tools_for_model("invalid_format")  # type: ignore

        assert "not supported" in str(exc_info.value)


class TestToolNameCollisions:
    """Tests for handling tool name collisions during normalization."""

    def test_different_original_names_same_normalized(self):
        """Test that tools with different original names but same normalized name are both registered.

        This is the expected behavior: `Google.Search` and `Google_Search` are treated as
        different tools because the registry uses original names as keys.
        The normalized name mapping only helps with lookup (for Anthropic format).
        """
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search", "description": "Dot version"})
        registry.add_tool({"name": "Google_Search", "description": "Underscore version"})

        # Both tools should be registered
        assert registry.tool_count() == 2
        assert "Google.Search" in registry.tool_names()
        assert "Google_Search" in registry.tool_names()

    def test_normalized_name_resolution_prefers_underscore_version(self):
        """Test that when both Google.Search and Google_Search exist,
        resolving 'Google_Search' returns the explicit underscore version.
        """
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search", "description": "Dot version"})
        registry.add_tool({"name": "Google_Search", "description": "Underscore version"})

        # "Google_Search" should resolve to itself (explicit match)
        resolved = registry.resolve_tool_name("Google_Search")
        assert resolved == "Google_Search"

        # "Google.Search" should resolve to itself (exact match)
        resolved = registry.resolve_tool_name("Google.Search")
        assert resolved == "Google.Search"

    def test_normalized_lookup_when_only_dot_version_exists(self):
        """Test that normalized name lookup works when only dot version exists."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search", "description": "Dot version"})

        # "Google_Search" should resolve to "Google.Search"
        resolved = registry.resolve_tool_name("Google_Search")
        assert resolved == "Google.Search"

    def test_anthropic_format_normalizes_names(self):
        """Test that Anthropic format output uses normalized names (underscores)."""
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "Google.Search", "description": "Search"})

        tools = registry.list_tools_for_model("anthropic")

        # Anthropic format should have normalized name
        assert tools[0]["name"] == "Google_Search"
