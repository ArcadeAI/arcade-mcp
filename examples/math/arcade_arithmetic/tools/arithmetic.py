import math
from typing import Annotated

from arcade.sdk.tool import tool


@tool
def add(
    a: Annotated[int, "The first number"], b: Annotated[int, "The second number"]
) -> Annotated[int, "The sum of the two numbers"]:
    """
    Add two numbers together
    """
    return a + b


@tool
def multiply(
    a: Annotated[int, "The first number"], b: Annotated[int, "The second number"]
) -> Annotated[int, "The product of the two numbers"]:
    """
    Multiply two numbers together
    """
    return a * b


@tool
def divide(
    a: Annotated[int, "The first number"], b: Annotated[int, "The second number"]
) -> Annotated[float, "The quotient of the two numbers"]:
    """
    Divide two numbers
    """
    return a / b


@tool
def sqrt(
    a: Annotated[int, "The number to square root"],
) -> Annotated[float, "The square root of the number"]:
    """
    Get the square root of a number
    """
    return math.sqrt(a)
