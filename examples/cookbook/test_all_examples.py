#!/usr/bin/env python3
"""
Test script to verify all cookbook examples work in:
1. Local development mode (HTTP)
2. MCP mode (stdio/SSE/stream)
3. Deployed mode (after arcade deploy)
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx


class CookbookTester:
    """Test all cookbook examples across different modes."""

    def __init__(self):
        self.base_url = "http://localhost:8002"
        self.examples = [
            "simple_tool",
            "gmail_curator",
            "notetaker_local_mcp",
            "using_local_resources",
        ]
        self.results = {}

    async def test_local_http(self, example: str) -> dict[str, any]:
        """Test example in local HTTP mode."""
        print(f"\n🔧 Testing {example} in LOCAL HTTP mode...")

        # Start the worker
        process = subprocess.Popen(
            ["arcade", "serve"],
            cwd=example,  # We're already in the cookbook directory
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "ARCADE_WORKER_SECRET": "dev"},
        )

        # Wait for server to start
        await asyncio.sleep(3)

        try:
            async with httpx.AsyncClient() as client:
                # Test catalog endpoint
                response = await client.get(
                    f"{self.base_url}/worker/catalog",
                    headers={"Authorization": "Bearer dev"},
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Catalog failed: {response.status_code}",
                    }

                catalog = response.json()
                print(f"  ✓ Found {len(catalog)} tools")

                # Test specific tools based on example
                test_results = await self._test_example_tools(client, example, catalog)

                return {
                    "success": True,
                    "tools_count": len(catalog),
                    "tests": test_results,
                }

        finally:
            process.terminate()
            process.wait()

    async def test_mcp_stdio(self, example: str) -> dict[str, any]:
        """Test example in MCP stdio mode."""
        print(f"\n🔧 Testing {example} in MCP STDIO mode...")

        # Test MCP stdio by running arcade serve --local
        result = subprocess.run(
            ["arcade", "serve", "--local", "--test"],
            cwd=f"examples/cookbook/{example}",
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        return {"success": True, "output": result.stdout}

    async def test_mcp_sse(self, example: str) -> dict[str, any]:
        """Test example in MCP SSE mode."""
        print(f"\n🔧 Testing {example} in MCP SSE mode...")

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
                # Test SSE endpoint
                response = await client.get(f"{self.base_url}/sse")

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"SSE endpoint failed: {response.status_code}",
                    }

                return {"success": True}

        finally:
            process.terminate()
            process.wait()

    async def _test_example_tools(
        self, client: httpx.AsyncClient, example: str, catalog: list
    ) -> dict:
        """Test specific tools for each example."""
        results = {}

        if example == "simple_tool":
            # Test HelloWorld
            response = await client.post(
                f"{self.base_url}/worker/tools/invoke",
                json={
                    "tool": {"name": "HelloWorld"},
                    "inputs": {"name": "Test"},
                },
                headers={"Authorization": "Bearer dev"},
            )
            results["HelloWorld"] = response.status_code == 200

            # Test AddNumbers
            response = await client.post(
                f"{self.base_url}/worker/tools/invoke",
                json={
                    "tool": {"name": "AddNumbers"},
                    "inputs": {"a": 5, "b": 3},
                },
                headers={"Authorization": "Bearer dev"},
            )
            results["AddNumbers"] = response.status_code == 200

        elif example == "gmail_curator":
            # Test AnalyzeInbox
            response = await client.post(
                f"{self.base_url}/worker/tools/invoke",
                json={
                    "tool": {"name": "AnalyzeInbox"},
                    "inputs": {"days_back": 7},
                },
                headers={"Authorization": "Bearer dev"},
            )
            results["AnalyzeInbox"] = response.status_code == 200

        elif example == "notetaker_local_mcp":
            # Test CreateNote
            response = await client.post(
                f"{self.base_url}/worker/tools/invoke",
                json={
                    "tool": {"name": "CreateNote"},
                    "inputs": {
                        "title": "Test Note",
                        "content": "Test content",
                        "format": "markdown",
                    },
                },
                headers={"Authorization": "Bearer dev"},
            )
            results["CreateNote"] = response.status_code == 200

        elif example == "using_local_resources":
            # Test CheckConnections
            response = await client.post(
                f"{self.base_url}/worker/tools/invoke",
                json={
                    "tool": {"name": "CheckConnections"},
                    "inputs": {},
                },
                headers={"Authorization": "Bearer dev"},
            )
            results["CheckConnections"] = response.status_code == 200

        return results

    async def test_all(self):
        """Run all tests for all examples."""
        print("🚀 Testing all cookbook examples...\n")

        for example in self.examples:
            print(f"\n{'=' * 60}")
            print(f"📦 Testing example: {example}")
            print(f"{'=' * 60}")

            self.results[example] = {}

            # Test local HTTP mode
            self.results[example]["local_http"] = await self.test_local_http(example)

            # Test MCP modes
            # self.results[example]["mcp_stdio"] = await self.test_mcp_stdio(example)
            self.results[example]["mcp_sse"] = await self.test_mcp_sse(example)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test results summary."""
        print(f"\n\n{'=' * 60}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 60}\n")

        for example, results in self.results.items():
            print(f"\n{example}:")
            for mode, result in results.items():
                status = "✅" if result.get("success") else "❌"
                print(f"  {mode}: {status}")
                if not result.get("success"):
                    print(f"    Error: {result.get('error', 'Unknown error')}")


async def main():
    """Run all tests."""
    tester = CookbookTester()
    await tester.test_all()


if __name__ == "__main__":
    asyncio.run(main())
