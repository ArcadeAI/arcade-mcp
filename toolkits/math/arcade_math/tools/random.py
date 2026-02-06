import random
from typing import Annotated

from arcade_core.metadata import (
    Behavior,
    Classification,
    Domain,
    SystemType,
    ToolMetadata,
    Verb,
)
from arcade_tdk import tool


@tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.TRANSFORM],
            system_types=[SystemType.SELF_CONTAINED],
        ),
        behavior=Behavior(
            verbs=[Verb.EXECUTE],
            read_only=True,
            destructive=False,
            idempotent=False,
            open_world=False,
        ),
    ),
)
def generate_random_int(
    min_value: Annotated[str, "The minimum value of the random integer as a string"],
    max_value: Annotated[str, "The maximum value of the random integer as a string"],
    seed: Annotated[
        str | None,
        "The seed for the random number generator as a string."
        " If None, the current system time is used.",
    ] = None,
) -> Annotated[str, "A random integer between min_value and max_value as a string"]:
    """Generate a random integer between min_value and max_value (inclusive)."""
    if seed is not None:
        random.seed(int(seed))

    return str(random.randint(int(min_value), int(max_value)))  # noqa: S311


@tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.TRANSFORM],
            system_types=[SystemType.SELF_CONTAINED],
        ),
        behavior=Behavior(
            verbs=[Verb.EXECUTE],
            read_only=True,
            destructive=False,
            idempotent=False,
            open_world=False,
        ),
    ),
)
def generate_random_float(
    min_value: Annotated[str, "The minimum value of the random float as a string"],
    max_value: Annotated[str, "The maximum value of the random float as a string"],
    seed: Annotated[
        str | None,
        "The seed for the random number generator as a string."
        " If None, the current system time is used.",
    ] = None,
) -> Annotated[str, "A random float between min_value and max_value as a string"]:
    """Generate a random float between min_value and max_value."""
    if seed is not None:
        random.seed(int(seed))

    return str(random.uniform(float(min_value), float(max_value)))  # noqa: S311
