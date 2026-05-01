from __future__ import annotations

from typing import Any

from apps.agent.nodes import _should_escalate, check_escalation, report


def test_should_escalate_on_tool_failure():
    state: dict[str, Any] = {
        "incident_id": "ps17-tool-failure",
        "subsystem": "Power",
        "risk": "medium",
        "hypotheses": ["Telemetry retrieval failed due to timeout."],
        "citations": [],
        "tool_outcomes": {
            "query_telemetry": "failure",
            "search_runbooks": "empty",
            "search_postmortems": "empty",
        },
    }
    escalate, reason = _should_escalate(state)
    assert escalate is True
    assert reason == "tool_failure"

    result = check_escalation(state)
    assert result["escalated"] is True
    assert (result.get("escalation_packet") or {}).get("reason") == "tool_failure"


def test_should_escalate_on_conflicting_signals():
    state: dict[str, Any] = {
        "incident_id": "ps17-conflict",
        "subsystem": "Thermal",
        "risk": "high",
        "hypotheses": [
            "Telemetry anomaly detected on radiator loop.",
            "Runbook says values are nominal and stable.",
        ],
        "citations": [{"doc_id": "rb-thermal", "snippet_id": "s1"}],
    }
    escalate, reason = _should_escalate(state)
    assert escalate is True
    assert reason == "conflicting_signals"


def test_report_schema_accepts_escalation_packet():
    state: dict[str, Any] = {
        "incident_id": "ps17-report",
        "subsystem": "Ground",
        "risk": "high",
        "hypotheses": ["No telemetry or KB hits; escalate for manual review."],
        "citations": [],
        "plan": [{"action": "Escalate to ops", "action_type": "report", "safe": True}],
        "escalated": True,
        "escalation_packet": {
            "reason": "no_evidence",
            "what_we_know": ["Incident ps17-report"],
            "what_we_dont_know": ["Insufficient evidence"],
            "what_to_check": ["Review logs"],
        },
        "trace_id": "ps17traceid",
    }
    out = report(state)
    rep = out.get("report") or {}
    assert rep.get("incident_id") == "ps17-report"
    assert (rep.get("escalation_packet") or {}).get("reason") == "no_evidence"
