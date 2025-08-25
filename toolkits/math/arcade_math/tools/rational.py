import math
from typing import Annotated

from arcade_tdk import tool


@tool
def gcd(
    a: Annotated[str, "First integer as a string"],
    b: Annotated[str, "Second integer as a string"],
) -> Annotated[str, "The greatest common divisor of a and b as a string"]:
    """
    Calculate the greatest common divisor (GCD) of two integers.
    """
    return str(math.gcd(int(a), int(b)))


@tool
def lcm(
    a: Annotated[str, "First integer as a string"],
    b: Annotated[str, "Second integer as a string"],
) -> Annotated[str, "The least common multiple of a and b as a string"]:
    """
    Calculate the least common multiple (LCM) of two integers.
    Returns "0" if either integer is 0.
    """
    a_int, b_int = int(a), int(b)
    if a_int == 0 or b_int == 0:
        return "0"
    return str(abs(a_int * b_int) // math.gcd(a_int, b_int))
