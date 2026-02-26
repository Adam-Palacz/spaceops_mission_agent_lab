"""
SpaceOps Agent — LangGraph pipeline: Triage → Investigate → [Check escalation] → Decide or Report (S1.7, S1.8).
S1.10: OTel spans per node; trace_id in state for Jaeger URL in report.
S1.12: Run-level timeout and token budget; on timeout/limit → escalation (NF6).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from langgraph.graph import END, StateGraph

from config import settings
from apps.agent.state import AgentState
from apps.agent.nodes import (
    act,
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
    workflow.add_node(
        "check_escalation", _wrap_node("check_escalation", check_escalation)
    )
    workflow.add_node("decide", _wrap_node("decide", decide))
    workflow.add_node("act", _wrap_node("act", act))
    workflow.add_node("build_report", _wrap_node("build_report", report_node_fn))
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "investigate")
    workflow.add_edge("investigate", "check_escalation")
    workflow.add_conditional_edges(
        "check_escalation",
        _route_after_escalation,
        {"build_report": "build_report", "decide": "decide"},
    )
    workflow.add_edge("decide", "act")
    workflow.add_edge("act", "build_report")
    workflow.add_edge("build_report", END)
    return workflow.compile()


def _run_timeout_escalation_result(incident_id: str, trace_id: str) -> dict:
    """S1.12: Build result dict when run hits timeout (NF6, F10)."""
    from config import settings as s

    packet = {
        "reason": "run_timeout",
        "what_we_know": [
            f"Incident {incident_id}",
            "Run exceeded agent_run_timeout_seconds; stopped.",
        ],
        "what_we_dont_know": ["Pipeline did not complete; outcome unknown."],
        "what_to_check": [
            "Increase agent_run_timeout_seconds or simplify payload.",
            "Check for slow LLM or MCP responses.",
        ],
    }
    trace_url = f"{s.jaeger_ui_url}/trace/{trace_id}"
    report = {
        "incident_id": incident_id,
        "executive_summary": f"[ESCALATION] Incident {incident_id}: handoff to human. Reason: run_timeout.",
        "evidence": [],
        "citation_refs": [],
        "proposed_actions": [],
        "rollback": "N/A",
        "trace_link": trace_url,
        "escalation_packet": packet,
        "handoff": "Run timed out; manual review required.",
    }
    return {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "escalated": True,
        "escalation_packet": packet,
        "report": report,
    }


def run_pipeline(incident_id: str, payload: dict | None = None) -> dict:
    """Run the pipeline and return final state (includes report). S1.10: root span; S1.12: run timeout."""
    init_telemetry()
    graph = build_graph()
    tracer = get_tracer("apps.agent")
    run_timeout = max(0, getattr(settings, "agent_run_timeout_seconds", 0))
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("incident_id", incident_id)
        trace_id_hex = get_current_trace_id_hex()
        trace_id = trace_id_hex or incident_id
        initial: AgentState = {
            "incident_id": incident_id,
            "trace_id": trace_id,
            "payload": payload or {},
            "tokens_used": 0,
            "llm_calls_used": 0,
        }
        if run_timeout:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(graph.invoke, initial)
                try:
                    result = fut.result(timeout=run_timeout)
                except FuturesTimeoutError:
                    return _run_timeout_escalation_result(incident_id, trace_id)
        else:
            result = graph.invoke(initial)
    return result
