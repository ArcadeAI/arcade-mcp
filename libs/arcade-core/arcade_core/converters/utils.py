"""Shared utilities for tool name conversion across providers.

This module contains common utilities used by both OpenAI and Anthropic converters.
"""


def normalize_tool_name(name: str) -> str:
    """
    Normalize a tool name for LLM provider compatibility.

    Both OpenAI and Anthropic have restrictions on tool names:
    - OpenAI: allows alphanumeric, hyphens, underscores (max 64 chars)
    - Anthropic: allows alphanumeric and underscores only (no dots)

    Arcade uses dot notation for fully qualified names (e.g., "Google.Search"),
    so we normalize by replacing dots with underscores.

    Args:
        name: The original tool name (e.g., "Google.Search")

    Returns:
        The normalized tool name (e.g., "Google_Search")

    Examples:
        >>> normalize_tool_name("Google.Search")
        'Google_Search'
        >>> normalize_tool_name("MyTool")
        'MyTool'
        >>> normalize_tool_name("Namespace.Sub.Tool")
        'Namespace_Sub_Tool'
    """
    return name.replace(".", "_")


def denormalize_tool_name(normalized_name: str, separator: str = ".") -> str:
    """
    Reverse the normalization of a tool name.

    This converts provider-format names back to Arcade's dot notation.
    Note: This is a best-effort reversal and may not be accurate if the original
    name contained underscores.

    Args:
        normalized_name: The normalized tool name (e.g., "Google_Search")
        separator: The separator to use (default: ".")

    Returns:
        The denormalized tool name (e.g., "Google.Search")

    Examples:
        >>> denormalize_tool_name("Google_Search")
        'Google.Search'
    """
    return normalized_name.replace("_", separator)
