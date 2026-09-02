from typing import Any, TypeVar

from arcade_core.log_extras import build_tool_error_span_attributes
from arcade_core.resource_schema import (
    ListResourcesParams,
    ListResourcesResult,
    ReadResourceParams,
    ReadResourceResult,
)
from arcade_core.resources import InvalidCursorError, ResourceNotFoundError
from arcade_core.schema import (
    ToolCallRequest,
    ToolCallResponse,
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel, ValidationError

from arcade_serve.core.common import (
    CatalogResponse,
    HealthCheckResponse,
    InvalidRequestParamsError,
    RequestData,
    Router,
    WorkerComponent,
)

_P = TypeVar("_P", bound=BaseModel)


def _caller_params(model: type[_P], body: Any) -> _P:
    """Build an endpoint's params from the caller's body."""
    try:
        return model.model_validate(body or {})
    except ValidationError as e:
        raise InvalidRequestParamsError(f"{e.error_count()} error(s)") from e


class CatalogComponent(WorkerComponent):
    def register(self, router: Router) -> None:
        """
        Register the catalog route with the router.
        """
        router.add_route(
            "tools",
            self,
            method="GET",
            response_type=CatalogResponse,
            operation_id="get_catalog",
            description="Get the catalog of tools",
            summary="Get the catalog of tools",
            tags=["Arcade"],
        )

    async def __call__(self, request: RequestData) -> CatalogResponse:
        """
        Handle the request to get the catalog.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("Catalog"):
            return self.worker.get_catalog()


class CallToolComponent(WorkerComponent):
    def register(self, router: Router) -> None:
        """
        Register the call tool route with the router.
        """
        router.add_route(
            "tools/invoke",
            self,
            method="POST",
            response_type=ToolCallResponse,
            operation_id="call_tool",
            description="Call a tool",
            summary="Call a tool",
            tags=["Arcade"],
        )

    async def __call__(self, request: RequestData) -> ToolCallResponse:
        """
        Handle the request to call (invoke) a tool.
        """
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("CallTool") as current_span:
            call_tool_request_data = request.body_json
            call_tool_request = _caller_params(ToolCallRequest, call_tool_request_data)

            current_span.set_attribute("tool_name", str(call_tool_request.tool.name))
            current_span.set_attribute("toolkit_version", str(call_tool_request.tool.version))
            current_span.set_attribute("toolkit_name", str(call_tool_request.tool.toolkit))
            if hasattr(self.worker, "environment"):
                current_span.set_attribute("environment", self.worker.environment)

            response = await self.worker.call_tool(call_tool_request)
            if response.output and response.output.error:
                for key, value in build_tool_error_span_attributes(response.output.error).items():
                    current_span.set_attribute(key, value)
            return response


class HealthCheckComponent(WorkerComponent):
    def register(self, router: Router) -> None:
        """
        Register the health check route with the router.
        """
        router.add_route(
            "health",
            self,
            method="GET",
            response_type=HealthCheckResponse,
            operation_id="health_check",
            description="Health check",
            summary="Health check",
            tags=["Arcade"],
            require_auth=False,
        )

    async def __call__(self, request: RequestData) -> HealthCheckResponse:
        """
        Handle the request to check the health of the worker.
        """
        return self.worker.health_check()


class ListResourcesComponent(WorkerComponent):
    def register(self, router: Router) -> None:
        """
        Register the resource listing route with the router.
        """
        router.add_route(
            "resources/list",
            self,
            method="POST",
            response_type=ListResourcesResult,
            operation_id="list_resources",
            description="List the resources this worker serves",
            summary="List resources",
            tags=["Arcade"],
            # An absent optional field is omitted rather than sent as null,
            # because a null is not the same thing as an unset one to a client
            # reading this. FastAPI serializes every unset field as null without
            # it.
            response_model_exclude_none=True,
        )

    async def __call__(self, request: RequestData) -> ListResourcesResult:
        """
        Handle the request to list resources.
        """
        tracer = trace.get_tracer(__name__)
        # A refused cursor is an answer this endpoint gives, so it must not
        # land as a failed span.
        with tracer.start_as_current_span(
            "ListResources", record_exception=False, set_status_on_exception=False
        ) as current_span:
            try:
                params = _caller_params(ListResourcesParams, request.body_json)
                result = self.worker.list_resources(params.cursor)
            except (InvalidCursorError, InvalidRequestParamsError):
                current_span.set_attribute("outcome", "invalid_request")
                raise
            except Exception as e:
                current_span.record_exception(e)
                current_span.set_status(Status(StatusCode.ERROR))
                raise
            current_span.set_attribute("outcome", "success")
            return result


class ReadResourceComponent(WorkerComponent):
    def register(self, router: Router) -> None:
        """
        Register the resource read route with the router.
        """
        router.add_route(
            "resources/read",
            self,
            method="POST",
            response_type=ReadResourceResult,
            operation_id="read_resource",
            description="Read a resource by URI",
            summary="Read a resource",
            tags=["Arcade"],
            response_model_exclude_none=True,
        )

    async def __call__(self, request: RequestData) -> ReadResourceResult:
        """
        Handle the request to read a resource.
        """
        tracer = trace.get_tracer(__name__)
        # A URI this worker does not serve is a routine answer. Left to the
        # default, every render of a stale interface arrives as an error span
        # carrying a stack trace.
        with tracer.start_as_current_span(
            "ReadResource", record_exception=False, set_status_on_exception=False
        ) as current_span:
            try:
                params = _caller_params(ReadResourceParams, request.body_json)
                current_span.set_attribute("resource_uri", params.uri)
                result = self.worker.read_resource(params.uri)
            except ResourceNotFoundError:
                current_span.set_attribute("outcome", "not_found")
                raise
            except InvalidRequestParamsError:
                current_span.set_attribute("outcome", "invalid_request")
                raise
            except Exception as e:
                current_span.record_exception(e)
                current_span.set_status(Status(StatusCode.ERROR))
                raise
            current_span.set_attribute("outcome", "success")
            return result
