import datetime
import functools
import inspect
import re
from typing import Any, Callable, TypeVar, Union

import httpx

from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.errors import (
    NonRetryableToolError,
    RetryableToolError,
    ToolExecutionError,
)
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

                # make sure developer raised ToolExecutionError is not
                # reraised incorrectly.
                except ToolExecutionError:
                    raise
                except Exception as e:
                    adapter = GenericHTTPAdapter()
                    # raise NonRetryableToolError(
                    #     message=f"Error in execution of {tool_name}",
                    #     developer_message=f"Error in {func_name}: {e!s}",
                    # ) from e
                    _raise_mapped(e, adapter)

        else:

            @functools.wraps(func)
            def func_with_error_handling(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except ToolExecutionError:
                    raise
                except Exception as e:
                    raise ToolExecutionError(
                        message=f"Error in execution of {tool_name}",
                        developer_message=f"Error in {func_name}: {e!s}",
                    ) from e

        def _raise_mapped(e, adapter):
            if adapter and (err := adapter.from_exception(e)):
                raise err
            if err := GenericHTTPAdapter().from_exception(e):
                raise err
            raise ToolExecutionError(
                message=f"Error in execution of {tool_name}",
                developer_message=f"Error in {func_name}: {e!s}",
            ) from e

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


RATE_HEADERS = ("retry-after", "x-ratelimit-reset", "x-ratelimit-reset-ms")


def _parse_retry_ms(headers: dict[str, str]) -> int:
    val = next((headers.get(h) for h in RATE_HEADERS if headers.get(h)), None)
    if val is None:
        return 1_000
    if re.fullmatch(r"\d+", val):  # seconds (int)
        return int(val) * 1_000
    try:  # HTTP-date
        dt = datetime.datetime.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")
        return int((dt - datetime.datetime.utcnow()).total_seconds() * 1_000)
    except Exception:
        return 1_000


class GenericHTTPAdapter:
    slug = "_generic_http"

    def _map(self, status: int, headers, msg: str):
        if status == 429:
            return RetryableToolError(
                message=msg,
                status_code=status,
                retry_after_ms=_parse_retry_ms(headers),
            )
            # return UpstreamRateLimitError(_parse_retry_ms(headers), msg)
        if status in (401, 403):
            return NonRetryableToolError(message=msg, status_code=status)
            # return AuthError(msg)
        if 500 <= status < 600:
            return NonRetryableToolError(message=msg, status_code=status)
            # return TransientUpstreamError(msg)
        if 400 <= status < 500:
            return NonRetryableToolError(status_code=status, message=msg)
            # return NonRetryableError(origin="UPSTREAM", code=f"HTTP_{status}", message=msg)
        return None

    # httpx exceptions
    def from_exception(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            r = exc.response
            return self._map(r.status_code, r.headers, str(exc))
        # TODO: Add support for requests
        return None

    # raw Response objects
    def from_response(self, r: Any):
        status = getattr(r, "status_code", None)
        headers = getattr(r, "headers", {})
        if status and status >= 400:
            return self._map(status, headers, f"HTTP {status}")
        return None
