#!/usr/bin/env python
"""
01_tools.py - Tool creation, discovery, and parameter types

This example demonstrates:
1. How to create tools with the @tool decorator
2. Different parameter types (simple, lists, TypedDict)
3. How arcade_mcp discovers tools automatically

To run:
    python -m arcade_mcp                  # Auto-discover all tools
    python -m arcade_mcp --show-packages  # Show what's being loaded
    python -m arcade_mcp stdio            # For Claude Desktop
"""

# === DISCOVERY PATTERNS ===

"""
The arcade_mcp CLI discovers tools using these patterns:

1. Current directory: *.py files
   - Scans all Python files in the current directory
   - Imports and checks for @tool decorated functions

2. tools/ directory:
   - If exists, recursively scans for Python files
   - Common convention for organizing tools

3. arcade_tools/ directory:
   - Alternative directory name
   - Also recursively scanned

4. Package loading with --tool-package:
   python -m arcade_mcp --tool-package github
   - Loads arcade-github package
   - Can load any installed package in the current python environment

5. Discover all installed with --discover-installed:
   python -m arcade_mcp --discover-installed
   - Finds all arcade-* packages in the current python environment
   - Loads all their tools

Discovery tips:
- Use __init__.py in directories for proper imports
- Organize related tools in subdirectories
- Use clear, descriptive tool names
- Tools are namespaced by their toolkit name
"""

from typing import Annotated
from typing_extensions import TypedDict
from arcade_tdk import tool


# === SIMPLE TOOLS ===

@tool
def hello(name: Annotated[str, "Name to greet"]) -> Annotated[str, "Greeting message"]:
    """Say hello to someone."""
    return f"Hello, {name}!"


@tool
def add(
    a: Annotated[float, "First number"],
    b: Annotated[float, "Second number"]
) -> Annotated[float, "Sum of the numbers"]:
    """Add two numbers together."""
    return a + b


# === TOOLS WITH LIST PARAMETERS ===

@tool
def calculate_average(
    numbers: Annotated[list[float], "List of numbers to average"]
) -> Annotated[float, "Average of all numbers"]:
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


@tool
def factorial(
    n: Annotated[int, "Non-negative integer"]
) -> Annotated[int, "Factorial of n"]:
    """Calculate the factorial of a number."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1

    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


# === TOOLS WITH COMPLEX TYPES (TypedDict) ===

class PersonInfo(TypedDict):
    name: str
    age: int
    email: str
    is_active: bool


@tool
def create_user_profile(
    person: Annotated[PersonInfo, "Person's information"]
) -> Annotated[str, "Formatted user profile"]:
    """Create a formatted user profile from person information."""
    status = "Active" if person["is_active"] else "Inactive"
    return f"""
User Profile:
- Name: {person['name']}
- Age: {person['age']}
- Email: {person['email']}
- Status: {status}
""".strip()


class CalculationResult(TypedDict):
    sum: float
    average: float
    min: float
    max: float
    count: int


@tool
def analyze_numbers(
    values: Annotated[list[float], "List of numbers to analyze"]
) -> Annotated[CalculationResult, "Statistical analysis of the numbers"]:
    """Analyze a list of numbers and return statistics."""
    if not values:
        return {
            "sum": 0.0,
            "average": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0
        }

    return {
        "sum": sum(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "count": len(values)
    }
