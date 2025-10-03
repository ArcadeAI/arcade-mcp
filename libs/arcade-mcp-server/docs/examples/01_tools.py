#!/usr/bin/env python3
"""
01_tools.py - Tool creation and parameter types

This example demonstrates:
1. How to create tools with @app.tool decorator in MCPApp
2. Different parameter types (simple, lists, TypedDict)
3. Direct Python execution for better control

To run:
    uv run 01_tools.py                  # HTTP transport (default)
    uv run 01_tools.py stdio           # stdio transport for Claude Desktop
"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp
from typing_extensions import TypedDict

# Create the MCP application
app = MCPApp(
    name="tools_example",
    version="1.0.0",
    instructions="Example server demonstrating various tool parameter types",
)

# === SIMPLE TOOLS ===


@app.tool
def hello(name: Annotated[str, "Name to greet"]) -> Annotated[str, "Greeting message"]:
    """Say hello to someone."""
    return f"Hello, {name}!"


@app.tool
def add(
    a: Annotated[float, "First number"], b: Annotated[float, "Second number"]
) -> Annotated[float, "Sum of the numbers"]:
    """Add two numbers together."""
    return a + b


# === TOOLS WITH LIST PARAMETERS ===


@app.tool
def calculate_average(
    numbers: Annotated[list[float], "List of numbers to average"],
) -> Annotated[float, "Average of all numbers"]:
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


@app.tool
def factorial(n: Annotated[int, "Non-negative integer"]) -> Annotated[int, "Factorial of n"]:
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


@app.tool
def create_user_profile(
    person: Annotated[PersonInfo, "Person's information"],
) -> Annotated[str, "Formatted user profile"]:
    """Create a formatted user profile from person information."""
    status = "Active" if person["is_active"] else "Inactive"
    return f"""
User Profile:
- Name: {person["name"]}
- Age: {person["age"]}
- Email: {person["email"]}
- Status: {status}
""".strip()


class CalculationResult(TypedDict):
    sum: float
    average: float
    min: float
    max: float
    count: int


@app.tool
def analyze_numbers(
    values: Annotated[list[float], "List of numbers to analyze"],
) -> Annotated[CalculationResult, "Statistical analysis of the numbers"]:
    """Analyze a list of numbers and return statistics."""
    if not values:
        return {"sum": 0.0, "average": 0.0, "min": 0.0, "max": 0.0, "count": 0}

    return {
        "sum": sum(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "count": len(values),
    }


if __name__ == "__main__":
    # Check if stdio transport was requested
    transport = "stdio" if len(sys.argv) > 1 and sys.argv[1] == "stdio" else "http"

    print(f"Starting {app.name} v{app.version}")
    print(f"Transport: {transport}")

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)
