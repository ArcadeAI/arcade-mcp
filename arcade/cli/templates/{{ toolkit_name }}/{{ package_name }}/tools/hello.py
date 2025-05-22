from typing import Annotated

from arcade_tdk_py.sdk import tool


@tool
def say_hello(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Say a greeting!"""

    return "Hello, " + name + "!"
