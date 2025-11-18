"""
Example: Evaluating MCP Server Tools with arcade-evals

This example demonstrates how to evaluate tools from an MCP server
without requiring Python callables.
"""

from arcade_evals import BinaryCritic, EvalSuite, ExpectedToolCall, MCPToolRegistry

# Step 1: Define MCP tool descriptors
# These would typically come from an MCP server's tools/list response
mcp_tools = [
    {
        "name": "calculator_add",
        "description": "Add two numbers together",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number",
                },
                "b": {
                    "type": "number",
                    "description": "Second number",
                    "default": 0,  # Optional: MCP tools can specify defaults
                },
            },
            "required": ["a"],
        },
    },
    {
        "name": "calculator_multiply",
        "description": "Multiply two numbers together",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"],
        },
    },
]

# Step 2: Create an MCP tool registry
registry = MCPToolRegistry(mcp_tools)

# Step 3: Create an evaluation suite using the MCP registry
suite = EvalSuite(
    name="Calculator MCP Evaluation",
    system_message="You are a helpful calculator assistant. Use the available tools to perform calculations.",
    catalog=registry,  # Use MCP registry instead of ToolCatalog
)

# Step 4: Add test cases using tool names (not Python functions!)
suite.add_case(
    name="Simple addition",
    user_message="What is 5 plus 3?",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator_add",  # String name, not a callable
            args={"a": 5, "b": 3},
        )
    ],
    critics=[
        BinaryCritic(critic_field="a", weight=0.5),
        BinaryCritic(critic_field="b", weight=0.5),
    ],
)

suite.add_case(
    name="Addition with implicit default",
    user_message="Add 10",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator_add",
            args={"a": 10},  # 'b' will use default value of 0
        )
    ],
    critics=[
        BinaryCritic(critic_field="a", weight=1.0),
    ],
)

suite.add_case(
    name="Multiplication",
    user_message="What is 7 times 6?",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator_multiply",
            args={"a": 7, "b": 6},
        )
    ],
    critics=[
        BinaryCritic(critic_field="a", weight=0.5),
        BinaryCritic(critic_field="b", weight=0.5),
    ],
)

# Step 5: Demo the configuration
if __name__ == "__main__":
    print("Running MCP tool evaluations...")
    print(f"Suite: {suite.name}")
    print(f"Cases: {len(suite.cases)}")
    print()

    print("✅ MCP evaluation suite configured successfully!")
    print("\nConfigured cases:")
    for i, case in enumerate(suite.cases, 1):
        print(f"{i}. {case.name}")
        print(f"   Expected: {len(case.expected_tool_calls)} tool call(s)")
        for tc in case.expected_tool_calls:
            print(f"   - {tc.name}({tc.args})")

    print("\n💡 To run actual evaluations, use:")
    print("   results = suite.run(provider_api_key='your-api-key', model='gpt-4')")

    # Demo: Show how MCP tools are converted to OpenAI format
    print("\n📋 MCP tools converted to OpenAI format:")
    tools = registry.list_tools_for_model(tool_format="openai")
    for tool in tools:
        print(f"\n- {tool['function']['name']}")
        print(f"  Description: {tool['function']['description']}")
        function_params = tool["function"].get("parameters")
        if function_params and isinstance(function_params, dict):
            params = function_params.get("properties", {})
            if params:
                print(f"  Parameters: {', '.join(params.keys())}")
