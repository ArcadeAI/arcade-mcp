import logging
import os
import urllib.parse
import warnings
from typing import Any, Literal, Optional

# requests scans the environment for chardet at import time and emits a
# RequestsDependencyWarning when chardet>=6 is present (e.g. pulled in by tox).
# The warning is noise: requests uses charset-normalizer regardless of chardet.
warnings.filterwarnings(
    "ignore",
    message="urllib3.*chardet.*",
    module="requests",
)

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.metrics import Meter, get_meter_provider, set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv._incubating.attributes import deployment_attributes
from opentelemetry.semconv.attributes import service_attributes

from arcade_serve.fastapi import _arcade_telemetry

EXCLUDED_URLS = "/worker/health"
EXCLUDED_SPANS: list[Literal["send", "receive"]] = ["send", "receive"]


class ShutdownError(Exception):
    pass


class OTELHandler:
    def __init__(
        self,
        enable: bool = True,
        log_level: int = logging.INFO,
        *,
        service_name: str = "worker",
        service_version: str = "",
    ):
        self.enable = enable
        self.log_level = log_level
        self.service_name = service_name
        self.service_version = service_version
        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer_span_exporter: Optional[OTLPSpanExporter] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._meter_reader: Optional[PeriodicExportingMetricReader] = None
        self._otlp_metric_exporter: Optional[OTLPMetricExporter] = None
        self._logger_provider: Optional[LoggerProvider] = None
        self._log_processor: Optional[BatchLogRecordProcessor] = None
        self._arcade_telemetry_handle: Optional[Any] = None
        self.environment = os.environ.get("ARCADE_ENVIRONMENT", "local")

    def instrument_app(self, app: FastAPI) -> None:
        if not self.enable:
            return

        if _arcade_telemetry.is_available():
            logging.info("🔎 Initializing OpenTelemetry via arcade-telemetry")
            handle = _arcade_telemetry.init_providers(
                service_name=self.service_name,
                environment=self.environment,
                version=self.service_version,
                log_level=self.log_level,
            )
            if handle is not None:
                self._arcade_telemetry_handle = handle
                FastAPIInstrumentor().instrument_app(
                    app, excluded_urls=EXCLUDED_URLS, exclude_spans=EXCLUDED_SPANS
                )
                # Pass tracer_provider=None so instrumentors pick up the global
                # provider set by arcade-telemetry.
                HTTPXClientInstrumentor()._instrument(tracer_provider=None)
                AioHttpClientInstrumentor()._instrument(tracer_provider=None)
                RequestsInstrumentor()._instrument(tracer_provider=None)
                return
            # init_providers returned None (arcade-telemetry import race or
            # internal opt-out) — fall through to the in-house OTLP setup so
            # shutdown() has something to tear down.

        logging.info(
            "🔎 Initializing OpenTelemetry. Use environment variables to configure the connection"
        )
        resource_attrs: dict[str, str] = {
            service_attributes.SERVICE_NAME: self.service_name,
            deployment_attributes.DEPLOYMENT_ENVIRONMENT_NAME: self.environment,
        }
        if self.service_version:
            resource_attrs[service_attributes.SERVICE_VERSION] = self.service_version
        self.resource = Resource(attributes=resource_attrs)

        self._init_tracer()
        self._init_metrics()
        self._init_logging(self.log_level)
        FastAPIInstrumentor().instrument_app(
            app, excluded_urls=EXCLUDED_URLS, exclude_spans=EXCLUDED_SPANS
        )
        HTTPXClientInstrumentor()._instrument(tracer_provider=self._tracer_provider)
        AioHttpClientInstrumentor()._instrument(tracer_provider=self._tracer_provider)
        RequestsInstrumentor()._instrument(tracer_provider=self._tracer_provider)

    def _init_tracer(self) -> None:
        self._tracer_provider = TracerProvider(resource=self.resource)
        trace.set_tracer_provider(self._tracer_provider)

        # Create an OTLP exporter
        self._tracer_span_exporter = OTLPSpanExporter()

        try:
            self._tracer_span_exporter.export([trace.get_tracer(__name__).start_span("ping")])
        except Exception as e:
            raise ConnectionError(
                f"Could not connect to OpenTelemetry Tracer endpoint. Check OpenTelemetry configuration or disable: {e}"
            )

        # Create a batch span processor and add the exporter
        span_processor = BatchSpanProcessor(self._tracer_span_exporter)
        self._tracer_provider.add_span_processor(span_processor)

    def _init_metrics(self) -> None:
        self._otlp_metric_exporter = OTLPMetricExporter()

        self._meter_reader = PeriodicExportingMetricReader(self._otlp_metric_exporter)

        self._meter_provider = MeterProvider(
            metric_readers=[self._meter_reader], resource=self.resource
        )

        set_meter_provider(self._meter_provider)

    def get_meter(self) -> Meter:
        return get_meter_provider().get_meter(__name__)

    def _init_logging(self, log_level: int) -> None:
        otlp_log_exporter = OTLPLogExporter()

        self._logger_provider = LoggerProvider(resource=self.resource)
        set_logger_provider(self._logger_provider)

        # Create a batch span processor and add the exporter
        self._log_processor = BatchLogRecordProcessor(otlp_log_exporter)
        self._logger_provider.add_log_record_processor(self._log_processor)

        handler = LoggingHandler(level=log_level, logger_provider=self._logger_provider)
        logging.getLogger().addHandler(handler)

        # Create a filter for urllib3 connection logs related to OpenTelemetry
        class OTELConnectionFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                # Filter out connection logs to OpenTelemetry endpoints
                parsed_url = urllib.parse.urlparse(
                    os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
                )
                domain = parsed_url.netloc.split(":")[0]
                return not (domain and domain in str(getattr(record, "args", ())))

        # Apply the filter to the urllib3 logger
        urllib3_logger = logging.getLogger("urllib3.connectionpool")
        urllib3_logger.addFilter(OTELConnectionFilter())

    def _shutdown_tracer(self) -> None:
        if self._tracer_span_exporter is None:
            raise ShutdownError("Tracer provider not initialized. Failed to shutdown")
        self._tracer_span_exporter.shutdown()

    def _shutdown_metrics(self) -> None:
        if self._otlp_metric_exporter is None:
            raise ShutdownError("Meter provider not initialized. Failed to shutdown")
        self._otlp_metric_exporter.shutdown()

    def _shutdown_logging(self) -> None:
        if self._logger_provider is None:
            raise ShutdownError("Log provider not initialized. Failed to shutdown")
        self._logger_provider.shutdown()

    def shutdown(self) -> None:
        if self._arcade_telemetry_handle is not None:
            _arcade_telemetry.shutdown(self._arcade_telemetry_handle)
            self._arcade_telemetry_handle = None
            return
        self._shutdown_tracer()
        self._shutdown_metrics()
        self._shutdown_logging()
