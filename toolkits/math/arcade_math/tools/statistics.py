import decimal
from decimal import Decimal
from statistics import median as stats_median
from typing import Annotated

from arcade_tdk import tool

decimal.getcontext().prec = 100


@tool
def avg(
    numbers: Annotated[list[str], "The list of numbers as strings"],
) -> Annotated[str, "The average (mean) of the numbers in the list as a string"]:
    """
    Calculate the average (mean) of a list of numbers.
    Returns "0.0" if the list is empty.
    """
    # Use Decimal for arbitrary precision
    d_numbers = [Decimal(n) for n in numbers]
    return str(sum(d_numbers) / len(d_numbers)) if d_numbers else "0.0"


@tool
def median(
    numbers: Annotated[list[str], "A list of numbers as strings"],
) -> Annotated[str, "The median value of the numbers in the list as a string"]:
    """
    Calculate the median of a list of numbers.
    Returns "0.0" if the list is empty.
    """
    # Use Decimal for arbitrary precision
    d_numbers = [Decimal(n) for n in numbers]
    return str(stats_median(d_numbers)) if d_numbers else "0.0"
