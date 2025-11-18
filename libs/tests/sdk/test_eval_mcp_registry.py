"""Tests for MCP registry functionality in evaluations."""

from typing import Any

import pytest
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    MCPToolRegistry,
    NamedExpectedToolCall,
)
from arcade_evals.critic import Critic
from arcade_evals.eval import EvalCase


# MCP tool descriptor examples
def get_sample_mcp_tools() -> list[dict[str, Any]]:
    """Return sample MCP tool descriptors."""
    return [
        {
            "name": "calculator_add",
            "description": "Add two numbers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number", "default": 0},
                },
                "required": ["a"],
            },
        },
        {
            "name": "greeter_greet",
            "description": "Greet someone",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"},
                    "formal": {
                        "type": "boolean",
                        "description": "Use formal greeting",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        },
    ]


def test_mcp_registry_initialization() -> None:
    """Test MCPToolRegistry can be initialized with tools."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    assert len(registry._tools) == 2
    assert "calculator_add" in registry._tools
    assert "greeter_greet" in registry._tools


def test_mcp_registry_add_tool() -> None:
    """Test adding tools to registry after initialization."""
    registry = MCPToolRegistry()

    tool = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {"type": "object", "properties": {}},
    }
    registry.add_tool(tool)

    assert "test_tool" in registry._tools


def test_mcp_registry_add_tool_missing_name() -> None:
    """Test that adding a tool without name raises ValueError."""
    registry = MCPToolRegistry()

    with pytest.raises(ValueError, match="must have a 'name' field"):
        registry.add_tool({"description": "No name"})


def test_mcp_registry_list_tools_for_model() -> None:
    """Test converting MCP tools to OpenAI format."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    openai_tools = registry.list_tools_for_model("openai")

    assert len(openai_tools) == 2
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "calculator_add"
    assert "parameters" in openai_tools[0]["function"]


def test_mcp_registry_list_tools_unsupported_format() -> None:
    """Test that unsupported tool format raises ValueError."""
    registry = MCPToolRegistry(get_sample_mcp_tools())

    with pytest.raises(ValueError, match="not supported"):
        registry.list_tools_for_model("anthropic")


def test_mcp_registry_resolve_tool_name() -> None:
    """Test resolving tool names."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    # Should accept string names
    name = registry.resolve_tool_name("calculator_add")
    assert name == "calculator_add"

    # Should reject non-string identifiers
    with pytest.raises(TypeError, match="string names"):
        registry.resolve_tool_name(lambda: None)

    # Should reject unknown tools
    with pytest.raises(ValueError, match="not found"):
        registry.resolve_tool_name("unknown_tool")


def test_mcp_registry_normalize_args_with_defaults() -> None:
    """Test argument normalization with schema defaults."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    # Tool with default values
    args = {"a": 5}
    normalized = registry.normalize_args("calculator_add", args)

    assert normalized["a"] == 5
    assert normalized["b"] == 0  # Default value filled in


def test_mcp_registry_normalize_args_without_defaults() -> None:
    """Test argument normalization without defaults."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    # Provide all args explicitly
    args = {"name": "Alice", "formal": True}
    normalized = registry.normalize_args("greeter_greet", args)

    assert normalized == args


def test_mcp_registry_normalize_args_unknown_tool() -> None:
    """Test normalizing args for unknown tool returns args as-is."""
    registry = MCPToolRegistry(get_sample_mcp_tools())

    args = {"x": 1}
    normalized = registry.normalize_args("unknown_tool", args)

    assert normalized == args


def test_mcp_registry_get_tool_schema() -> None:
    """Test getting tool schema."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    schema = registry.get_tool_schema("calculator_add")
    assert schema is not None
    assert schema["name"] == "calculator_add"
    assert "inputSchema" in schema

    # Unknown tool returns None
    assert registry.get_tool_schema("unknown") is None


def test_expected_tool_call_with_tool_name() -> None:
    """Test ExpectedToolCall with tool_name (MCP style)."""
    # Should accept tool_name
    call = ExpectedToolCall(tool_name="my_tool", args={"param": "value"})
    assert call.tool_name == "my_tool"
    assert call.func is None

    # Should reject both func and tool_name
    with pytest.raises(ValueError, match="Only one"):
        ExpectedToolCall(func=lambda: None, tool_name="my_tool", args={})

    # Should reject neither
    with pytest.raises(ValueError, match="Either"):
        ExpectedToolCall(args={})


