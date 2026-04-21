import functools
import inspect
import logging
from typing import Any, Callable, TypeVar

from arcade_core.metadata import ToolMetadata
from arcade_core.schema import ToolExecution

from arcade_tdk.auth import ToolAuthorization
from arcade_tdk.error_adapters import ErrorAdapter
from arcade_tdk.error_adapters.utils import get_adapter_for_auth_provider
from arcade_tdk.errors import (
    FatalToolError,
    ToolRuntimeError,
)
from arcade_tdk.providers.graphql import GraphQLErrorAdapter
from arcade_tdk.providers.http import HTTPErrorAdapter
from arcade_tdk.utils import snake_to_pascal_case

T = TypeVar("T")

logger = logging.getLogger(__name__)


def _build_adapter_chain(
    adapters: list[ErrorAdapter] | None, auth_provider: ToolAuthorization | None
) -> list[ErrorAdapter]:
    """
    Build the adapter chain for error handling.

    Args:
        adapters: User-provided list of error adapters
        auth_provider: The auth provider for the tool

    Returns:
        A deduplicated list of error adapters with the HTTP adapter as fallback

    Raises:
        ValueError: If any adapter doesn't follow the ErrorAdapter protocol
    """
    adapter_chain = adapters or []

    # Validate that all adapters follow the ErrorAdapter protocol
    if not all(isinstance(adapter, ErrorAdapter) for adapter in adapter_chain):
        invalid_adapters = [
            type(adapter).__name__
            for adapter in adapter_chain
            if not isinstance(adapter, ErrorAdapter)
        ]
        raise ValueError(
            f"All adapters must follow the ErrorAdapter protocol. "
            f"Invalid adapters: {', '.join(invalid_adapters)}"
        )

    # Add the adapter that is mapped to the tool's auth provider if it exists
    if auth_adapter := get_adapter_for_auth_provider(auth_provider):
        adapter_chain.append(auth_adapter)

    # Always add GraphQL adapter (it will no-op if gql is not installed)
    adapter_chain.append(GraphQLErrorAdapter())

    # Always add HTTP adapter as the final adapter fallback
    adapter_chain.append(HTTPErrorAdapter())

    # Remove duplicates from the adapter chain, preserving order
    seen_types = set()
    deduplicated_chain = []
    for adapter in adapter_chain:
        adapter_type = type(adapter)
        if adapter_type not in seen_types:
            seen_types.add(adapter_type)
            deduplicated_chain.append(adapter)

    return deduplicated_chain


def _raise_as_arcade_error(
    exception: Exception, adapter_chain: list[ErrorAdapter], tool_name: str, func_name: str
) -> None:
    """
    Try to translate an exception using the adapter chain, then raise the translated error.
    If no adapter can translate the exception, a FatalToolError is raised.

    Args:
        exception: The exception to translate to an Arcade Error
        adapter_chain: List of error adapters to try
        tool_name: The tool's display name for error messages
        func_name: The function name for developer messages

    Raises:
        ToolRuntimeError or some subclass thereof

    Data-leak policy (strict):
        The fallback path below NEVER places ``str(exception)`` content into
        the agent-facing ``message`` field. Tool authors commonly embed user
        input in raised exception messages
        (e.g. ``raise ValueError(f"Bad password: {password}")``) and the
        framework cannot reliably distinguish secrets/PII from safe context.

        Resolution:
        * ``message`` (agent-facing) — exception **type only**, no
          ``str(exception)`` content.
        * ``developer_message`` (server-side logs only — ``error_developer_message``
          Datadog facet, never returned to the client) — carries the
          full ``f"{ExceptionType}: {str(exception)}"`` so on-call engineers
          retain debugging context. Authorized log access is the security
          boundary, not the agent transport.
    """
    for adapter in adapter_chain:
        try:
            mapped = adapter.from_exception(exception)
        except Exception as e:
            logger.warning(
                f"Failed to map exception to Arcade Error with adapter {adapter.slug}: {e}"
            )
            continue
        if isinstance(mapped, ToolRuntimeError):
            raise mapped from exception

    exc_type = type(exception).__name__
    exc_str = str(exception).strip()
    # Agent-facing: type only — never str(exception). See "Data-leak policy".
    message = f"An unhandled {exc_type} was raised by the tool."
    # Server-side debugging: full content goes to logs only.
    developer_message = (
        f"{exc_type}: {exc_str}" if exc_str else f"{exc_type} (no exception message)"
    )
    raise FatalToolError(
        message=message,
        developer_message=developer_message,
    ) from exception


def tool(
    func: Callable | None = None,
    desc: str | None = None,
    name: str | None = None,
    requires_auth: ToolAuthorization | None = None,
    requires_secrets: list[str] | None = None,
    requires_metadata: list[str] | None = None,
    adapters: list[ErrorAdapter] | None = None,
    metadata: ToolMetadata | None = None,
    execution: ToolExecution | None = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        func_name = str(getattr(func, "__name__", None))
        tool_name = name or snake_to_pascal_case(func_name)

        func.__tool_name__ = tool_name  # type: ignore[attr-defined]
        func.__tool_description__ = desc or inspect.cleandoc(func.__doc__ or "")  # type: ignore[attr-defined]
        func.__tool_requires_auth__ = requires_auth  # type: ignore[attr-defined]
        func.__tool_requires_secrets__ = requires_secrets  # type: ignore[attr-defined]
        func.__tool_requires_metadata__ = requires_metadata  # type: ignore[attr-defined]
        func.__tool_metadata__ = metadata  # type: ignore[attr-defined]
        func.__tool_execution__ = execution  # type: ignore[attr-defined]

        adapter_chain = _build_adapter_chain(adapters, requires_auth)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def func_with_error_handling(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except ToolRuntimeError:
                    # re-raise as-is if it is already an Arcade Error
                    raise
                except Exception as e:
                    _raise_as_arcade_error(e, adapter_chain, tool_name, func_name)

        else:

            @functools.wraps(func)
            def func_with_error_handling(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except ToolRuntimeError:
                    # re-raise as-is if it is already an Arcade Error
                    raise
                except Exception as e:
                    _raise_as_arcade_error(e, adapter_chain, tool_name, func_name)

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
