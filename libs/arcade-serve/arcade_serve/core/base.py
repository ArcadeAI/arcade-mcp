import atexit
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Callable, ClassVar

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
    _cache_dir = "/tmp/arcade_worker_cache"  # noqa: S108

    default_components: ClassVar[tuple[type[WorkerComponent], ...]] = (
        CatalogComponent,
        CallToolComponent,
        HealthCheckComponent,
    )

    def __init__(
        self,
        secret: str | None = None,
        disable_auth: bool = False,
        otel_meter: Meter | None = None,
    ) -> None:
        """
        Initialize the BaseWorker with an empty ToolCatalog.
        If no secret is provided, the worker will use the ARCADE_WORKER_SECRET environment variable.
        """
        self._catalog_cache_path: str | None = None
        self._catalog = ToolCatalog()
        self._cache_enabled = os.environ.get("CACHE_WORKER_CATALOG", "false").lower() == "true"
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

    @property
    def catalog(self) -> ToolCatalog:
        """Get the worker's tool catalog."""
        return self._catalog

    @catalog.setter
    def catalog(self, value: ToolCatalog) -> None:
        """Set the worker's tool catalog and write it to cache if enabled."""
        self._catalog = value

        if not self._cache_enabled:
            return

        # Clean up old cache file if one exists
        if self._catalog_cache_path and os.path.exists(self._catalog_cache_path):
            try:
                os.remove(self._catalog_cache_path)
            except OSError as e:
                logger.warning(f"Failed to remove old cache file {self._catalog_cache_path}: {e}")

        # Compute hash of catalog contents
        catalog_hash = self._compute_catalog_hash()

        # Create cache directory if it doesn't exist
        os.makedirs(self._cache_dir, exist_ok=True)

        # Write cache file
        cache_filename = f"catalog_{catalog_hash}.json"
        self._catalog_cache_path = os.path.join(self._cache_dir, cache_filename)
        self._write_catalog_cache()

        # Register cleanup handler
        atexit.register(self._cleanup_catalog_cache)

    def _compute_catalog_hash(self) -> str:
        """Compute a hash of the catalog contents for cache file naming."""
        # Serialize all tool definitions to JSON for hashing
        tool_definitions = [tool.definition.model_dump() for tool in self._catalog]
        # Sort by fully_qualified_name for consistent hashing
        tool_definitions.sort(key=lambda td: td.get("fully_qualified_name", ""))
        catalog_json = json.dumps(tool_definitions, sort_keys=True)
        # Use SHA256 for hash
        hash_obj = hashlib.sha256(catalog_json.encode("utf-8"))
        return hash_obj.hexdigest()

    def _write_catalog_cache(self) -> None:
        """Write the catalog to disk as JSON."""
        try:
            tool_definitions = [tool.definition.model_dump() for tool in self._catalog]
            with open(self._catalog_cache_path, "w", encoding="utf-8") as f:
                json.dump(tool_definitions, f, indent=2)
            logger.debug(f"Wrote catalog cache to {self._catalog_cache_path}")
        except OSError as e:
            logger.warning(f"Failed to write catalog cache to {self._catalog_cache_path}: {e}")

    def _cleanup_catalog_cache(self) -> None:
        """Delete the catalog cache file on worker shutdown."""
        if self._catalog_cache_path and os.path.exists(self._catalog_cache_path):
            try:
                os.remove(self._catalog_cache_path)
                logger.debug(f"Cleaned up catalog cache file: {self._catalog_cache_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up cache file {self._catalog_cache_path}: {e}")

    def get_catalog(self) -> list[ToolDefinition]:
        """
        Get the catalog as a list of ToolDefinitions.
        Reads from cache file if caching is enabled and available, otherwise computes from in-memory catalog.
        """
        if (
            self._cache_enabled
            and self._catalog_cache_path
            and os.path.exists(self._catalog_cache_path)
        ):
            try:
                with open(self._catalog_cache_path, encoding="utf-8") as f:
                    catalog_data = json.load(f)
                # Deserialize JSON back to ToolDefinition objects
                return [ToolDefinition.model_validate(td) for td in catalog_data]
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Failed to read catalog cache from {self._catalog_cache_path}: {e}. "
                    "Falling back to in-memory catalog."
                )

        return [tool.definition for tool in self._catalog]

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
            if output.error.stacktrace:
                logger.debug(f"{execution_id} | Tool traceback: {output.error.stacktrace}")
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

    def register_routes(self, router: Router) -> None:
        """
        Register the necessary routes to the application.
        """
        # Initialize components list if it doesn't exist
        if not hasattr(self, "components"):
            self.components = []

        for component_cls in self.default_components:
            component = component_cls(self)
            component.register(router)
            self.components.append(component)
