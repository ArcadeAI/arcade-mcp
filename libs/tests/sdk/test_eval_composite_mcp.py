"""Tests for CompositeMCPRegistry functionality."""

from typing import Any

import pytest
from arcade_evals import (
    BinaryCritic,
    CompositeMCPRegistry,
    EvalSuite,
    ExpectedToolCall,
    MCPToolRegistry,
)


def get_calculator_tools() -> list[dict[str, Any]]:
    """Sample calculator MCP tools."""
    return [
        {
            "name": "add",
            "description": "Add two numbers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number", "default": 0},
                },
                "required": ["a"],
            },
        },
        {
            "name": "multiply",
            "description": "Multiply two numbers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    ]


def get_string_tools() -> list[dict[str, Any]]:
    """Sample string manipulation MCP tools."""
    return [
        {
            "name": "uppercase",
            "description": "Convert string to uppercase",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "reverse",
            "description": "Reverse a string",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    ]


def get_duplicate_tools() -> list[dict[str, Any]]:
    """Tools with duplicate names (to test collision handling)."""
    return [
        {
            "name": "add",  # Duplicate name!
            "description": "Add strings together",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "str1": {"type": "string"},
                    "str2": {"type": "string"},
                },
                "required": ["str1", "str2"],
            },
        },
    ]


# Initialization tests


def test_composite_registry_init_with_tool_lists() -> None:
    """Test initializing composite registry with tool descriptor lists."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    assert len(composite.get_server_names()) == 2
    assert "calculator" in composite.get_server_names()
    assert "strings" in composite.get_server_names()


def test_composite_registry_init_with_registries() -> None:
    """Test initializing composite registry with MCPToolRegistry instances."""
    calc_registry = MCPToolRegistry(get_calculator_tools())
    string_registry = MCPToolRegistry(get_string_tools())

    composite = CompositeMCPRegistry(
        registries={
            "calc": calc_registry,
            "str": string_registry,
        }
    )

    assert len(composite.get_server_names()) == 2
    assert composite.get_registry("calc") is calc_registry
    assert composite.get_registry("str") is string_registry


def test_composite_registry_init_mixed() -> None:
    """Test initializing with both registries and tool lists."""
    calc_registry = MCPToolRegistry(get_calculator_tools())

    composite = CompositeMCPRegistry(
        registries={"calc": calc_registry},
        tool_lists={"strings": get_string_tools()},
    )

    assert len(composite.get_server_names()) == 2


def test_composite_registry_init_empty() -> None:
    """Test that initializing without any registries fails."""
    with pytest.raises(ValueError, match="At least one registry"):
        CompositeMCPRegistry()


def test_composite_registry_init_duplicate_server_name() -> None:
    """Test that duplicate server names in mixed init fail."""
    calc_registry = MCPToolRegistry(get_calculator_tools())

    with pytest.raises(ValueError, match="Duplicate server name"):
        CompositeMCPRegistry(
            registries={"calc": calc_registry},
            tool_lists={"calc": get_string_tools()},
        )


# Tool listing tests


def test_composite_list_tools_for_model() -> None:
    """Test listing all tools from multiple registries."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    tools = composite.list_tools_for_model(tool_format="openai")

    assert len(tools) == 4  # 2 calc + 2 string tools
    tool_names = [t["function"]["name"] for t in tools]

    # All tools should be namespaced with underscores (OpenAI compatible)
    assert "calculator_add" in tool_names
    assert "calculator_multiply" in tool_names
    assert "strings_uppercase" in tool_names
    assert "strings_reverse" in tool_names