def test_eval_suite_with_mcp_registry() -> None:
    """Test EvalSuite working with MCPToolRegistry."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    suite = EvalSuite(
        name="MCP Test Suite",
        system_message="Test system",
        catalog=registry,
    )

    # Verify catalog is set up correctly
    assert suite.catalog is registry
    assert isinstance(suite.catalog, MCPToolRegistry)

    # Add a case with MCP-style tool call
    suite.add_case(
        name="Add numbers test",
        user_message="Add 5 and 3",
        expected_tool_calls=[ExpectedToolCall(tool_name="calculator_add", args={"a": 5, "b": 3})],
    )

    assert len(suite.cases) == 1
    case = suite.cases[0]
    assert case.name == "Add numbers test"
    assert len(case.expected_tool_calls) == 1


def test_eval_suite_mcp_converts_to_named_call() -> None:
    """Test that MCP expected calls are converted to NamedExpectedToolCall."""
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    suite = EvalSuite(
        name="Test Suite",
        system_message="Test",
        catalog=registry,
    )

    suite.add_case(
        name="Test case",
        user_message="Test",
        expected_tool_calls=[ExpectedToolCall(tool_name="calculator_add", args={"a": 10})],
    )

    case = suite.cases[0]
    expected_call = case.expected_tool_calls[0]

    assert isinstance(expected_call, NamedExpectedToolCall)
    assert expected_call.name == "calculator_add"
    # Should have default filled in
    assert expected_call.args["a"] == 10
    assert expected_call.args["b"] == 0  # Default from schema


def test_eval_case_evaluate_with_mcp_tools() -> None:
    """Test evaluating a case with MCP tool calls."""
    expected_tool_calls = [
        NamedExpectedToolCall(name="calculator_add", args={"a": 5, "b": 3}),
    ]
    actual_tool_calls = [
        ("calculator_add", {"a": 5, "b": 3}),
    ]

    critics: list[Critic] = [
        BinaryCritic(critic_field="a", weight=0.5),
        BinaryCritic(critic_field="b", weight=0.5),
    ]

    case = EvalCase(
        name="TestCase",
        system_message="",
        user_message="",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(fail_threshold=0.8, tool_selection_weight=1.0),
    )

    result = case.evaluate(actual_tool_calls)

    # Tool selection: 1.0, critics: 0.5 + 0.5 = 1.0
    # Total: 2.0 / 2.0 = 1.0
    assert result.score == 1.0
    assert result.passed


def test_eval_case_evaluate_mcp_tools_mismatch() -> None:
    """Test evaluation when MCP tool calls don't match."""
    expected_tool_calls = [
        NamedExpectedToolCall(name="calculator_add", args={"a": 5, "b": 3}),
    ]
    actual_tool_calls = [
        ("calculator_add", {"a": 10, "b": 20}),
    ]

    critics: list[Critic] = [
        BinaryCritic(critic_field="a", weight=0.5),
        BinaryCritic(critic_field="b", weight=0.5),
    ]

    case = EvalCase(
        name="TestCase",
        system_message="",
        user_message="",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(fail_threshold=0.8, tool_selection_weight=1.0),
    )

    result = case.evaluate(actual_tool_calls)

    # Tool selection: 1.0, but critics don't match: 0.0
    # Total: 1.0 / 2.0 = 0.5
    assert result.score == 0.5
    assert not result.passed


def test_mixed_python_and_mcp_not_supported() -> None:
    """Test that we can't mix Python and MCP tools in same suite."""
    # This is more of a conceptual test - in practice, you'd use one registry or the other
    tools = get_sample_mcp_tools()
    registry = MCPToolRegistry(tools)

    suite = EvalSuite(
        name="Mixed Suite",
        system_message="Test",
        catalog=registry,
    )

    # MCP tools work fine
    suite.add_case(
        name="MCP case",
        user_message="Test",
        expected_tool_calls=[ExpectedToolCall(tool_name="calculator_add", args={"a": 1})],
    )

    # But trying to use Python func with MCP registry should fail
    with pytest.raises((ValueError, AttributeError)):
        suite.add_case(
            name="Python case",
            user_message="Test",
            expected_tool_calls=[ExpectedToolCall(func=lambda x: x, args={})],
        )
