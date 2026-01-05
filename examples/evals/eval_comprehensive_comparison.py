"""Comprehensive comparison across multiple tool sources.

This example demonstrates comparative evaluations across different sources:
- Arcade Gateway (cloud toolkits)
- Local stdio MCP servers
- Dict-based tool definitions (baseline)

Run:
    arcade evals examples/evals/eval_comprehensive_comparison.py \\
        -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \\
        -k openai:YOUR_KEY -k anthropic:YOUR_KEY \\
        -o comparison.html -d
"""

import asyncio
import os

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedMCPToolCall,
    MCPToolDefinition,
    SimilarityCritic,
    tool_eval,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ARCADE_API_KEY = os.environ.get("ARCADE_API_KEY", "YOUR_ARCADE_API_KEY_HERE")
ARCADE_USER_ID = os.environ.get("ARCADE_USER_ID", "YOUR_USER_ID_HERE")

EXAMPLES_DIR = os.path.dirname(os.path.dirname(__file__))
SIMPLE_SERVER_PATH = os.path.join(EXAMPLES_DIR, "mcp_servers", "simple")

SIMPLE_SERVER_COMMAND = [
    "uv",
    "run",
    "--directory",
    SIMPLE_SERVER_PATH,
    "simple",
]

# Baseline dict tool (for comparison)
DICT_SEARCH: MCPToolDefinition = {
    "name": "search",
    "description": "Search for information",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    },
}

default_rubric = EvalRubric(
    fail_threshold=0.6,
    warn_threshold=0.8,
    fail_on_tool_selection=False,
)


# =============================================================================
# EVAL SUITE
# =============================================================================


@tool_eval()
async def eval_comprehensive_comparison() -> EvalSuite:
    """Compare tool performance across multiple sources."""
    suite = EvalSuite(
        name="Multi-Source Comparative Evaluation",
        system_message="You are a helpful assistant with various tools available.",
        rubric=default_rubric,
    )

    loaded_tracks: list[str] = []

    # Always add baseline dict tools
    suite.add_tool_definitions([DICT_SEARCH], track="dict_baseline")
    loaded_tracks.append("dict_baseline")

    print("\n  Loading tool sources...")

    # Load from Arcade Gateway
    try:
        print("  → Loading Arcade Gateway (Math)...")
        await asyncio.wait_for(
            suite.add_arcade_gateway(
                gateway_slug="Math",
                arcade_api_key=ARCADE_API_KEY,
                arcade_user_id=ARCADE_USER_ID,
                track="arcade_gateway",
            ),
            timeout=10.0,
        )
        loaded_tracks.append("arcade_gateway")
        print("  ✓ Arcade Gateway")
    except asyncio.TimeoutError:
        print("  ✗ Arcade Gateway - timeout")
    except Exception as e:
        print(f"  ✗ Arcade Gateway - {type(e).__name__}: {e}")

    # Load from stdio MCP server
    try:
        print("  → Loading stdio MCP server (simple)...")
        await asyncio.wait_for(
            suite.add_mcp_stdio_server(
                command=SIMPLE_SERVER_COMMAND,
                env={"PYTHONUNBUFFERED": "1"},
                track="stdio_simple",
            ),
            timeout=15.0,
        )
        loaded_tracks.append("stdio_simple")
        print("  ✓ Stdio MCP server")
    except asyncio.TimeoutError:
        print("  ✗ Stdio MCP server - timeout")
    except Exception as e:
        print(f"  ✗ Stdio MCP server - {type(e).__name__}: {e}")

    print(f"\n  Loaded tracks: {loaded_tracks}\n")

    # =========================================================================
    # TEST CASE 1: Math operation (Arcade Gateway vs baseline)
    # =========================================================================

    if "arcade_gateway" in loaded_tracks:
        case1 = suite.add_comparative_case(
            name="Math addition - Gateway vs Baseline",
            user_message="What is 15 plus 27?",
        )
        case1.for_track(
            "arcade_gateway",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="Math_Add",
                    args={"a": 15, "b": 27},
                )
            ],
            critics=[
                BinaryCritic(critic_field="a", weight=0.5),
                BinaryCritic(critic_field="b", weight=0.5),
            ],
        )
        case1.for_track(
            "dict_baseline",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="search",
                    args={"query": "15 plus 27"},
                )
            ],
            critics=[SimilarityCritic(critic_field="query", weight=1.0, similarity_threshold=0.3)],
        )

    # =========================================================================
    # TEST CASE 2: Echo operation (stdio vs baseline)
    # =========================================================================

    if "stdio_simple" in loaded_tracks:
        case2 = suite.add_comparative_case(
            name="Echo message - Stdio vs Baseline",
            user_message="Echo 'Hello World'",
        )
        case2.for_track(
            "stdio_simple",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="echo",
                    args={"message": "Hello World"},
                )
            ],
            critics=[
                BinaryCritic(critic_field="message", weight=1.0),
            ],
        )
        case2.for_track(
            "dict_baseline",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="search",
                    args={"query": "Hello World"},
                )
            ],
            critics=[SimilarityCritic(critic_field="query", weight=1.0, similarity_threshold=0.5)],
        )

    # =========================================================================
    # TEST CASE 3: Conversational context
    # =========================================================================

    if "arcade_gateway" in loaded_tracks:
        case3 = suite.add_comparative_case(
            name="Math with context",
            user_message="Now add them together",
            additional_messages=[
                {"role": "user", "content": "I have two numbers: 50 and 25"},
                {"role": "assistant", "content": "I'll remember those numbers."},
            ],
        )
        case3.for_track(
            "arcade_gateway",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="Math_Add",
                    args={"a": 50, "b": 25},
                )
            ],
            critics=[
                BinaryCritic(critic_field="a", weight=0.5),
                BinaryCritic(critic_field="b", weight=0.5),
            ],
        )
        case3.for_track(
            "dict_baseline",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="search",
                    args={"query": "50 plus 25"},
                )
            ],
            critics=[SimilarityCritic(critic_field="query", weight=1.0, similarity_threshold=0.3)],
        )

    return suite
