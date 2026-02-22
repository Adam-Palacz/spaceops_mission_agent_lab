"""
SpaceOps Agent — LangGraph pipeline: Triage → Investigate → Decide → Report (S1.7).
No Act node yet.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from apps.agent.state import AgentState
from apps.agent.nodes import triage, investigate, decide, report as report_node_fn


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("triage", triage)
    workflow.add_node("investigate", investigate)
    workflow.add_node("decide", decide)
    workflow.add_node("build_report", report_node_fn)
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "investigate")
    workflow.add_edge("investigate", "decide")
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
