#!/usr/bin/env python3
"""04: Read secrets from .env via Context

Run (auto-discovery):
  python -m arcade_mcp

For Claude Desktop (stdio transport):
  python -m arcade_mcp stdio

Environment:
  # Create a .env in the working directory with:
  #   API_KEY=supersecret
"""

from arcade_tdk import Context, tool


@tool(
    name="UseSecret",
    desc="Echo a masked secret read from the context",
    requires_secrets=["API_KEY"],  # declare we need API_KEY
)
def use_secret(context: Context) -> str:
    """Read API_KEY from context and return a masked confirmation string."""
    try:
        value = context.get_secret("API_KEY")
        masked = value[:2] + "***" if len(value) >= 2 else "***"
        return f"Got API_KEY of length {len(value)} -> {masked}"
    except Exception as e:
        return f"Error getting secret: {e}"
