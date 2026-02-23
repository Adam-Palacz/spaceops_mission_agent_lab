"""
SpaceOps Agent — LangGraph pipeline: Triage → Investigate → [Check escalation] → Decide or Report (S1.7, S1.8).
S1.10: OTel spans per node; trace_id in state for Jaeger URL in report.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from apps.agent.state import AgentState
from apps.agent.nodes import (
    check_escalation,
    decide,
    investigate,
    report as report_node_fn,
    triage,
)
from apps.telemetry import get_tracer, get_current_trace_id_hex, init_telemetry


def _wrap_node(span_name: str, node_fn):
    """S1.10: run node under a span; set incident_id attribute."""

    def wrapped(state: AgentState) -> dict:
        tracer = get_tracer("apps.agent")
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("incident_id", state.get("incident_id") or "unknown")
            return node_fn(state)

    return wrapped


def _route_after_escalation(state: AgentState) -> str:
    """If escalated, go to report; else go to decide (S1.8)."""
    return "build_report" if state.get("escalated") else "decide"


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("triage", _wrap_node("triage", triage))
    workflow.add_node("investigate", _wrap_node("investigate", investigate))
    workflow.add_node("check_escalation", _wrap_node("check_escalation", check_escalation))
    workflow.add_node("decide", _wrap_node("decide", decide))
    workflow.add_node("build_report", _wrap_node("build_report", report_node_fn))
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "investigate")
    workflow.add_edge("investigate", "check_escalation")
    workflow.add_conditional_edges("check_escalation", _route_after_escalation, {"build_report": "build_report", "decide": "decide"})
    workflow.add_edge("decide", "build_report")
    workflow.add_edge("build_report", END)
    return workflow.compile()


def run_pipeline(incident_id: str, payload: dict | None = None) -> dict:
    """Run the pipeline and return final state (includes report). S1.10: root span + trace_id for Jaeger URL."""
    init_telemetry()
    graph = build_graph()
    tracer = get_tracer("apps.agent")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("incident_id", incident_id)
        trace_id_hex = get_current_trace_id_hex()
        initial: AgentState = {
            "incident_id": incident_id,
            "trace_id": trace_id_hex or incident_id,
            "payload": payload or {},
        }
        result = graph.invoke(initial)
    return result
