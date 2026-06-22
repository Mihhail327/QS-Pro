import logging
import os
import sys
import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def add_otel_trace_info(logger, method_name, event_dict):
    """Processor to inject trace_id and span_id into log records."""
    try:
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None
        if span_context and span_context.is_valid:
            event_dict["trace_id"] = f"{span_context.trace_id:032x}"
            event_dict["span_id"] = f"{span_context.span_id:016x}"
    except Exception:
        pass
    return event_dict

def setup_logging_and_telemetry(app):
    # 1. Initialize OpenTelemetry Tracer Provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI app
    FastAPIInstrumentor.instrument_app(app)

    # 2. Configure structlog
    is_production = (
        os.getenv("ENV", "").lower().startswith("prod") or
        os.getenv("ENVIRONMENT", "").lower().startswith("prod")
    )

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.contextvars.merge_contextvars,
        add_otel_trace_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_production:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )

    # Stream handler configuration
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger integration
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Configure stdlib uvicorn loggers to use the same formatter
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        log = logging.getLogger(logger_name)
        log.handlers = [handler]
        log.propagate = False

    # Configure structlog wrapper
    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
