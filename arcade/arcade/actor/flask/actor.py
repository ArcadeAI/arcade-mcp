import asyncio
from typing import Any, Callable, cast

from flask import Flask, request
from pydantic import BaseModel

from arcade.actor.core.base import BaseActor, Router
from arcade.actor.core.common import RequestData
from arcade.actor.utils import is_async_callable


class FlaskActor(BaseActor):
    """
    An Arcade Actor that is hosted inside a Flask app.
    """

    def __init__(self, app: Flask) -> None:
        """
        Initialize the FlaskActor with a Flask app
        instance and an empty ToolCatalog.
        """
        super().__init__()
        self.app = app
        self.router = FlaskRouter(app, self)
        self.register_routes(self.router)


class FlaskRouter(Router):
    def __init__(self, app: Flask, actor: BaseActor) -> None:
        self.app = app
        self.actor = actor

    def _wrap_handler(self, handler: Callable) -> Callable:
        def wrapped_handler() -> Any:
            # TODO: Handle JWT auth
            body_json = cast(dict, request.get_json()) if request.is_json else {}
            request_data = RequestData(
                path=request.path,
                method=request.method,
                body_json=body_json,
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

    def add_route(self, endpoint_path: str, handler: Callable, method: str) -> None:
        """
        Add a route to the Flask application.
        """
        handler_name = handler.__name__ if hasattr(handler, "__name__") else type(handler).__name__
        endpoint_name = f"actor_{handler_name}_{method}"
        self.app.add_url_rule(
            f"{self.actor.base_path}/{endpoint_path}",
            endpoint_name,
            view_func=self._wrap_handler(handler),
            methods=[method],
        )
