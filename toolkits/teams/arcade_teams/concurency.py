import asyncio
from collections.abc import Callable
from typing import Any

from arcade_tdk import ToolContext

from arcade_teams.exceptions import PaginationTimeoutError
from arcade_teams.models import PaginationSentinel


def default_response_getter(response: Any) -> Any:
    if hasattr(response, "value"):
        return response.value
    return response


async def paginate(
    context: ToolContext,
    func: Callable,
    request_builder: Callable,
    page_limit: int,
    result_getter: Callable = default_response_getter,
    global_limit: int | None = None,
    timeout: int | None = None,
    sentinel: PaginationSentinel | None = None,
    semaphore: asyncio.Semaphore | None = None,
    **request_kwargs: Any,
) -> tuple[list, str | None]:
    """Paginate a Microsoft Graph Client's method results."""
    results: list[Any] = []

    from arcade_teams.utils import load_config_param  # Avoid circular import

    timeout = timeout or load_config_param(context, "TEAMS_PAGINATION_TIMEOUT")
    semaphore = semaphore or asyncio.Semaphore(load_config_param(context, "TEAMS_MAX_CONCURRENCY"))
    next_page_token = request_kwargs.get("skiptoken")

    async def pagination_loop() -> tuple[list[Any], str | None]:
        nonlocal results, next_page_token
        should_continue = True

        while should_continue:
            request_kwargs["top"] = (
                page_limit if not global_limit else min(page_limit, global_limit - len(results))
            )
            request_kwargs["next_page_token"] = next_page_token
            request = request_builder(**request_kwargs)

            async with semaphore:
                api_response = await func(request)

            result = result_getter(api_response)

            next_page_token = api_response.odata_next_link

            if (
                (sentinel and sentinel(last_result=result))
                or (global_limit and len(results) >= global_limit)
                or not next_page_token
            ):
                should_continue = False

            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)

        return results, next_page_token

    try:
        results, next_page_token = await asyncio.wait_for(pagination_loop(), timeout=timeout)
    # asyncio.TimeoutError for Python <= 3.10, TimeoutError for Python >= 3.11
    except (TimeoutError, asyncio.TimeoutError) as e:
        raise PaginationTimeoutError(timeout) from e
    else:
        return results, next_page_token
