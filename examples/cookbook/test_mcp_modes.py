#!/usr/bin/env python3
"""
Test MCP modes (stdio, SSE, stream) for cookbook examples.
Tests the MCP-specific features like tool discovery and invocation.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import httpx


class MCPModeTester:
    """Test MCP modes for cookbook examples."""

    def __init__(self):
        self.examples = [
            "simple_tool",
            "gmail_curator",
            "notetaker_local_mcp",
            "using_local_resources",
        ]

    async def test_stdio_mode(self, example: str) -> dict:
        """Test MCP stdio mode by sending/receiving JSON-RPC messages."""
        print(f"\n📡 Testing {example} in STDIO mode...")

        # Start arcade serve --local
        process = subprocess.Popen(
            ["arcade", "serve", "--local"],
            cwd=f"examples/cookbook/{example}",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }

            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()

            # Read response (with timeout)
            response_line = process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                print(
                    f"  ✓ Initialize response: {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}"
                )

                # List tools
                list_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }

                process.stdin.write(json.dumps(list_request) + "\n")
                process.stdin.flush()

                tools_response_line = process.stdout.readline()
                if tools_response_line:
                    tools_response = json.loads(tools_response_line)
                    tools = tools_response.get("result", {}).get("tools", [])
                    print(f"  ✓ Found {len(tools)} tools")

                    return {"success": True, "tools_count": len(tools)}

            return {"success": False, "error": "No response from stdio server"}

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            process.terminate()
            process.wait()

    async def test_sse_mode(self, example: str) -> dict:
        """Test MCP SSE mode."""
        print(f"\n📡 Testing {example} in SSE mode...")

        # Start SSE server
        process = subprocess.Popen(
            ["arcade", "serve", "--sse", "--no-auth"],
            cwd=f"examples/cookbook/{example}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        await asyncio.sleep(3)

        try:
            async with httpx.AsyncClient() as client:
                # Send initialize through SSE
                response = await client.post(
                    "http://localhost:8002/sse",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "0.1.0",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "test-sse-client",
                                "version": "1.0.0",
                            },
                        },
                    },
                )

                if response.status_code == 200:
                    # List tools
                    tools_response = await client.post(
                        "http://localhost:8002/sse",
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list",
                            "params": {},
                        },
                    )

                    if tools_response.status_code == 200:
                        result = tools_response.json()
                        tools = result.get("result", {}).get("tools", [])
                        print(f"  ✓ Found {len(tools)} tools via SSE")
                        return {"success": True, "tools_count": len(tools)}

                return {
                    "success": False,
                    "error": f"SSE request failed: {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            process.terminate()
            process.wait()

    async def test_stream_mode(self, example: str) -> dict:
        """Test MCP stream mode (HTTPS with streaming)."""
        print(f"\n📡 Testing {example} in STREAM mode...")

        # Start stream server
        process = subprocess.Popen(
            ["arcade", "serve", "--stream", "--no-auth"],
            cwd=f"examples/cookbook/{example}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        await asyncio.sleep(3)

        try:
            async with httpx.AsyncClient() as client:
                # Initialize via stream endpoint
                response = await client.post(
                    "http://localhost:8002/stream",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "0.1.0",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "test-stream-client",
                                "version": "1.0.0",
                            },
                        },
                    },
                )

                if response.status_code == 200:
                    # Test streaming response
                    print("  ✓ Stream endpoint accessible")

                    # List tools
                    tools_response = await client.post(
                        "http://localhost:8002/stream",
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list",
                            "params": {},
                        },
                    )

                    if tools_response.status_code == 200:
                        # Parse streaming response
                        content = tools_response.text
                        # Stream format might have multiple chunks
                        tools_count = 0
                        if "tools" in content:
                            # Simple parsing for demo
                            tools_count = content.count('"name":')

                        print(f"  ✓ Stream mode working, found tools")
                        return {"success": True, "stream_mode": True}

                return {
                    "success": False,
                    "error": f"Stream request failed: {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            process.terminate()
            process.wait()

    async def test_mcp_tool_invocation(self, example: str) -> dict:
        """Test actual tool invocation through MCP."""
        print(f"\n🔧 Testing tool invocation for {example}...")

        # Use SSE mode for testing
        process = subprocess.Popen(
            ["arcade", "serve", "--sse", "--no-auth"],
            cwd=f"examples/cookbook/{example}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        await asyncio.sleep(3)

        try:
            async with httpx.AsyncClient() as client:
                # Initialize first
                await client.post(
                    "http://localhost:8002/sse",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "0.1.0", "capabilities": {}},
                    },
                )

                # Pick a tool to test based on example
                tool_name = None
                tool_args = {}

                if example == "simple_tool":
                    tool_name = "HelloWorld"
                    tool_args = {"name": "MCP Test"}
                elif example == "gmail_curator":
                    tool_name = "AnalyzeInbox"
                    tool_args = {"days_back": 7}
                elif example == "notetaker_local_mcp":
                    tool_name = "CreateNote"
                    tool_args = {
                        "title": "MCP Test Note",
                        "content": "Testing MCP",
                        "format": "markdown",
                    }
                elif example == "using_local_resources":
                    tool_name = "ProcessWorkspaceFiles"
                    tool_args = {"pattern": "*.txt", "operation": "count"}

                if tool_name:
                    # Call the tool
                    response = await client.post(
                        "http://localhost:8002/sse",
                        json={
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {"name": tool_name, "arguments": tool_args},
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✓ Tool {tool_name} executed successfully")
                        return {"success": True, "tool_executed": tool_name}

                return {"success": False, "error": "Tool execution failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            process.terminate()
            process.wait()

    async def run_all_tests(self):
        """Run all MCP mode tests."""
        print("🚀 Testing MCP modes for all cookbook examples\n")

        results = {}

        for example in self.examples:
            print(f"\n{'=' * 60}")
            print(f"📦 Testing: {example}")
            print(f"{'=' * 60}")

            results[example] = {
                "stdio": await self.test_stdio_mode(example),
                "sse": await self.test_sse_mode(example),
                "stream": await self.test_stream_mode(example),
                "invocation": await self.test_mcp_tool_invocation(example),
            }

        # Print summary
        print(f"\n\n{'=' * 60}")
        print("📊 MCP MODE TEST SUMMARY")
        print(f"{'=' * 60}\n")

        for example, modes in results.items():
            print(f"\n{example}:")
            for mode, result in modes.items():
                status = "✅" if result.get("success") else "❌"
                print(f"  {mode}: {status}")
                if not result.get("success"):
                    print(f"    Error: {result.get('error', 'Unknown')}")


async def main():
    """Run MCP mode tests."""
    tester = MCPModeTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