def test_composite_list_tools_unsupported_format() -> None:
    """Test that unsupported tool formats raise an error."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    with pytest.raises(ValueError, match="not supported"):
        composite.list_tools_for_model(tool_format="anthropic")


# Name resolution tests


def test_composite_resolve_namespaced_tool_name() -> None:
    """Test resolving fully namespaced tool names."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    # Fully namespaced names (both notations) should resolve to underscore format
    assert composite.resolve_tool_name("calculator.add") == "calculator_add"
    assert composite.resolve_tool_name("calculator_add") == "calculator_add"
    assert composite.resolve_tool_name("strings.uppercase") == "strings_uppercase"
    assert composite.resolve_tool_name("strings_uppercase") == "strings_uppercase"


def test_composite_resolve_short_unique_name() -> None:
    """Test resolving short tool names when unique across servers."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    # Short names should auto-resolve if unique
    assert composite.resolve_tool_name("add") == "calculator_add"
    assert composite.resolve_tool_name("uppercase") == "strings_uppercase"


def test_composite_resolve_ambiguous_name() -> None:
    """Test that ambiguous tool names raise helpful errors."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_duplicate_tools(),  # Both have 'add'
        }
    )

    # Ambiguous short name should fail
    with pytest.raises(ValueError, match="ambiguous.*multiple servers"):
        composite.resolve_tool_name("add")

    # But namespaced names should still work
    assert composite.resolve_tool_name("calculator.add") == "calculator_add"
    assert composite.resolve_tool_name("strings.add") == "strings_add"


def test_composite_resolve_nonexistent_tool() -> None:
    """Test that nonexistent tool names raise errors."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    with pytest.raises(ValueError, match="not found"):
        composite.resolve_tool_name("nonexistent")


def test_composite_resolve_non_string() -> None:
    """Test that non-string identifiers raise TypeError."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    with pytest.raises(TypeError, match="string names"):
        composite.resolve_tool_name(123)


# Argument normalization tests


def test_composite_normalize_args_with_defaults() -> None:
    """Test normalizing arguments with defaults from schema."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    # 'add' has default for 'b'
    args = composite.normalize_args("calculator.add", {"a": 5})
    assert args == {"a": 5, "b": 0}

    # Also works with short name if unique
    args = composite.normalize_args("add", {"a": 10})
    assert args == {"a": 10, "b": 0}


def test_composite_normalize_args_no_defaults() -> None:
    """Test normalizing arguments when no defaults exist."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    # 'multiply' has no defaults
    args = composite.normalize_args("calculator.multiply", {"a": 5, "b": 3})
    assert args == {"a": 5, "b": 3}


def test_composite_normalize_args_across_registries() -> None:
    """Test normalizing arguments from different registries."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    # Should work for tools from different registries
    calc_args = composite.normalize_args("calculator.add", {"a": 5})
    assert calc_args == {"a": 5, "b": 0}

    string_args = composite.normalize_args("strings.uppercase", {"text": "hello"})
    assert string_args == {"text": "hello"}


# Schema retrieval tests


def test_composite_get_tool_schema() -> None:
    """Test retrieving tool schemas."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    schema = composite.get_tool_schema("calculator.add")
    assert schema is not None
    assert schema["name"] == "add"
    assert "inputSchema" in schema


def test_composite_get_tool_schema_short_name() -> None:
    """Test retrieving schema using short name."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    schema = composite.get_tool_schema("add")  # Short name
    assert schema is not None
    assert schema["name"] == "add"


def test_composite_get_tool_schema_nonexistent() -> None:
    """Test that nonexistent tool returns None."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    schema = composite.get_tool_schema("nonexistent")
    assert schema is None


# Dynamic registry addition tests


def test_composite_add_registry() -> None:
    """Test adding a registry after initialization."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    assert len(composite.get_server_names()) == 1

    # Add another registry
    string_registry = MCPToolRegistry(get_string_tools())
    composite.add_registry("strings", string_registry)

    assert len(composite.get_server_names()) == 2
    assert "strings" in composite.get_server_names()

    # Should be able to resolve new tools
    assert composite.resolve_tool_name("strings.uppercase") == "strings_uppercase"


def test_composite_add_registry_duplicate_name() -> None:
    """Test that adding duplicate server name fails."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    string_registry = MCPToolRegistry(get_string_tools())
    with pytest.raises(ValueError, match="already exists"):
        composite.add_registry("calculator", string_registry)


