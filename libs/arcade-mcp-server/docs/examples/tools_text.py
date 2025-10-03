#!/usr/bin/env python3
"""
tools_text.py - Text processing tools

This file demonstrates how to organize text processing tools in separate files.
All functions decorated with @tool will be discoverable and can be imported.
"""

from typing import Annotated

from arcade_mcp_server import tool


@tool
def capitalize_string(text: Annotated[str, "Text to capitalize"]) -> str:
    """Capitalize the first letter of a string."""
    return text.capitalize()


@tool
def word_count(text: Annotated[str, "Text to count words in"]) -> int:
    """Count the number of words in a string."""
    return len(text.split())


@tool
def reverse_string(text: Annotated[str, "Text to reverse"]) -> str:
    """Reverse a string."""
    return text[::-1]
