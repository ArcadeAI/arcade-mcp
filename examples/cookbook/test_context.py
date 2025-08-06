#!/usr/bin/env python3
"""
Test script to verify ToolContext is properly passed in both local and deployed settings.
"""

import asyncio
import json
from pathlib import Path

import httpx

# Test the simple_tool example
BASE_URL = "http://localhost:8002"


async def test_tool_context():
    """Test that ToolContext is properly populated."""
    async with httpx.AsyncClient() as client:
        # Test the GetCurrentTime tool which uses ctx
        response = await client.post(
            f"{BASE_URL}/worker/tools/invoke",
            json={
                "tool": {
                    "name": "GetCurrentTime",
                    "toolkit": {"name": "simple_tools", "version": "0.1.0"},
                },
                "inputs": {"timezone": "UTC"},
            },
            headers={"Authorization": "Bearer dev"},
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")

            # Check if user_id was included in the response
            if "output" in result and "value" in result["output"]:
                output_value = result["output"]["value"]
                print(f"\nOutput value: {output_value}")

                # The GetCurrentTime tool includes user_id in its output
                if "user: " in output_value:
                    user_part = output_value.split("user: ")[-1].strip(")")
                    print(f"User ID from context: {user_part}")

                    # Check if it matches what's in worker.toml
                    worker_toml = Path("simple_tool/worker.toml")
                    if worker_toml.exists():
                        import toml

                        config = toml.load(worker_toml)
                        expected_user = (
                            config.get("worker", [{}])[0]
                            .get("config", {})
                            .get("local_context", {})
                            .get("user_id", "anonymous")
                        )

                        if user_part == expected_user:
                            print(
                                f"✅ SUCCESS: Context user_id matches worker.toml: {expected_user}"
                            )
                        else:
                            print(
                                f"❌ FAIL: Context user_id '{user_part}' doesn't match worker.toml '{expected_user}'"
                            )
                else:
                    print("❌ FAIL: No user information found in output")
        else:
            print(f"Error: {response.text}")


async def test_catalog():
    """Test that the catalog endpoint works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/worker/catalog", headers={"Authorization": "Bearer dev"}
        )

        print(f"\nCatalog Status: {response.status_code}")
        if response.status_code == 200:
            catalog = response.json()
            print(f"Tools found: {len(catalog)}")
            for tool in catalog:
                print(f"  - {tool['name']}")


if __name__ == "__main__":
    print("Testing ToolContext passing in Arcade worker...\n")
    asyncio.run(test_catalog())
    asyncio.run(test_tool_context())
