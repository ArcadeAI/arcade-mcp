import os
from typing import Any, Callable, Optional, TypeVar, Union

from arcade.tool.schemas import ToolAuthorizationRequirement
from arcade.utils import snake_to_pascal_case

T = TypeVar("T")


# TODO change desc to description
def tool(
    func: Callable | None = None,
    desc: str | None = None,
    name: str | None = None,
    requires_auth: Union[ToolAuthorizationRequirement, None] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        func_name = str(getattr(func, "__name__", None))
        tool_name = name or snake_to_pascal_case(func_name)

        setattr(func, "__tool_name__", tool_name)  # noqa: B010 (Do not call `setattr` with a constant attribute value)
        setattr(func, "__tool_description__", desc or func.__doc__)  # noqa: B010
        setattr(func, "__tool_requires_auth__", requires_auth)  # noqa: B010

        return func

    if func:  # This means the decorator is used without parameters
        return decorator(func)
    return decorator


def get_secret(name: str, default: Optional[Any] = None) -> Any:
    secret = os.getenv(name)
    if secret is None:
        if default is not None:
            return default
        raise ValueError(f"Secret {name} is not set.")
    return secret
