import logging
import os
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, ClassVar

from arcade_core.catalog import ToolCatalog, Toolkit
from arcade_core.executor import ToolExecutor
from arcade_core.schema import (
    ToolCallRequest,
    ToolCallResponse,
    ToolDefinition,
)
from opentelemetry import trace
from opentelemetry.metrics import Meter

from arcade_serve.core.common import Router, Worker
from arcade_serve.core.components import (
    CallToolComponent,
    CatalogComponent,
    HealthCheckComponent,
    WorkerComponent,
)

logger = logging.getLogger(__name__)


class BaseWorker(Worker):
    """
    A base worker class that provides a default implementation for registering tools and invoking them.
    Worker implementations for specific web frameworks will inherit from this class.
    """

    base_path = "/worker"  # By default, prefix all our routes with /worker

    default_components: ClassVar[tuple[type[WorkerComponent], ...]] = (
        CatalogComponent,
        CallToolComponent,
        HealthCheckComponent,
    )

    def __init__(
        self,
        secret: str | None = None,
        disable_auth: bool = True,
        otel_meter: Meter | None = None,
    ) -> None:
        """
        Initialize the BaseWorker with an empty ToolCatalog.
        If no secret is provided, the worker will use the ARCADE_WORKER_SECRET environment variable.
        """
        self.catalog = ToolCatalog()
        self.disable_auth = disable_auth
        if disable_auth:
            logger.warning(
                "Warning: Worker is running without authentication. Not recommended for production."
            )

        self.secret = self._set_secret(secret, disable_auth)
        self.environment = os.environ.get("ARCADE_ENVIRONMENT", "local")

        self.tool_counter = None
        if otel_meter:
            self.tool_counter = otel_meter.create_counter(
                "tool_call", "requests", "Total number of tools called"
            )

    def _set_secret(self, secret: str | None, disable_auth: bool) -> str:
        if disable_auth:
            return ""

        # If secret is provided, use it
        if secret:
            return secret

        # If secret is not provided, try to get it from environment variables
        env_secret = os.environ.get("ARCADE_WORKER_SECRET")
        if env_secret:
            return env_secret

        raise ValueError(
            "No secret provided for worker. Set the ARCADE_WORKER_SECRET environment variable."
        )

    def get_catalog(self) -> list[ToolDefinition]:
        """
        Get the catalog as a list of ToolDefinitions.
        """
        return [tool.definition for tool in self.catalog]

    def register_tool(self, tool: Callable, toolkit_name: str) -> None:
        """
        Register a tool to the catalog.
        """
        self.catalog.add_tool(tool, toolkit_name)

    def register_toolkit(self, toolkit: Toolkit) -> None:
        """
        Register a toolkit to the catalog.
        """
        self.catalog.add_toolkit(toolkit)

    async def call_tool(self, tool_request: ToolCallRequest) -> ToolCallResponse:
        """
        Call (invoke) a tool using the ToolExecutor.
        """
        tool_fqname = tool_request.tool.get_fully_qualified_name()

        try:
            materialized_tool = self.catalog.get_tool(tool_fqname)
        except KeyError:
            raise ValueError(
                f"Tool {tool_fqname} not found in catalog with toolkit version {tool_request.tool.version}."
            )

        start_time = time.time()

        if self.tool_counter:
            self.tool_counter.add(
                1,
                {
                    "tool_name": tool_fqname.name,
                    "toolkit_version": str(tool_fqname.toolkit_version),
                    "toolkit_name": tool_fqname.toolkit_name,
                    "environment": self.environment,
                },
            )
        execution_id = tool_request.execution_id or ""
        logger.info(
            f"{execution_id} | Calling tool: {tool_fqname} version: {tool_request.tool.version}"
        )
        logger.debug(f"{execution_id} | Tool inputs: {tool_request.inputs}")

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("RunTool"):
            output = await ToolExecutor.run(
                func=materialized_tool.tool,
                definition=materialized_tool.definition,
                input_model=materialized_tool.input_model,
                output_model=materialized_tool.output_model,
                context=tool_request.context,
                **tool_request.inputs or {},
            )

        end_time = time.time()  # End time in seconds
        duration_ms = (end_time - start_time) * 1000  # Convert to milliseconds

        if output.error:
            logger.warning(
                f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} failed"
            )
            logger.warning(f"{execution_id} | Tool error: {output.error.message}")
            logger.warning(
                f"{execution_id} | Tool developer message: {output.error.developer_message}"
            )
            logger.debug(
                f"{execution_id} | duration: {duration_ms}ms | Tool output: {output.value}"
            )
            if output.error.traceback_info:
                logger.debug(f"{execution_id} | Tool traceback: {output.error.traceback_info}")
        else:
            logger.info(
                f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} success"
            )
            logger.debug(
                f"{execution_id} | duration: {duration_ms}ms | Tool output: {output.value}"
            )

        return ToolCallResponse(
            execution_id=execution_id,
            duration=duration_ms,
            finished_at=datetime.now().isoformat(),
            success=not output.error,
            output=output,
        )

    def health_check(self) -> dict[str, Any]:
        """
        Provide a health check that serves as a heartbeat of worker health.
        """
        return {"status": "ok", "tool_count": str(len(self.catalog))}

    def get_tool_schema(self, tool_name: str) -> dict[str, Any]:
        """
        Get the input and output schema for a specific tool.
        """
        try:
            tool = self.catalog.get_tool_by_name(tool_name)
            definition = tool.definition

            # Convert input parameters to JSON Schema
            input_properties = {}
            required = []
            for param in definition.input.parameters:
                input_properties[param.name] = self._value_schema_to_json_schema(param.value_schema)
                if param.required:
                    required.append(param.name)
                # Add description if available
                if param.description:
                    input_properties[param.name]["description"] = param.description

            input_schema = {
                "type": "object",
                "properties": input_properties,
                "required": required,
            }

            # Convert output schema
            output_schema = None
            if definition.output.value_schema:
                output_schema = self._value_schema_to_json_schema(definition.output.value_schema)
                if definition.output.description:
                    output_schema["description"] = definition.output.description
            else:
                output_schema = {"type": "null"}

            return {
                "tool_name": str(definition.get_fully_qualified_name()),
                "description": definition.description,
                "input": input_schema,
                "output": output_schema,
            }
        except ValueError as e:
            raise ValueError(f"Tool '{tool_name}' not found") from e

    def _value_schema_to_json_schema(self, value_schema: Any) -> dict[str, Any]:
        """Convert ValueSchema to JSON Schema format."""
        if not value_schema:
            return {"type": "null"}

        # Map Arcade types to JSON Schema types
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
            "json": "object",
            "array": "array",
        }

        result: dict[str, Any] = {"type": type_mapping.get(value_schema.val_type, "object")}

        # Handle enums
        if value_schema.enum:
            result["enum"] = value_schema.enum

        # Handle arrays
        if value_schema.val_type == "array" and value_schema.inner_val_type:
            result["items"] = {"type": type_mapping.get(value_schema.inner_val_type, "object")}

        # Handle nested properties for objects
        if (
            value_schema.val_type == "json"
            and hasattr(value_schema, "properties")
            and value_schema.properties
        ):
            result["properties"] = {}
            for prop_name, prop_schema in value_schema.properties.items():
                result["properties"][prop_name] = self._value_schema_to_json_schema(prop_schema)

        return result

    def register_routes(self, router: Router) -> None:
        """
        Register the necessary routes to the application.
        """
        for component_cls in self.default_components:
            component_cls(self).register(router)
