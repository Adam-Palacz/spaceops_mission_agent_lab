from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from apps.agent.nodes import report
from apps.agent.opa_client import opa_allow
from apps.tracing import current_w3c_trace_headers, extract_w3c_context_from_headers


def _in_memory_provider() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def test_distributed_context_continuity_agent_to_mcp_simulated():
    provider, exporter = _in_memory_provider()
    agent_tracer = provider.get_tracer("tests.agent")
    mcp_tracer = provider.get_tracer("tests.mcp")
    with agent_tracer.start_as_current_span("agent.run", kind=SpanKind.INTERNAL):
        outbound_headers = current_w3c_trace_headers()
        assert "traceparent" in outbound_headers
        assert "authorization" not in {k.lower() for k in outbound_headers}
        parent_ctx = extract_w3c_context_from_headers(outbound_headers)
        with mcp_tracer.start_as_current_span(
            "mcp.telemetry.query_telemetry",
            context=parent_ctx,
            kind=SpanKind.SERVER,
        ):
            pass
    spans = exporter.get_finished_spans()
    assert len(spans) >= 2
    agent_span = next(s for s in spans if s.name == "agent.run")
    mcp_span = next(s for s in spans if s.name == "mcp.telemetry.query_telemetry")
    assert agent_span.context.trace_id == mcp_span.context.trace_id


def test_opa_deny_sets_error_span_status(monkeypatch):
    provider, exporter = _in_memory_provider()
    monkeypatch.setattr(
        "apps.agent.opa_client.with_retry_sync",
        lambda *args, **kwargs: {"result": False},
    )
    monkeypatch.setattr(
        "apps.agent.opa_client.get_tracer",
        lambda *_args, **_kwargs: provider.get_tracer("tests.opa"),
    )
    allowed = opa_allow({"action_type": "change_config"}, "inc-ps19")
    assert allowed is False
    spans = exporter.get_finished_spans()
    opa_span = next(s for s in spans if s.name == "policy.opa.evaluate")
    assert opa_span.status.status_code == StatusCode.ERROR


def test_report_trace_link_only_for_valid_trace_id():
    invalid = report(
        {
            "incident_id": "inc-1",
            "trace_id": "inc-1",
            "hypotheses": [],
            "citations": [],
            "plan": [],
            "escalated": False,
        }
    )
    assert (invalid.get("report") or {}).get("trace_link") == ""

    valid = report(
        {
            "incident_id": "inc-2",
            "trace_id": "a" * 32,
            "hypotheses": [],
            "citations": [],
            "plan": [],
            "escalated": False,
        }
    )
    trace_link = (valid.get("report") or {}).get("trace_link") or ""
    assert trace_link.endswith("/trace/" + ("a" * 32))
