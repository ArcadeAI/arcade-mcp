"""Local stdio MCP server evaluation.

This example demonstrates loading and evaluating tools from a local MCP server
running as a subprocess via stdio (standard input/output).

Run:
    arcade evals examples/evals/eval_stdio_mcp_server.py \\
        -p openai:gpt-4o \\
        -k openai:YOUR_KEY \\
        -o results.html -d
"""

import asyncio
import os

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedMCPToolCall,
    tool_eval,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Path to the simple echo server
EXAMPLES_DIR = os.path.dirname(os.path.dirname(__file__))
SIMPLE_SERVER_PATH = os.path.join(EXAMPLES_DIR, "mcp_servers", "simple")

# Stdio server command
SIMPLE_SERVER_COMMAND = [
    "uv",
    "run",
    "--directory",
    SIMPLE_SERVER_PATH,
    "simple",
]

default_rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
)


# =============================================================================
# EVAL SUITE
# =============================================================================


@tool_eval()
async def eval_stdio_simple_server() -> EvalSuite:
    """Evaluate simple echo server via stdio."""
    suite = EvalSuite(
        name="Stdio MCP Server - Simple Echo",
        system_message="You are a helpful assistant that can echo messages.",
        rubric=default_rubric,
    )

    print("\n  Loading stdio MCP server (simple)...")

    try:
        await asyncio.wait_for(
            suite.add_mcp_stdio_server(
                command=SIMPLE_SERVER_COMMAND,
                env={"PYTHONUNBUFFERED": "1"},
            ),
            timeout=15.0,
        )
        print("  ✓ Simple MCP server (stdio)")
    except asyncio.TimeoutError:
        print("  ✗ Simple MCP server (stdio) - timeout")
        return suite
    except Exception as e:
        print(f"  ✗ Simple MCP server (stdio) - {type(e).__name__}: {e}")
        return suite

    # Test Case 1: Simple echo
    suite.add_case(
        name="Echo - Hello",
        user_message="Echo the word 'Hello'",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="echo",
                args={"message": "Hello"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="message", weight=1.0),
        ],
    )

    # Test Case 2: Echo with punctuation
    suite.add_case(
        name="Echo - Hello, World!",
        user_message="Echo this: Hello, World!",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="echo",
                args={"message": "Hello, World!"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="message", weight=1.0),
        ],
    )

    # Test Case 3: Echo longer phrase
    suite.add_case(
        name="Echo - Longer phrase",
        user_message="Please echo: The quick brown fox",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="echo",
                args={"message": "The quick brown fox"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="message", weight=1.0),
        ],
    )

    return suite
