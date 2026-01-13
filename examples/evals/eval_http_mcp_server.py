"""Remote HTTP/SSE MCP server evaluation.

This example demonstrates loading and evaluating tools from remote MCP servers
accessible via HTTP or Server-Sent Events (SSE).

NOTE: This requires a running HTTP MCP server. Update the configuration below
with your server details.

Run:
    arcade evals examples/evals/eval_http_mcp_server.py \\
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
# CONFIGURATION - Update these for your HTTP MCP server
# =============================================================================

# Example: GitHub Copilot MCP (requires GitHub token)
HTTP_MCP_URL = os.environ.get("MCP_SERVER_URL", "https://api.githubcopilot.com/mcp/")
HTTP_MCP_TOKEN = os.environ.get("GITHUB_PAT", "YOUR_GITHUB_TOKEN_HERE")

# Example: SSE-based MCP server
SSE_MCP_URL = os.environ.get("SSE_MCP_URL", "https://mcp.example.com/sse")

default_rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
)


# =============================================================================
# EVAL SUITE - HTTP MCP Server
# =============================================================================


@tool_eval()
async def eval_http_mcp_server() -> EvalSuite:
    """Evaluate tools from HTTP MCP server."""
    suite = EvalSuite(
        name="HTTP MCP Server Evaluation",
        system_message="You are a helpful assistant with access to remote tools.",
        rubric=default_rubric,
    )

    print("\n  Loading HTTP MCP server...")

    try:
        await asyncio.wait_for(
            suite.add_mcp_server(
                url=HTTP_MCP_URL,
                headers={"Authorization": f"Bearer {HTTP_MCP_TOKEN}"},
                use_sse=False,  # Use HTTP streaming
            ),
            timeout=15.0,
        )
        print("  ✓ HTTP MCP server")
    except asyncio.TimeoutError:
        print("  ✗ HTTP MCP server - timeout")
        return suite
    except Exception as e:
        print(f"  ✗ HTTP MCP server - {type(e).__name__}: {e}")
        return suite

    # Add test cases based on your server's tools
    # Example: If your server has an echo tool
    suite.add_case(
        name="HTTP server tool call",
        user_message="Echo 'Hello from HTTP'",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="echo",  # Adjust to match your server's tool names
                args={"message": "Hello from HTTP"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="message", weight=1.0),
        ],
    )

    return suite


# =============================================================================
# EVAL SUITE - SSE MCP Server
# =============================================================================


@tool_eval()
async def eval_sse_mcp_server() -> EvalSuite:
    """Evaluate tools from SSE MCP server."""
    suite = EvalSuite(
        name="SSE MCP Server Evaluation",
        system_message="You are a helpful assistant with access to SSE-connected tools.",
        rubric=default_rubric,
    )

    print("\n  Loading SSE MCP server...")

    try:
        await asyncio.wait_for(
            suite.add_mcp_server(
                url=SSE_MCP_URL,
                use_sse=True,  # Use SSE transport
                headers={"Accept": "text/event-stream"},
            ),
            timeout=15.0,
        )
        print("  ✓ SSE MCP server")
    except asyncio.TimeoutError:
        print("  ✗ SSE MCP server - timeout")
        return suite
    except Exception as e:
        print(f"  ✗ SSE MCP server - {type(e).__name__}: {e}")
        return suite

    # Add test cases for your SSE server's tools
    suite.add_case(
        name="SSE server tool call",
        user_message="Get status",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="get_status",  # Adjust to match your server's tools
                args={},
            )
        ],
        critics=[],
    )

    return suite
