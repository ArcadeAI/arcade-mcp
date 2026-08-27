from decimal import Decimal
from typing import Annotated

from arcade_tdk import tool


@tool
def sum_list(
    numbers: Annotated[list[str], "The list of numbers as strings"],
) -> Annotated[str, "The sum of the numbers in the list as a string"]:
    """
    Sum all numbers in a list
    """
    # Use Decimal for arbitrary precision
    return str(sum([Decimal(n) for n in numbers]))
