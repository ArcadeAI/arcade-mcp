from typing import Any, Callable

from fastapi import FastAPI, Request

from arcade.actor.core.base import BaseActor, BaseRouter
from arcade.actor.utils import is_async_callable


class FastAPIActor(BaseActor):
    def __init__(self, app: FastAPI) -> None:
        """
        Initialize the FastAPIActor with a FastAPI app
        instance and an empty ToolCatalog.
        """
        super().__init__()
        self.app = app
        self.router = FastAPIRouter(app, self)
        self.register_routes(self.router)


class FastAPIRouter(BaseRouter):
    def __init__(self, app: FastAPI, actor: BaseActor) -> None:
        self.app = app
        self.actor = actor

    def _wrap_handler(self, handler: Callable) -> Callable:
        """
        Wrap the handler to handle FastAPI-specific request and response.
        """

        async def wrapped_handler(
            request: Request,
            # api_key: str = Depends(get_api_key), # TODO re-enable when Engine supports auth
        ) -> Any:
            if is_async_callable(handler):
                return await handler(request)
            else:
                return handler(request)

        return wrapped_handler

    def add_route(self, path: str, handler: Callable, method: str) -> None:
        """
        Add a route to the FastAPI application.
        """
        for m in method:
            if m == "GET":
                self.app.get(path)(self._wrap_handler(handler))
            elif m == "POST":
                self.app.post(path)(self._wrap_handler(handler))
            elif m == "PUT":
                self.app.put(path)(self._wrap_handler(handler))
            elif m == "DELETE":
                self.app.delete(path)(self._wrap_handler(handler))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
