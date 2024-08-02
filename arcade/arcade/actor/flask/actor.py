import asyncio
from typing import Any, Callable, cast

from flask import Flask, request
from pydantic import BaseModel

from arcade.actor.core.base import BaseActor, BaseRouter
from arcade.actor.core.common import RequestData
from arcade.actor.utils import is_async_callable


class FlaskActor(BaseActor):
    def __init__(self, app: Flask) -> None:
        """
        Initialize the FlaskActor with a Flask app
        instance and an empty ToolCatalog.
        """
        super().__init__()
        self.app = app
        self.router = FlaskRouter(app, self)
        self.register_routes(self.router)


class FlaskRouter(BaseRouter):
    def __init__(self, app: Flask, actor: BaseActor) -> None:
        self.app = app
        self.actor = actor

    def _wrap_handler(self, handler: Callable) -> Callable:
        def wrapped_handler() -> Any:
            # TODO: Handle JWT auth
            request_data = RequestData(
                path=request.path,
                method=request.method,
                body=request.get_json()
                if request.is_json
                else cast(str, request.get_data(as_text=True)),
            )

            if is_async_callable(handler):
                # TODO probably not the best way to do this.
                # Consider a thread pool when we make this production-worthy.
                result = asyncio.run(handler(request_data))
            else:
                result = handler(request_data)

            # If the result is a pydantic BaseModel, use model_dump
            if isinstance(result, BaseModel):
                return result.model_dump()
            elif isinstance(result, list) and all(isinstance(item, BaseModel) for item in result):
                return [item.model_dump() for item in result]
            return result

        return wrapped_handler

    def add_route(self, path: str, handler: Callable, method: str) -> None:
        """
        Add a route to the Flask application.
        """
        handler_name = handler.__name__ if hasattr(handler, "__name__") else type(handler).__name__
        endpoint_name = f"actor_{handler_name}_{method}"
        self.app.add_url_rule(
            path, endpoint_name, view_func=self._wrap_handler(handler), methods=[method]
        )
