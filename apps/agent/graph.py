"""
SpaceOps Agent — LangGraph pipeline: Triage → Investigate → [Check escalation] → Decide or Report (S1.7, S1.8).
No Act node yet. F10: when escalation conditions met, skip Decide and go to Report with escalation packet.
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


def _route_after_escalation(state: AgentState) -> str:
    """If escalated, go to report; else go to decide (S1.8)."""
    return "build_report" if state.get("escalated") else "decide"


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("triage", triage)
    workflow.add_node("investigate", investigate)
    workflow.add_node("check_escalation", check_escalation)
    workflow.add_node("decide", decide)
    workflow.add_node("build_report", report_node_fn)
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "investigate")
    workflow.add_edge("investigate", "check_escalation")
    workflow.add_conditional_edges("check_escalation", _route_after_escalation, {"build_report": "build_report", "decide": "decide"})
    workflow.add_edge("decide", "build_report")
    workflow.add_edge("build_report", END)
    return workflow.compile()


def run_pipeline(incident_id: str, payload: dict | None = None) -> dict:
    """Run the pipeline and return final state (includes report)."""
    graph = build_graph()
    initial: AgentState = {
        "incident_id": incident_id,
        "payload": payload or {},
    }
    result = graph.invoke(initial)
    return result
