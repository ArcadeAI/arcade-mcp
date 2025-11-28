"""
Example: Evaluating MCP Server Tools with arcade-evals

Shows TWO approaches:
1. Manual tool definitions (no MCP server required)
2. Automatic loading from running MCP server

Both approaches work the same way after loading.
"""

from arcade_evals import (
    BinaryCritic,
    EvalSuite,
    ExpectedToolCall,
    MCPToolRegistry,
)

# ============================================================================
# TWO WAYS TO GET TOOLS
# ============================================================================

# ──────────────────────────────────────────────────────────────────────────
# OPTION 1: Manual Definitions (NO MCP server needed) ✅ Simpler for demos
# ──────────────────────────────────────────────────────────────────────────
manual_tools = [
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

# ──────────────────────────────────────────────────────────────────────────
# OPTION 2: Automatic Loading (MCP server required) ⚡ Always up-to-date
# ──────────────────────────────────────────────────────────────────────────

# Example 1: Load from your own MCP server (stdio)
# from arcade_evals import load_from_stdio
# automatic_tools = load_from_stdio(["python", "my_server.py", "stdio"])

# Example 2: Load via stdio with custom env vars
# from arcade_evals import load_from_stdio
# automatic_tools = load_from_stdio(
#     ["npx", "-y", "@your/mcp-server"],
#     env={"API_KEY": "..."}
# )

# Example 3: Load from Arcade MCP server via stdio
# from arcade_evals import load_stdio_arcade
# automatic_tools = load_stdio_arcade(
#     ["python", "server.py", "stdio"],
#     arcade_api_key="arc_...",
#     arcade_user_id="user@example.com",
#     tool_secrets={"MY_SECRET": "secret_value"}
# )

# Example 4: Load from HTTP MCP server with headers
# from arcade_evals import load_from_http
# automatic_tools = load_from_http(
#     "http://localhost:8000",
#     headers={"Authorization": "Bearer your_token"}
# )

# Example 5: Load from Arcade Cloud MCP gateway
# from arcade_evals import load_arcade_cloud
# automatic_tools = load_arcade_cloud(
#     gateway_slug="your-gateway-slug",
#     arcade_api_key="arc_your_api_key",
#     arcade_user_id="user@example.com"
# )

# ============================================================================

# For this example, use manual tools (works immediately, no server needed)
tools_to_use = manual_tools

# To test with your own MCP server, uncomment:
# tools_to_use = load_from_stdio(["python", "my_server.py", "stdio"])

# Step 2: Create an MCP tool registry (same for both approaches!)
# By default, strict_mode=True which converts schemas to OpenAI strict mode format:
#   - additionalProperties: false at all levels
#   - All properties added to required array
#   - Optional params get nullable types (e.g., ["string", "null"])
#   - Unsupported keywords stripped (minimum, maximum, pattern, format, etc.)
registry = MCPToolRegistry(tools_to_use)

# To disable strict mode and use original schemas:
# registry = MCPToolRegistry(tools_to_use, strict_mode=False)

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
