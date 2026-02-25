import decimal
import math
from decimal import Decimal
from typing import Annotated

from arcade_mcp_server import tool
from arcade_mcp_server.metadata import Behavior, ToolMetadata

decimal.getcontext().prec = 100


@tool(
    metadata=ToolMetadata(
        behavior=Behavior(
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
    ),
)
def log(
    a: Annotated[str, "The number to take the logarithm of as a string"],
    base: Annotated[str, "The logarithmic base as a string"],
) -> Annotated[str, "The logarithm of the number with the specified base as a string"]:
    """
    Calculate the logarithm of a number with a given base
    """
    # Use Decimal for arbitrary precision
    return str(math.log(Decimal(a), Decimal(base)))


@tool(
    metadata=ToolMetadata(
        behavior=Behavior(
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
    ),
)
def power(
    a: Annotated[str, "The base number as a string"],
    b: Annotated[str, "The exponent as a string"],
) -> Annotated[str, "The result of raising a to the power of b as a string"]:
    """
    Calculate one number raised to the power of another
    """
    # Use Decimal for arbitrary precision
    return str(Decimal(a) ** Decimal(b))
