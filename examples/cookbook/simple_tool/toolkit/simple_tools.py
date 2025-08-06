"""
Simple tools example - Basic Arcade tool patterns
"""

from datetime import datetime

from arcade_sdk import tool
from arcade_sdk.context import ToolContext


@tool
async def hello_world(name: str = "World") -> str:
    """
    A simple greeting tool.

    Args:
        name: The name to greet

    Returns:
        A friendly greeting
    """
    return f"Hello, {name}! Welcome to Arcade."


@tool
async def add_numbers(a: float, b: float) -> float:
    """
    Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


@tool
async def get_current_time(timezone: str = "UTC", ctx: ToolContext = None) -> str:
    """
    Get the current time with user context.

    Args:
        timezone: The timezone to use (default: UTC)
        ctx: Tool context (injected automatically)

    Returns:
        Current time and user info
    """
    now = datetime.now()
    user_id = ctx.user_id if ctx else "anonymous"

    return f"Current time in {timezone}: {now.strftime('%Y-%m-%d %H:%M:%S')} (user: {user_id})"


@tool
async def process_list(items: list[str], operation: str = "count") -> dict[str, any]:
    """
    Process a list of items with various operations.

    Args:
        items: List of items to process
        operation: Operation to perform (count, reverse, sort, unique)

    Returns:
        Result of the operation
    """
    if operation == "count":
        return {"result": len(items), "operation": operation}
    elif operation == "reverse":
        return {"result": list(reversed(items)), "operation": operation}
    elif operation == "sort":
        return {"result": sorted(items), "operation": operation}
    elif operation == "unique":
        return {"result": list(set(items)), "operation": operation}
    else:
        return {"error": f"Unknown operation: {operation}"}
