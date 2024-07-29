import inspect
import os
from abc import ABC
from typing import Any, Callable, Optional, TypeVar, Union

from pydantic import AnyUrl, BaseModel

from arcade.core.utils import snake_to_pascal_case

T = TypeVar("T")


class ToolAuthorization(BaseModel, ABC):
    """The annotation for a tool that requires authorization."""

    pass


class OAuth2Authorization(ToolAuthorization):
    """The annotation for a tool that requires OAuth2 authorization."""

    authority: AnyUrl
    """The URL to which the user should be redirected to authorize the tool."""

    scope: Optional[list[str]] = None
    """The scope of the authorization."""


# TODO change desc to description
def tool(
    func: Callable | None = None,
    desc: str | None = None,
    name: str | None = None,
    requires_auth: Union[ToolAuthorization, None] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        func_name = str(getattr(func, "__name__", None))
        tool_name = name or snake_to_pascal_case(func_name)

        setattr(func, "__tool_name__", tool_name)  # noqa: B010 (Do not call `setattr` with a constant attribute value)
        setattr(func, "__tool_description__", desc or inspect.cleandoc(func.__doc__ or ""))  # noqa: B010
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
