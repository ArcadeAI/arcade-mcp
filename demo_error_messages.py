#!/usr/bin/env python3
"""
Demonstration of Improved Error Messages

This script demonstrates the actionable error messages by simulating
the errors and showing what users would see.
"""

import sys


def demo_missing_secrets_error():
    """Demonstrate missing secrets error message."""
    print("=" * 70)
    print("SCENARIO: Tool requires secrets that aren't configured")
    print("=" * 70)

    # Simulate the error
    missing_secrets = ["API_KEY", "SECRET_TOKEN"]
    missing_secrets_str = "', '".join(missing_secrets)
    env_examples = "\n     ".join([f"{key}=your_value_here" for key in missing_secrets])
    export_examples = "\n     ".join([f"export {key}=your_value_here" for key in missing_secrets])

    error_message = (
        f"✗ Missing secrets: '{missing_secrets_str}'\n\n"
        f"  Tool 'fetch_data' requires these secrets but they are not configured."
    )

    fix_instructions = (
        f"The MCP server cannot execute the 'fetch_data' tool because "
        f"these required secrets are missing: {missing_secrets_str}\n\n"
        f"To fix, tell the developer to either:\n"
        f"  1. Add to .env file in the server's working directory:\n"
        f"     {env_examples}\n\n"
        f"  2. Set as environment variables:\n"
        f"     {export_examples}\n\n"
        f"Then restart the MCP server for changes to take effect."
    )

    print("\nUser sees:")
    print(error_message)
    print("\nLLM receives:")
    print(fix_instructions)
    print()


def demo_missing_api_key_error():
    """Demonstrate missing Arcade API key error."""
    print("=" * 70)
    print("SCENARIO: Tool requires authorization but API key not configured")
    print("=" * 70)

    error_message = (
        "✗ Missing Arcade API key\n\n"
        "  Tool 'send_email' requires authorization but no API key is configured."
    )

    fix_instructions = (
        "The MCP server cannot execute the 'send_email' tool because it requires authorization "
        "but the Arcade API key is not configured.\n\n"
        "To fix, tell the developer to either:\n"
        "  1. Run the CLI command:\n"
        "     arcade login\n\n"
        "  2. Set environment variable:\n"
        "     export ARCADE_API_KEY=your_api_key_here\n\n"
        "Then restart the MCP server for changes to take effect."
    )

    print("\nUser sees:")
    print(error_message)
    print("\nLLM receives:")
    print(fix_instructions)
    print()


def demo_authorization_required():
    """Demonstrate OAuth authorization required."""
    print("=" * 70)
    print("SCENARIO: User needs to authorize access to their account")
    print("=" * 70)

    auth_url = "https://accounts.google.com/o/oauth2/auth?client_id=..."

    error_message = (
        "→ Authorization required\n\n"
        "  Tool 'read_emails' needs user permission to access their account."
    )

    fix_instructions = (
        "The 'read_emails' tool requires user authorization before it can execute.\n\n"
        f"To authorize, show this link to the user:\n"
        f"{auth_url}\n\n"
        "Once the user completes the OAuth2 flow, the tool can be executed."
    )

    print("\nUser sees:")
    print(error_message)
    print("\nLLM receives:")
    print(fix_instructions)
    print()


def demo_invalid_log_level():
    """Demonstrate configuration validation error."""
    print("=" * 70)
    print("SCENARIO: Invalid configuration value")
    print("=" * 70)

    error_message = (
        "✗ Invalid log level: 'TRACE'\n\n"
        "  Valid options: DEBUG, INFO, WARNING, ERROR, CRITICAL\n\n"
        "To fix, set MCP_MIDDLEWARE_LOG_LEVEL to one of the valid options:\n"
        "  export MCP_MIDDLEWARE_LOG_LEVEL=INFO\n\n"
        "Or in .env file:\n"
        "  MCP_MIDDLEWARE_LOG_LEVEL=INFO"
    )

    print("\nUser sees:")
    print(error_message)
    print()


def demo_invalid_app_name():
    """Demonstrate app name validation error."""
    print("=" * 70)
    print("SCENARIO: Invalid MCPApp name")
    print("=" * 70)

    error_message = (
        "✗ Invalid app name: 'my-app'\n\n"
        "  App names must contain only alphanumeric characters and underscores.\n\n"
        "Valid examples:\n"
        "  - my_app\n"
        "  - MyApp\n"
        "  - app123\n\n"
        "Invalid characters found in: 'my-app'"
    )

    print("\nUser sees:")
    print(error_message)
    print()


def demo_tool_not_found():
    """Demonstrate tool not found error."""
    print("=" * 70)
    print("SCENARIO: Calling a non-existent tool")
    print("=" * 70)

    error_message = (
        "✗ Tool not found: 'send_sms'\n\n"
        "  The requested tool does not exist in the catalog.\n\n"
        "To fix:\n"
        "  1. List available tools with tools/list\n"
        "  2. Check for typos in the tool name\n"
        "  3. Ensure the tool package is loaded correctly"
    )

    print("\nUser sees:")
    print(error_message)
    print()


