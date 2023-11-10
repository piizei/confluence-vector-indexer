import logging
import os

from azure.core.settings import settings
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler
)
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


def setup():
    settings.tracing_implementation = "opentelemetry"
    if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING") is not None:
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        logger_provider = LoggerProvider()
        set_logger_provider(logger_provider)

        exporter = AzureMonitorLogExporter(
            connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
        )

        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        handler = LoggingHandler()

        # Attach LoggingHandler to root logger
        logging.getLogger().addHandler(handler)
    else:
        logging.warning("No application insights connection string found.")
