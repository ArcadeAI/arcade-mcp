import functools
from collections.abc import Callable
from typing import Any

from arcade_tdk import ToolContext
from googleapiclient.errors import HttpError

from arcade_google_docs.file_picker import generate_google_file_picker_url


def with_filepicker_fallback(func: Callable[..., Any]) -> Callable[..., Any]:
    """ """

    @functools.wraps(func)
    async def async_wrapper(context: ToolContext, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(context, *args, **kwargs)
        except HttpError as e:
            if e.status_code in [403, 404]:
                file_picker_response = generate_google_file_picker_url(context)
                return file_picker_response
            raise

    return async_wrapper
