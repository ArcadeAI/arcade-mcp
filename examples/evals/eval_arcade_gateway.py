"""Arcade Gateway evaluation - Loading tools from cloud-hosted toolkits.

This example demonstrates loading and evaluating tools from Arcade Gateway,
which provides access to pre-built toolkits (Math, GitHub, Slack, Linear, etc.).

Prerequisites:
    1. Get your API key: https://docs.arcade.dev/en/get-started/setup/api-keys
    2. Create an MCP Gateway at https://portal.arcade.dev
    3. Add toolkits to your gateway (e.g., Math, GitHub, Slack)
    4. Get your ARCADE_API_KEY and ARCADE_USER_ID from the portal

    Full setup guide: https://docs.arcade.dev/en/guides/create-tools/mcp-gateways

Run:
    # Set environment variables
    export ARCADE_API_KEY=your_arcade_key
    export ARCADE_USER_ID=your_user_id

    # Run the evaluation
    arcade evals examples/evals/eval_arcade_gateway.py \\
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

ARCADE_API_KEY = os.environ.get("ARCADE_API_KEY", "YOUR_ARCADE_API_KEY_HERE")
ARCADE_USER_ID = os.environ.get("ARCADE_USER_ID", "YOUR_USER_ID_HERE")

default_rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
)


# =============================================================================
# EVAL SUITE
# =============================================================================


@tool_eval()
async def eval_arcade_gateway() -> EvalSuite:
    """Evaluate Math toolkit from Arcade Gateway."""
    suite = EvalSuite(
        name="Arcade Gateway - Math Toolkit",
        system_message="You are a helpful math assistant. Use tools to perform calculations.",
        rubric=default_rubric,
    )

    print("\n  Loading Arcade Gateway...")

    try:
        await asyncio.wait_for(
            suite.add_arcade_gateway(
                gateway_slug="Math",
                arcade_api_key=ARCADE_API_KEY,
                arcade_user_id=ARCADE_USER_ID,
            ),
            timeout=10.0,
        )
        print("  ✓ Arcade Gateway (Math toolkit)")
    except asyncio.TimeoutError:
        print("  ✗ Arcade Gateway - timeout")
        return suite
    except Exception as e:
        print(f"  ✗ Arcade Gateway - {type(e).__name__}: {e}")
        return suite

    # Test Case 1: Simple addition
    suite.add_case(
        name="Simple addition - 10 + 5",
        user_message="What is 10 plus 5?",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="Math_Add",
                args={"a": 10, "b": 5},
            )
        ],
        critics=[
            BinaryCritic(critic_field="a", weight=0.5),
            BinaryCritic(critic_field="b", weight=0.5),
        ],
    )

    # Test Case 2: Larger numbers
    suite.add_case(
        name="Addition - 123 + 456",
        user_message="Calculate 123 + 456",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="Math_Add",
                args={"a": 123, "b": 456},
            )
        ],
        critics=[
            BinaryCritic(critic_field="a", weight=0.5),
            BinaryCritic(critic_field="b", weight=0.5),
        ],
    )

    # Test Case 3: Conversational context
    suite.add_case(
        name="Addition with context",
        user_message="Now add them together",
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
        additional_messages=[
            {"role": "user", "content": "I have two numbers: 50 and 25"},
            {"role": "assistant", "content": "Great! I'll remember those numbers."},
        ],
    )

    return suite
