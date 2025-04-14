import json
from typing import Any, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry.metrics import Meter

from arcade.worker.core.base import (
    BaseWorker,
    Router,
)
from arcade.worker.core.common import RequestData, WorkerComponent
from arcade.worker.fastapi.auth import validate_engine_request
from arcade.worker.mcp.logging import create_mcp_logging_middleware
from arcade.worker.mcp.sse import create_mcp_sse_component
from arcade.worker.utils import is_async_callable

MCP_AVAILABLE = True


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
        enable_mcp: bool = False,
        mcp_config: dict[str, Any] | None = None,
        mcp_type: str = "sse",
        enable_mcp_logging: bool = True,
        mcp_logging_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the FastAPIWorker with a FastAPI app instance.
        If no secret is provided, the worker will use the ARCADE_WORKER_SECRET environment variable.

        Args:
            app: The FastAPI app to host the worker in
            secret: Optional secret for authorization
            disable_auth: Whether to disable authorization
            otel_meter: Optional OpenTelemetry meter
            enable_mcp: Whether to enable MCP support
            mcp_config: Configuration for MCP components
            mcp_type: Type of MCP transport ("sse", "stdio", or "both")
            enable_mcp_logging: Whether to enable MCP logging middleware
            mcp_logging_config: Configuration for MCP logging middleware
        """
        super().__init__(secret, disable_auth, otel_meter)
        self.app = app
        self.router = FastAPIRouter(app, self)
        self.register_routes(self.router)

        # Initialize components
        self.components: list[WorkerComponent] = []

        # Enable MCP if requested
        if enable_mcp:
            config = mcp_config or {}

            # Add logging middleware if enabled
            if enable_mcp_logging:
                logging_middleware = create_mcp_logging_middleware(**(mcp_logging_config or {}))
                if logging_middleware:
                    config["middleware"] = [logging_middleware]

            self._initialize_mcp(mcp_type, config)

    def _initialize_mcp(self, mcp_type: str, config: dict[str, Any]) -> None:
        """Initialize MCP components based on the requested type."""
        if mcp_type == "sse" or mcp_type == "both":
            mcp_sse = create_mcp_sse_component(self, self.app, **config)
            if mcp_sse:
                self.components.append(mcp_sse)
                print("Registered MCP SSE component")

        # Register all components with the router
        for component in self.components:
            component.register(self.router)


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
        self, endpoint_path: str, handler: Callable, method: str, require_auth: bool = True
    ) -> None:
        """
        Add a route to the FastAPI application.
        """
        self.app.add_api_route(
            f"{self.worker.base_path}/{endpoint_path}",
            self._wrap_handler(handler, require_auth),
            methods=[method],
        )
