import random
from typing import Annotated, Optional

from arcade.sdk import tool


@tool
def generate_random_int(
    min_value: Annotated[int, "The minimum value of the random integer"],
    max_value: Annotated[int, "The maximum value of the random integer"],
    seed: Annotated[
        Optional[int],
        "The seed for the random number generator. If None, the current system time is used.",
    ] = None,
) -> Annotated[int, "A random integer between min_value and max_value"]:
    """Generate a random integer between min_value and max_value (inclusive)."""
    if seed is not None:
        random.seed(seed)

    return random.randint(min_value, max_value)  # noqa: S311


@tool
def generate_random_float(
    min_value: Annotated[float, "The minimum value of the random float"],
    max_value: Annotated[float, "The maximum value of the random float"],
    seed: Annotated[
        Optional[int],
        "The seed for the random number generator. If None, the current system time is used.",
    ] = None,
) -> Annotated[float, "A random float between min_value and max_value"]:
    """Generate a random float between min_value and max_value."""
    if seed is not None:
        random.seed(seed)

    return random.uniform(min_value, max_value)  # noqa: S311
