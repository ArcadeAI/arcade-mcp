import functools
import inspect
from typing import Any, Callable, TypeVar, Union

from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.errors import (
    NonRetryableToolError,
    ToolRuntimeError,
)
from arcade_tdk.providers.http import HTTPErrorAdapter
from arcade_tdk.utils import snake_to_pascal_case

T = TypeVar("T")


def tool(
    func: Callable | None = None,
    desc: str | None = None,
    name: str | None = None,
    requires_auth: Union[ToolAuthorization, None] = None,
    requires_secrets: Union[list[str], None] = None,
    requires_metadata: Union[list[str], None] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        func_name = str(getattr(func, "__name__", None))
        tool_name = name or snake_to_pascal_case(func_name)

        func.__tool_name__ = tool_name  # type: ignore[attr-defined]
        func.__tool_description__ = desc or inspect.cleandoc(func.__doc__ or "")  # type: ignore[attr-defined]
        func.__tool_requires_auth__ = requires_auth  # type: ignore[attr-defined]
        func.__tool_requires_secrets__ = requires_secrets  # type: ignore[attr-defined]
        func.__tool_requires_metadata__ = requires_metadata  # type: ignore[attr-defined]

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def func_with_error_handling(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)

                # make sure developer raised ToolRuntimeError is not re-raised incorrectly.
                except ToolRuntimeError:
                    raise
                except Exception as e:
                    adapter = HTTPErrorAdapter()
                    _raise_mapped(e, adapter)
                    raise NonRetryableToolError(
                        message=f"Error in execution of {tool_name}",
                        developer_message=f"Error in {func_name}: {e!s}",
                    ) from e

        else:

            @functools.wraps(func)
            def func_with_error_handling(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except ToolRuntimeError:
                    raise
                except Exception as e:
                    adapter = HTTPErrorAdapter()
                    _raise_mapped(e, adapter)
                    raise NonRetryableToolError(
                        message=f"Error in execution of {tool_name}",
                        developer_message=f"Error in {func_name}: {e!s}",
                    ) from e

        def _raise_mapped(e, adapter):
            if adapter and (err := adapter.from_exception(e)):
                raise err
            if err := HTTPErrorAdapter().from_exception(e):
                raise err

        return func_with_error_handling

    if func:
        return decorator(func)
    return decorator


def _tool_deprecated(message: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        func.__tool_deprecation_message__ = message  # type: ignore[attr-defined]
        return func

    return decorator


tool.deprecated = _tool_deprecated  # type: ignore[attr-defined]
