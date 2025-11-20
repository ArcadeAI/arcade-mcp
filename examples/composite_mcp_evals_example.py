"""
Example: Evaluating Tools from Multiple MCP Servers

This example demonstrates how to use CompositeMCPRegistry to evaluate tools
from multiple MCP servers in a single evaluation suite.
"""

from arcade_evals import (
    BinaryCritic,
    CompositeMCPRegistry,
    EvalSuite,
    ExpectedToolCall,
)

# To load tools automatically from running servers, uncomment:
# github_tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])
# slack_tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-slack"])

# Step 1: Define tool descriptors from multiple MCP servers
# (or use load_from_stdio/load_from_http to load automatically)

calculator_tools = [
    {
        "name": "add",
        "description": "Add two numbers together",
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
        "name": "multiply",
        "description": "Multiply two numbers together",
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

string_tools = [
    {
        "name": "uppercase",
        "description": "Convert string to uppercase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert"},
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
                "text": {"type": "string", "description": "Text to reverse"},
            },
            "required": ["text"],
        },
    },
]

datetime_tools = [
    {
        "name": "format_date",
        "description": "Format a date string",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "format": {"type": "string", "default": "%Y-%m-%d"},
            },
            "required": ["date"],
        },
    },
]

# Step 2: Create a composite registry with tools from multiple servers
# Method 1: Pass tool lists directly
composite = CompositeMCPRegistry(
    tool_lists={
        "calculator": calculator_tools,
        "strings": string_tools,
        "datetime": datetime_tools,
    }
)

print("🎯 Composite MCP Registry Created!")
print(f"Servers: {', '.join(composite.get_server_names())}")
print()

# Step 3: Show how tools are namespaced
print("📋 All Tools (with namespacing):")
tools = composite.list_tools_for_model(tool_format="openai")
for tool in tools:
    name = tool["function"]["name"]
    desc = tool["function"]["description"]
    print(f"  - {name}: {desc}")
print()

# Step 4: Create an evaluation suite using the composite registry
suite = EvalSuite(
    name="Multi-Server Evaluation Suite",
    system_message="You are a helpful assistant with access to calculator, string, and datetime tools.",
    catalog=composite,
)

# Step 5: Add test cases using tools from different servers

# Test 1: Calculator server - using fully namespaced name
suite.add_case(
    name="Addition with namespace",
    user_message="What is 15 plus 7?",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator.add",  # Fully namespaced
            args={"a": 15, "b": 7},
        )
    ],
    critics=[
        BinaryCritic(critic_field="a", weight=0.5),
        BinaryCritic(critic_field="b", weight=0.5),
    ],
)

# Test 2: String server - using short unique name
suite.add_case(
    name="String uppercase",
    user_message="Convert 'hello world' to uppercase",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="uppercase",  # Short name (unique across all servers)
            args={"text": "hello world"},
        )
    ],
    critics=[
        BinaryCritic(critic_field="text", weight=1.0),
    ],
)

# Test 3: Multiple tool calls from different servers
suite.add_case(
    name="Mixed server operations",
    user_message="Calculate 10 times 5, then reverse the result",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator.multiply",
            args={"a": 10, "b": 5},
        ),
        ExpectedToolCall(
            tool_name="strings.reverse",
            args={"text": "50"},
        ),
    ],
    critics=[
        BinaryCritic(critic_field="a", weight=0.25),
        BinaryCritic(critic_field="b", weight=0.25),
        BinaryCritic(critic_field="text", weight=0.5),
    ],
)

# Test 4: Using defaults from schema
suite.add_case(
    name="Date formatting with default",
    user_message="Format the date 2025-11-18",
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="datetime.format_date",
            args={"date": "2025-11-18"},  # 'format' will use default
        )
    ],
    critics=[
        BinaryCritic(critic_field="date", weight=1.0),
    ],
)

# Step 6: Display configured cases
print("✅ Evaluation Suite Configured!")
print(f"Suite: {suite.name}")
print(f"Total cases: {len(suite.cases)}\n")

print("Configured test cases:")
for i, case in enumerate(suite.cases, 1):
    print(f"\n{i}. {case.name}")
    print(f"   Expected {len(case.expected_tool_calls)} tool call(s):")
    for tc in case.expected_tool_calls:
        print(f"   - {tc.name}({tc.args})")

# Step 7: Demonstrate name collision handling
print("\n\n🔍 Name Collision Example:")
print("=" * 60)

# Create two servers with the same tool name
tools_a = [
    {
        "name": "process",
        "description": "Process A",
        "inputSchema": {"type": "object", "properties": {}},
    }
]
tools_b = [
    {
        "name": "process",
        "description": "Process B",
        "inputSchema": {"type": "object", "properties": {}},
    }
]

collision_composite = CompositeMCPRegistry(tool_lists={"server_a": tools_a, "server_b": tools_b})

# Short name is ambiguous
try:
    collision_composite.resolve_tool_name("process")
except ValueError as e:
    print(f"❌ Short name fails: {e}")

# But namespaced names work fine
print(f"✅ Namespaced works: {collision_composite.resolve_tool_name('server_a.process')}")
print(f"✅ Namespaced works: {collision_composite.resolve_tool_name('server_b.process')}")

print("\n\n💡 Key Features:")
print("  • Combine tools from multiple MCP servers")
print("  • Automatic namespacing prevents collisions (server.tool)")
print("  • Short names work when unique across all servers")
print("  • Each server's tools maintain their own schemas and defaults")
print("  • All existing Python tool evaluations still work unchanged")

print("\n💡 To run actual evaluations, use:")
print("   results = suite.run(provider_api_key='your-api-key', model='gpt-4')")
