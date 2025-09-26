from collections.abc import Awaitable
from typing import Callable, ClassVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class AddTrailingSlashToPathMiddleware(BaseHTTPMiddleware):
    """Middleware that adds trailing slashes to specific paths.

    Example:
    - /mcp -> /mcp/
    - /mcp/ -> /mcp/
    """

    PATHS_TO_ADD_SLASH: ClassVar[list[str]] = ["/mcp"]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.scope["path"]
        if path in self.PATHS_TO_ADD_SLASH and not path.endswith("/"):
            request.scope["path"] = path + "/"
        return await call_next(request)
