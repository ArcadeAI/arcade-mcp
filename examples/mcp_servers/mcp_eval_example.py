"""
Example: Using arcade evals with MCP server tools

This example demonstrates how to evaluate MCP server tools without requiring
Python callables. You can use tool descriptors directly from an MCP server's
tools/list response.
"""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    MCPToolRegistry,
)


def create_mcp_eval_example() -> EvalSuite:
    """
    Example showing how to evaluate MCP server tools.

    This approach works with any MCP server, whether it's:
    - A third-party MCP server running via HTTP
    - A local MCP server via stdio
    - Tool descriptors you've manually created
    """

    # Step 1: Define your MCP tool descriptors
    # These would typically come from an MCP server's tools/list response
    mcp_tools = [
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
            "name": "calculator_multiply",
            "description": "Multiply two numbers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "First number"},
                    "y": {"type": "number", "description": "Second number"},
                },
                "required": ["x", "y"],
            },
        },
    ]

    # Step 2: Create an MCP registry with the tool descriptors
    registry = MCPToolRegistry(mcp_tools)

    # Step 3: Create an evaluation suite using the registry
    suite = EvalSuite(
        name="MCP Calculator Evaluation",
        system_message="You are a helpful assistant with access to calculator tools.",
        catalog=registry,  # Pass the MCP registry directly
        rubric=EvalRubric(
            fail_threshold=0.8,
            warn_threshold=0.9,
        ),
    )

    # Step 4: Add test cases using tool names (not Python functions!)
    suite.add_case(
        name="Add two numbers",
        user_message="What is 5 plus 3?",
        expected_tool_calls=[
            # Use tool_name (string) instead of func (callable)
            ExpectedToolCall(
                tool_name="calculator_add",
                args={"a": 5, "b": 3},
            )
        ],
        critics=[
            BinaryCritic(critic_field="a", weight=0.5),
            BinaryCritic(critic_field="b", weight=0.5),
        ],
    )

    suite.add_case(
        name="Multiply two numbers",
        user_message="What is 4 times 7?",
        expected_tool_calls=[
            ExpectedToolCall(
                tool_name="calculator_multiply",
                args={"x": 4, "y": 7},
            )
        ],
        critics=[
            BinaryCritic(critic_field="x", weight=0.5),
            BinaryCritic(critic_field="y", weight=0.5),
        ],
    )

    # Step 5: Test with defaults
    suite.add_case(
        name="Add with default value",
        user_message="Add 10 to nothing",
        expected_tool_calls=[
            # The registry will fill in the default for 'b' (0)
            ExpectedToolCall(
                tool_name="calculator_add",
                args={"a": 10},  # 'b' will be filled with default 0
            )
        ],
        critics=[
            BinaryCritic(critic_field="a", weight=1.0),
            # Don't need to check 'b' if we don't care about the default
        ],
    )

    return suite


def load_tools_from_mcp_server() -> None:
    """
    Example helper showing how you might load tools from an actual MCP server.

    NOTE: This is pseudocode showing the pattern - you'd need to implement
    the actual MCP client connection based on your server's transport.
    """
    # For HTTP MCP server:
    # import httpx
    # response = httpx.post(
    #     "http://localhost:8000/mcp",
    #     json={
    #         "jsonrpc": "2.0",
    #         "id": 1,
    #         "method": "tools/list",
    #         "params": {}
    #     }
    # )
    # tools = response.json()["result"]["tools"]
    # return MCPToolRegistry(tools)

    # For stdio MCP server:
    # You'd start the process, send initialize + tools/list via JSON-RPC,
    # and parse the response

    pass


if __name__ == "__main__":
    # Create the evaluation suite
    suite = create_mcp_eval_example()

    print(f"Created evaluation suite with {len(suite.cases)} test cases")
    print("\nTest cases:")
    for case in suite.cases:
        print(f"  - {case.name}")
        for expected in case.expected_tool_calls:
            print(f"    Expected: {expected.name}({expected.args})")

    # To run the evaluation, you would use:
    # arcade evals <directory> --models gpt-4o

    # Or programmatically:
    # import asyncio
    # from openai import AsyncOpenAI
    # client = AsyncOpenAI(api_key="your-key")
    # results = asyncio.run(suite.run(client, "gpt-4o"))
