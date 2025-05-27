import json
from typing import Any, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry.metrics import Meter

from arcade_serve.core.base import (
    BaseWorker,
    Router,
)
from arcade_serve.core.common import RequestData, ResponseData, WorkerComponent
from arcade_serve.fastapi.auth import validate_engine_request
from arcade_serve.utils import is_async_callable


class FastAPIWorker(BaseWorker):
    """
    An Arcade Worker that is hosted inside a FastAPI app.
    """

    def __init__(
        self,
        app: FastAPI,
        secret: str | None = None,
        *,
        disable_auth: bool = False,
        otel_meter: Meter | None = None,
    ) -> None:
        """
        Initialize the FastAPIWorker with a FastAPI app instance.
        If no secret is provided, the worker will use the ARCADE_WORKER_SECRET environment variable.

        Args:
            app: The FastAPI app to host the worker in
            secret: Optional secret for authorization
            disable_auth: Whether to disable authorization
            otel_meter: Optional OpenTelemetry meter
        """
        super().__init__(secret, disable_auth, otel_meter)
        self.app = app
        self.router = FastAPIRouter(app, self)
        self.register_routes(self.router)

        # Initialize components
        self.components: list[WorkerComponent] = []


security = HTTPBearer()  # Authorization: Bearer <xxx>


class FastAPIRouter(Router):
    def __init__(self, app: FastAPI, worker: BaseWorker) -> None:
        self.app = app
        self.worker = worker

    def _wrap_handler(self, handler: Callable, require_auth: bool = True) -> Callable:
        """
        Wrap the handler to handle FastAPI-specific request and response.
        """

        use_auth_for_route = not self.worker.disable_auth and require_auth

        def call_validate_engine_request(worker_secret: str) -> Callable:
            async def dependency(
                credentials: HTTPAuthorizationCredentials = Depends(security),
            ) -> None:
                await validate_engine_request(worker_secret, credentials)

            return dependency

        async def wrapped_handler(
            request: Request,
            _: None = Depends(call_validate_engine_request(self.worker.secret))
            if use_auth_for_route
            else None,
        ) -> Any:
            body_str = await request.body()
            body_json = json.loads(body_str) if body_str else {}
            request_data = RequestData(
                path=request.url.path,
                method=request.method,
                body_json=body_json,
            )
            if is_async_callable(handler):
                return await handler(request_data)
            else:
                return handler(request_data)

        return wrapped_handler

    def add_route(
        self,
        endpoint_path: str,
        handler: Callable,
        method: str,
        require_auth: bool = True,
        response_type: type[ResponseData] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a route to the FastAPI application.
        """
        self.app.add_api_route(
            f"{self.worker.base_path}/{endpoint_path}",
            self._wrap_handler(handler, require_auth),
            methods=[method],
            response_model=response_type,
            # **kwargs to pass to FastAPI
            **kwargs,
        )