def demo_no_tools_error():
    """Demonstrate no tools found on startup."""
    print("=" * 70)
    print("SCENARIO: Server starts with no tools")
    print("=" * 70)

    error_message = (
        "✗ No tools found\n\n"
        "  The server cannot start without any tools.\n\n"
        "To fix:\n"
        "  1. Create Python files with @tool decorated functions\n"
        "  2. Ensure ARCADE_MCP_TOOL_PACKAGE points to your tools package\n"
        "  3. Or set ARCADE_MCP_DISCOVER_INSTALLED=true to discover installed toolkits\n\n"
        "Example tool:\n"
        "  from arcade.sdk import tool\n\n"
        "  @tool\n"
        "  def hello() -> str:\n"
        "      return 'Hello, world!'"
    )

    print("\nUser sees:")
    print(error_message)
    print()


def demo_session_not_available():
    """Demonstrate context used outside request."""
    print("=" * 70)
    print("SCENARIO: Using context outside of a request handler")
    print("=" * 70)

    error_message = (
        "✗ Session not available for sampling\n\n"
        "  Cannot create messages without an active MCP session.\n\n"
        "Possible causes:\n"
        "  1. Context is being used outside of a request handler\n"
        "  2. Session has not been initialized\n"
        "  3. Session was closed\n\n"
        "To fix:\n"
        "  Only call context.sampling.create_message() from within a tool or request handler."
    )

    print("\nUser sees:")
    print(error_message)
    print()


def demo_invalid_elicitation_schema():
    """Demonstrate schema validation error."""
    print("=" * 70)
    print("SCENARIO: Invalid schema for user elicitation")
    print("=" * 70)

    error_message = (
        "✗ Unsupported type for property 'preferences': 'object'\n\n"
        "  MCP elicitation only supports primitive types.\n\n"
        "Allowed types:\n"
        "  - string\n"
        "  - number\n"
        "  - integer\n"
        "  - boolean\n\n"
        "Not allowed: object, array, null"
    )

    print("\nUser sees:")
    print(error_message)
    print()


def comparison_before_after():
    """Show before/after comparison."""
    print("\n" + "=" * 70)
    print("BEFORE vs AFTER COMPARISON")
    print("=" * 70)

    print("\n📌 BEFORE (not actionable):")
    print("-" * 70)
    print("ValueError: Invalid log level: TRACE. Must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']")

    print("\n✅ AFTER (actionable):")
    print("-" * 70)
    print("""✗ Invalid log level: 'TRACE'

  Valid options: DEBUG, INFO, WARNING, ERROR, CRITICAL

To fix, set MCP_MIDDLEWARE_LOG_LEVEL to one of the valid options:
  export MCP_MIDDLEWARE_LOG_LEVEL=INFO

Or in .env file:
  MCP_MIDDLEWARE_LOG_LEVEL=INFO""")

    print("\n" + "=" * 70)
    print("\n📌 BEFORE (not actionable):")
    print("-" * 70)
    print("Tool 'fetch_data' cannot be executed because it requires the following secrets that are not available: API_KEY")

    print("\n✅ AFTER (actionable):")
    print("-" * 70)
    print("""✗ Missing secret: 'API_KEY'

  Tool 'fetch_data' requires this secret but it is not configured.

To fix, tell the developer to either:
  1. Add to .env file in the server's working directory:
     API_KEY=your_value_here

  2. Set as environment variable:
     export API_KEY=your_value_here

Then restart the MCP server for changes to take effect.""")
    print()


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "ACTIONABLE ERROR MESSAGES DEMO" + " " * 23 + "║")
    print("║" + " " * 10 + "Improved Error Messages for arcade-mcp-server" + " " * 13 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    demos = [
        ("Missing Secrets", demo_missing_secrets_error),
        ("Missing API Key", demo_missing_api_key_error),
        ("Authorization Required", demo_authorization_required),
        ("Invalid Configuration", demo_invalid_log_level),
        ("Invalid App Name", demo_invalid_app_name),
        ("Tool Not Found", demo_tool_not_found),
        ("No Tools Found", demo_no_tools_error),
        ("Session Not Available", demo_session_not_available),
        ("Invalid Schema", demo_invalid_elicitation_schema),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{i}. {name}")
        print()
        demo_func()

    # Show comparison
    comparison_before_after()

    print("\n" + "=" * 70)
    print("KEY IMPROVEMENTS:")
    print("=" * 70)
    print("✓ Clear visual marker (✗) indicates user-facing error")
    print("✓ Specific problem statement with context")
    print("✓ Concrete fix instructions with examples")
    print("✓ Next steps clearly stated")
    print("✓ Common causes listed when applicable")
    print("✓ Reduces friction - users don't need to search docs")
    print("✓ Errors become self-service documentation")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
