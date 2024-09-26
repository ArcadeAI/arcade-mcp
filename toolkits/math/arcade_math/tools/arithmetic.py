import math
from typing import Annotated

from arcade.sdk import tool


@tool
def add(
    a: Annotated[int, "The first number"], b: Annotated[int, "The second number"]
) -> Annotated[int, "The sum of the two numbers"]:
    """
    Add two numbers together
    """
    return a + b


@tool
def subtract(
    a: Annotated[int, "The first number"], b: Annotated[int, "The second number"]
) -> Annotated[int, "The difference of the two numbers"]:
    """
    Subtract two numbers
    """
    return a - b


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


@tool
def sum_list(
    numbers: Annotated[list[float], "The list of numbers"],
) -> Annotated[float, "The sum of the numbers in the list"]:
    """
    Sum all numbers in a list
    """
    return sum(numbers)


@tool
def sum_range(
    start: Annotated[int, "The start of the range to sum"],
    end: Annotated[int, "The end of the range to sum"],
) -> Annotated[int, "The sum of the numbers in the list"]:
    """
    Sum all numbers from start through end
    """
    return sum(list(range(start, end + 1)))
