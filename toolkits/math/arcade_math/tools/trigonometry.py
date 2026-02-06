import decimal
import math
from decimal import Decimal
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

decimal.getcontext().prec = 100


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
            idempotent=True,
            open_world=False,
        ),
    ),
)
def deg_to_rad(
    degrees: Annotated[str, "Angle in degrees as a string"],
) -> Annotated[str, "Angle in radians as a string"]:
    """
    Convert an angle from degrees to radians.
    """
    # Use Decimal for arbitrary precision
    return str(math.radians(Decimal(degrees)))


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
            idempotent=True,
            open_world=False,
        ),
    ),
)
def rad_to_deg(
    radians: Annotated[str, "Angle in radians as a string"],
) -> Annotated[str, "Angle in degrees as a string"]:
    """
    Convert an angle from radians to degrees.
    """
    # Use Decimal for arbitrary precision
    return str(math.degrees(Decimal(radians)))
