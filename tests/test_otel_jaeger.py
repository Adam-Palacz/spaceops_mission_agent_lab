"""
S1.10: OTel + Jaeger — report trace link, spans, structured logging.
"""
from __future__ import annotations

import json
import logging
import re

import pytest

from apps.telemetry import (
    get_current_trace_id_hex,
    get_tracer,
    init_telemetry,
)
from apps.agent.graph import run_pipeline


def test_report_contains_jaeger_trace_url():
    """S1.10: Report contains a clickable/copy-paste Jaeger URL that opens the correct trace."""
    try:
        result = run_pipeline("trace-url-test", {"ref": "test"})
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        raise
    report = result.get("report") or {}
    trace_link = report.get("trace_link") or ""
    assert trace_link.startswith("http"), "trace_link must be a URL"
    assert "/trace/" in trace_link, "trace_link must point to Jaeger trace page"
    # trace_id segment (incident_id or 32-char hex)
    match = re.search(r"/trace/([^/?#]+)", trace_link)
    assert match, "trace_link must have trace id segment"
    trace_id = match.group(1)
    assert len(trace_id) >= 1 and len(trace_id) <= 64, "trace_id segment should be incident_id or 32-char hex"


def test_trace_id_in_state_when_otel_enabled(monkeypatch):
    """When OTel endpoint is set, run_pipeline sets trace_id in state (32-char hex for Jaeger)."""
    # Use a non-empty endpoint so TracerProvider is created and spans are recorded
    monkeypatch.setattr("config.settings.otel_exporter_otlp_endpoint", "http://localhost:4317")
    # Reset provider so init_telemetry picks up the new endpoint (test isolation)
    import apps.telemetry as tel
    tel._tracer_provider = None
    try:
        init_telemetry("spaceops-test")
        tracer = get_tracer("test")
        with tracer.start_as_current_span("test.span") as span:
            trace_id = get_current_trace_id_hex()
            assert trace_id is not None
            assert len(trace_id) == 32
            assert all(c in "0123456789abcdef" for c in trace_id), "trace_id must be 32-char hex"
    finally:
        tel._tracer_provider = None


def test_structured_log_format_includes_trace_id_when_in_span(monkeypatch):
    """S1.10: Logs contain trace_id for correlation when inside a span."""
    monkeypatch.setattr("config.settings.otel_exporter_otlp_endpoint", "http://localhost:4317")
    import apps.telemetry as tel
    tel._tracer_provider = None
    tel._logging_configured = False
    try:
        init_telemetry("spaceops-test")
        tracer = get_tracer("test")
        with tracer.start_as_current_span("log.test"):
            log = logging.getLogger("test.otel")
            # Capture what the formatter would output
            handler = logging.StreamHandler()
            handler.setFormatter(tel.JsonTraceFormatter())
            record = log.makeRecord("test.otel", logging.INFO, __file__, 0, "hello", (), None)
            line = handler.format(record)
        data = json.loads(line)
        assert "trace_id" in data
        assert len(data["trace_id"]) == 32
    finally:
        tel._tracer_provider = None
