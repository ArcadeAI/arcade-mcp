#!/usr/bin/env python3
"""
tools_math.py - Mathematical tools

This file demonstrates how to organize tools in separate files.
All functions decorated with @tool will be discoverable and can be imported.
"""

from typing import Annotated

from arcade_mcp_server import tool


@tool
def add(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Add two numbers together."""
    return a + b


@tool
def multiply(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Multiply two numbers together."""
    return a * b


@tool
def divide(a: Annotated[float, "Dividend"], b: Annotated[float, "Divisor"]) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
