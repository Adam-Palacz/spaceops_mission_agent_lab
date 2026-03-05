"""
SpaceOps — OpenTelemetry setup (S1.10): TracerProvider, OTLP export to Collector/Jaeger.
Structured logging (JSON with trace_id when in span). Call init_telemetry() once at app startup.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

_tracer_provider: TracerProvider | None = None
_service_name = "spaceops"
_logging_configured = False


class JsonTraceFormatter(logging.Formatter):
    """S1.10: JSON log line with trace_id from current span when available."""

    def format(self, record: logging.LogRecord) -> str:
        trace_id = None
        try:
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                if ctx and ctx.trace_id:
                    trace_id = format(ctx.trace_id, "032x")
        except Exception:
            pass
        out = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if trace_id:
            out["trace_id"] = trace_id
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


def _get_endpoint() -> str | None:
    from config import settings

    endpoint = (getattr(settings, "otel_exporter_otlp_endpoint", None) or "").strip()
    if not endpoint:
        return None
    # gRPC often expects host:port without scheme
    if endpoint.startswith("http://"):
        endpoint = endpoint.replace("http://", "", 1)
    elif endpoint.startswith("https://"):
        endpoint = endpoint.replace("https://", "", 1)
    return endpoint or None


def init_telemetry(service_name: str = "spaceops") -> None:
    """
    Initialize TracerProvider and OTLP exporter. Idempotent.
    If otel_exporter_otlp_endpoint is empty, tracing is no-op (no export).
    Always sets up structured (JSON) logging when called.
    """
    global _tracer_provider, _service_name, _logging_configured
    _service_name = service_name
    if not _logging_configured:
        _setup_structured_logging()
        _logging_configured = True
    if _tracer_provider is not None:
        return
    endpoint = _get_endpoint()
    if not endpoint:
        return
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        return
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer_provider = provider


def _setup_structured_logging() -> None:
    """Configure root logger with JSON formatter (trace_id when in span)."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonTraceFormatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)


def get_tracer(name: str, version: str = "0.1.0"):
    """Return a Tracer for the given name (e.g. 'apps.agent', 'apps.api')."""
    init_telemetry()
    return trace.get_tracer(name, version)


def get_current_trace_id_hex() -> str | None:
    """
    Return the current span's trace_id as 32-char hex, or None if no span/export disabled.
    Use for Jaeger UI URL: {jaeger_ui_url}/trace/{trace_id}
    """
    span = trace.get_current_span()
    if not span or not span.is_recording():
        return None
    ctx = span.get_span_context()
    if not ctx or ctx.trace_id == 0:
        return None
    return format(ctx.trace_id, "032x")