# Integration with EvalSuite tests


def test_eval_suite_with_composite_registry() -> None:
    """Test that EvalSuite works with composite registry."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    suite = EvalSuite(
        name="Multi-Server Suite",
        system_message="Test system",
        catalog=composite,
    )

    # Should accept composite registry
    assert suite.catalog is composite
    assert isinstance(suite.catalog, CompositeMCPRegistry)


def test_eval_suite_composite_add_case_namespaced() -> None:
    """Test adding cases with namespaced tool names."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    suite = EvalSuite(
        name="Multi-Server Suite",
        system_message="Test",
        catalog=composite,
    )

    # Add case with fully namespaced name
    suite.add_case(
        name="Calculator test",
        user_message="Add 5 and 3",
        expected_tool_calls=[ExpectedToolCall(tool_name="calculator.add", args={"a": 5, "b": 3})],
        critics=[BinaryCritic(critic_field="a", weight=1.0)],
    )

    assert len(suite.cases) == 1
    assert suite.cases[0].expected_tool_calls[0].name == "calculator_add"


def test_eval_suite_composite_add_case_short_unique() -> None:
    """Test adding cases with short unique tool names."""
    composite = CompositeMCPRegistry(tool_lists={"calculator": get_calculator_tools()})

    suite = EvalSuite(
        name="Single-Server Suite",
        system_message="Test",
        catalog=composite,
    )

    # Add case with short name (unique in this composite)
    suite.add_case(
        name="Calculator test",
        user_message="Add 5 and 3",
        expected_tool_calls=[ExpectedToolCall(tool_name="add", args={"a": 5, "b": 3})],
        critics=[BinaryCritic(critic_field="a", weight=1.0)],
    )

    # Should be resolved to namespaced version
    assert suite.cases[0].expected_tool_calls[0].name == "calculator_add"


def test_eval_suite_composite_add_case_ambiguous() -> None:
    """Test that ambiguous tool names in cases raise errors."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_duplicate_tools(),
        }
    )

    suite = EvalSuite(
        name="Ambiguous Suite",
        system_message="Test",
        catalog=composite,
    )

    # Should fail with ambiguous short name
    with pytest.raises(ValueError, match="ambiguous"):
        suite.add_case(
            name="Ambiguous test",
            user_message="Add something",
            expected_tool_calls=[ExpectedToolCall(tool_name="add", args={"a": 5})],
            critics=[BinaryCritic(critic_field="a", weight=1.0)],
        )


def test_eval_suite_composite_mixed_servers() -> None:
    """Test evaluation suite with tools from multiple servers."""
    composite = CompositeMCPRegistry(
        tool_lists={
            "calculator": get_calculator_tools(),
            "strings": get_string_tools(),
        }
    )

    suite = EvalSuite(
        name="Mixed Suite",
        system_message="Test",
        catalog=composite,
    )

    # Add cases using tools from different servers
    suite.add_case(
        name="Calc test",
        user_message="Add 5 and 3",
        expected_tool_calls=[ExpectedToolCall(tool_name="calculator.add", args={"a": 5, "b": 3})],
        critics=[BinaryCritic(critic_field="a", weight=1.0)],
    )

    suite.add_case(
        name="String test",
        user_message="Uppercase hello",
        expected_tool_calls=[
            ExpectedToolCall(tool_name="strings.uppercase", args={"text": "hello"})
        ],
        critics=[BinaryCritic(critic_field="text", weight=1.0)],
    )

    assert len(suite.cases) == 2
    assert suite.cases[0].expected_tool_calls[0].name == "calculator_add"
    assert suite.cases[1].expected_tool_calls[0].name == "strings_uppercase"
