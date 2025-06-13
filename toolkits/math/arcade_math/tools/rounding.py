import decimal
import math
from decimal import Decimal
from typing import Annotated

from arcade_tdk import tool

decimal.getcontext().prec = 100


@tool
def ceil(
    a: Annotated[str, "The number to round up as a string"],
) -> Annotated[str, "The smallest integer greater than or equal to the number as a string"]:
    """
    Return the ceiling of a number
    """
    # Use Decimal for arbitrary precision
    return str(math.ceil(Decimal(a)))


@tool
def floor(
    a: Annotated[str, "The number to round down as a string"],
) -> Annotated[str, "The largest integer less than or equal to the number as a string"]:
    """
    Return the floor of a number
    """
    # Use Decimal for arbitrary precision
    return str(math.floor(Decimal(a)))


@tool
def round_num(
    value: Annotated[str, "The number to round as a string"],
    ndigits: Annotated[str, "The number of digits after the decimal point as a string"],
) -> Annotated[str, "The number rounded to the specified number of digits as a string"]:
    """
    Round a number to a specified number of positive digits
    """
    ndigits_int = int(ndigits)
    if ndigits_int >= 0:
        # Use Decimal for arbitrary precision
        return str(round(Decimal(value), int(ndigits_int)))
    # cast value from str -> float -> int here because rounding with negative
    # decimals is only useful for weird math
    return str(round(int(float(value)), int(ndigits_int)))
