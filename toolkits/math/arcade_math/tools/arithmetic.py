import decimal
from decimal import Decimal
from typing import Annotated

from arcade_tdk import tool

decimal.getcontext().prec = 100


@tool
def add(
    a: Annotated[str, "The first number as a string"],
    b: Annotated[str, "The second number as a string"],
) -> Annotated[str, "The sum of the two numbers as a string"]:
    """
    Add two numbers together
    """
    # Use Decimal for arbitrary precision
    a_decimal = Decimal(a)
    b_decimal = Decimal(b)
    return str(a_decimal + b_decimal)


@tool
def subtract(
    a: Annotated[str, "The first number as a string"],
    b: Annotated[str, "The second number as a string"],
) -> Annotated[str, "The difference of the two numbers as a string"]:
    """
    Subtract two numbers
    """
    # Use Decimal for arbitrary precision
    a_decimal = Decimal(a)
    b_decimal = Decimal(b)
    return str(a_decimal - b_decimal)


@tool
def multiply(
    a: Annotated[str, "The first number as a string"],
    b: Annotated[str, "The second number as a string"],
) -> Annotated[str, "The product of the two numbers as a string"]:
    """
    Multiply two numbers together
    """
    # Use Decimal for arbitrary precision
    a_decimal = Decimal(a)
    b_decimal = Decimal(b)
    return str(a_decimal * b_decimal)


@tool
def divide(
    a: Annotated[str, "The first number as a string"],
    b: Annotated[str, "The second number as a string"],
) -> Annotated[str, "The quotient of the two numbers as a string"]:
    """
    Divide two numbers
    """
    # Use Decimal for arbitrary precision
    a_decimal = Decimal(a)
    b_decimal = Decimal(b)
    return str(a_decimal / b_decimal)


@tool
def sum_list(
    numbers: Annotated[list[str], "The list of numbers as strings"],
) -> Annotated[str, "The sum of the numbers in the list as a string"]:
    """
    Sum all numbers in a list
    """
    # Use Decimal for arbitrary precision
    return str(sum([Decimal(n) for n in numbers]))


@tool
def sum_range(
    start: Annotated[str, "The start of the range to sum as a string"],
    end: Annotated[str, "The end of the range to sum as a string"],
) -> Annotated[str, "The sum of the numbers in the list as a string"]:
    """
    Sum all numbers from start through end
    """
    return str(sum(list(range(int(start), int(end) + 1))))


@tool
def mod(
    a: Annotated[str, "The dividend as a string"],
    b: Annotated[str, "The divisor as a string"],
) -> Annotated[str, "The remainder after dividing a by b as a string"]:
    """
    Calculate the remainder (modulus) of one number divided by another
    """
    # Use Decimal for arbitrary precision
    return str(Decimal(a) % Decimal(b))
