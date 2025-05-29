import decimal
import math
from decimal import Decimal
from typing import Annotated

from arcade_tdk import tool

decimal.getcontext().prec = 100


@tool
def abs_val(
    a: Annotated[str, "The number as a string"],
) -> Annotated[str, "The absolute value of the number as a string"]:
    """
    Calculate the absolute value of a number
    """
    # Use Decimal for arbitrary precision
    return str(abs(Decimal(a)))


@tool
def factorial(
    a: Annotated[str, "The non-negative integer to compute the factorial for as a string"],
) -> Annotated[str, "The factorial of the number as a string"]:
    """
    Compute the factorial of a non-negative integer
    Returns "1" for "0"
    """
    return str(math.factorial(int(a)))


@tool
def sqrt(
    a: Annotated[str, "The number to square root as a string"],
) -> Annotated[str, "The square root of the number as a string"]:
    """
    Get the square root of a number
    """
    # Use Decimal for arbitrary precision
    a_decimal = Decimal(a)
    return str(a_decimal.sqrt())
