import random
from typing import Annotated

from arcade_mcp_server import tool


@tool
def get_n_random_numbers(
    n: Annotated[int, "The number of random numbers to generate"],
) -> Annotated[list[int], "A list of random numbers between 0 and 100"]:
    """
    Generate a list of random numbers between 0 and 100.
    """
    return [random.randint(0, 100) for _ in range(n)]  # noqa: S311
