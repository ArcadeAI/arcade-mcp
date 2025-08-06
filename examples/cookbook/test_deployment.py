#!/usr/bin/env python3
"""
Test script to verify cookbook examples work after deployment with arcade deploy.
This script tests using the Arcade Python client.
"""

import asyncio
import os
from pathlib import Path

# This would be imported after pip install arcade-ai
# from arcade import Arcade


async def test_deployed_example(toolkit_name: str, api_key: str):
    """Test a deployed toolkit using the Arcade client."""
    print(f"\n🚀 Testing deployed {toolkit_name}...")

    # This is how you'd use it with the real client:
    """
    arcade = Arcade(api_key=api_key)

    # List available tools
    tools = await arcade.tools.list(toolkit=toolkit_name)
    print(f"  ✓ Found {len(tools)} tools")

    # Test specific tools based on example
    if toolkit_name == "simple-tools":
        result = await arcade.tools.run(
            tool_name="HelloWorld",
            toolkit=toolkit_name,
            inputs={"name": "Production Test"}
        )
        print(f"  ✓ HelloWorld result: {result}")

    elif toolkit_name == "gmail-curator":
        result = await arcade.tools.run(
            tool_name="AnalyzeInbox",
            toolkit=toolkit_name,
            inputs={"days_back": 7}
        )
        print(f"  ✓ AnalyzeInbox result: {result}")
    """

    print(f"  ℹ️  To test after deployment:")
    print(f"     1. cd examples/cookbook/{toolkit_name.replace('-', '_')}")
    print(f"     2. arcade deploy")
    print(f"     3. Use the Arcade client with your API key")


def generate_deployment_guide():
    """Generate deployment guide for each example."""
    examples = {
        "simple_tool": "simple-tools",
        "gmail_curator": "gmail-curator",
        "notetaker_local_mcp": "notetaker-mcp",
        "using_local_resources": "local-resources",
    }

    print("\n📚 DEPLOYMENT GUIDE FOR COOKBOOK EXAMPLES")
    print("=" * 60)

    for dir_name, toolkit_id in examples.items():
        print(f"\n### {dir_name}")
        print(f"Toolkit ID: {toolkit_id}")
        print("\nDeployment steps:")
        print(f"1. cd examples/cookbook/{dir_name}")
        print("2. arcade deploy")
        print("\nPython client usage:")
        print("```python")
        print("from arcade import Arcade")
        print("")
        print('arcade = Arcade(api_key="your-api-key")')
        print(f'tools = await arcade.tools.list(toolkit="{toolkit_id}")')
        print("")

        # Example tool usage for each
        if dir_name == "simple_tool":
            print("result = await arcade.tools.run(")
            print('    tool_name="HelloWorld",')
            print(f'    toolkit="{toolkit_id}",')
            print('    inputs={"name": "World"}')
            print(")")

        elif dir_name == "gmail_curator":
            print("result = await arcade.tools.run(")
            print('    tool_name="AnalyzeInbox",')
            print(f'    toolkit="{toolkit_id}",')
            print('    inputs={"days_back": 30}')
            print(")")

        elif dir_name == "notetaker_local_mcp":
            print("result = await arcade.tools.run(")
            print('    tool_name="CreateNote",')
            print(f'    toolkit="{toolkit_id}",')
            print("    inputs={")
            print('        "title": "My Note",')
            print('        "content": "Note content",')
            print('        "format": "markdown"')
            print("    }")
            print(")")

        elif dir_name == "using_local_resources":
            print("# Note: This toolkit requires secrets to be configured")
            print("result = await arcade.tools.run(")
            print('    tool_name="CheckConnections",')
            print(f'    toolkit="{toolkit_id}",')
            print("    inputs={}")
            print(")")

        print("```")


def check_deployment_readiness():
    """Check if examples are ready for deployment."""
    print("\n🔍 CHECKING DEPLOYMENT READINESS")
    print("=" * 60)

    examples_dir = Path("examples/cookbook")
    issues = []

    for example in [
        "simple_tool",
        "gmail_curator",
        "notetaker_local_mcp",
        "using_local_resources",
    ]:
        example_path = examples_dir / example
        print(f"\n{example}:")

        # Check worker.toml
        worker_toml = example_path / "worker.toml"
        if not worker_toml.exists():
            issues.append(f"{example}: Missing worker.toml")
            print("  ❌ Missing worker.toml")
        else:
            print("  ✅ worker.toml found")

            # Check toolkit ID in worker.toml
            content = worker_toml.read_text()
            if 'id = "' in content:
                print("  ✅ Toolkit ID configured")
            else:
                issues.append(f"{example}: Missing toolkit ID in worker.toml")
                print("  ❌ Missing toolkit ID")

        # Check toolkit directory
        toolkit_dir = example_path / "toolkit"
        if not toolkit_dir.exists():
            issues.append(f"{example}: Missing toolkit directory")
            print("  ❌ Missing toolkit directory")
        else:
            print("  ✅ toolkit directory found")

            # Check for Python files
            py_files = list(toolkit_dir.glob("*.py"))
            if not py_files:
                issues.append(f"{example}: No Python files in toolkit directory")
                print("  ❌ No Python files in toolkit")
            else:
                print(f"  ✅ {len(py_files)} Python files found")

    if issues:
        print(f"\n⚠️  Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ All examples are deployment ready!")

    return len(issues) == 0


if __name__ == "__main__":
    print("🎯 Arcade Cookbook Deployment Testing\n")

    # Check deployment readiness
    ready = check_deployment_readiness()

    # Generate deployment guide
    generate_deployment_guide()

    # Provide testing instructions
    print("\n\n📋 MANUAL TESTING INSTRUCTIONS")
    print("=" * 60)
    print("\n1. Deploy each example:")
    print("   arcade deploy")
    print("\n2. Test with Python client:")
    print("   pip install arcade-ai")
    print("   python test_deployment.py")
    print("\n3. Verify in Arcade dashboard:")
    print("   https://app.arcade-ai.com/toolkits")
