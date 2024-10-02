import logging
import os
from typing import Optional

from fastapi import FastAPI
from opentelemetry import _logs, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import Meter, get_meter_provider, set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class ShutdownError(Exception):
    pass


class OTELHandler:
    def __init__(self, app: FastAPI, enable: bool = True, log_level: int = logging.INFO):
        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer_span_exporter: Optional[OTLPSpanExporter] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._meter_reader: Optional[PeriodicExportingMetricReader] = None
        self._otlp_metric_exporter: Optional[OTLPMetricExporter] = None
        self._logger_provider: Optional[LoggerProvider] = None
        self._log_processor: Optional[BatchLogRecordProcessor] = None
        self.environment = os.environ.get("ARCADE_ENVIRONMENT", "local")

        if enable:
            logging.info(
                "🔎 Initializing OpenTelemetry. Use environment variables to configure the connection"
            )
            self.resource = Resource(
                attributes={SERVICE_NAME: "arcade-actor", "environment": self.environment}
            )

            self._init_tracer()
            self._init_metrics()
            self._init_logging(log_level)

            FastAPIInstrumentor().instrument_app(app)

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
        _logs.set_logger_provider(self._logger_provider)

        # Create a batch span processor and add the exporter
        self._log_processor = BatchLogRecordProcessor(otlp_log_exporter)
        self._logger_provider.add_log_record_processor(self._log_processor)

        handler = LoggingHandler(level=log_level, logger_provider=self._logger_provider)
        logging.getLogger().addHandler(handler)

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
        self._shutdown_tracer()
        self._shutdown_metrics()
        self._shutdown_logging()
