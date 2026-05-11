from __future__ import annotations

from apps.agent.nodes import report


def test_ps41_evidence_policy_passes_for_grounded_non_report_steps():
    state = {
        "incident_id": "ps41-pass",
        "subsystem": "Power",
        "risk": "medium",
        "hypotheses": ["Telemetry indicates voltage ripple."],
        "citations": [
            {"doc_id": "rb-power", "snippet_id": "s1", "content": "Power runbook note."}
        ],
        "plan": [
            {
                "action": "Create ticket for power team",
                "action_type": "create_ticket",
                "safe": True,
                "doc_ids": ["rb-power"],
                "snippet_ids": ["s1"],
            }
        ],
        "escalated": False,
        "trace_id": "a" * 32,
    }
    out = report(state)
    rep = out.get("report") or {}
    assert out.get("escalated") is False
    assert not rep.get("escalation_packet")
    assert out.get("evidence_policy_status") == "ok"


def test_ps41_evidence_policy_escalates_on_unsupported_citations():
    state = {
        "incident_id": "ps41-fail",
        "subsystem": "Power",
        "risk": "high",
        "hypotheses": ["Potential anomaly detected."],
        "citations": [
            {"doc_id": "rb-power", "snippet_id": "s1", "content": "Power runbook note."}
        ],
        "plan": [
            {
                "action": "Open PR changing threshold",
                "action_type": "create_pr",
                "safe": True,
                "doc_ids": ["rb-unknown"],
                "snippet_ids": [],
            }
        ],
        "escalated": False,
        "trace_id": "a" * 32,
    }
    out = report(state)
    rep = out.get("report") or {}
    packet = rep.get("escalation_packet") or {}
    assert out.get("escalated") is True
    assert packet.get("reason") == "evidence_policy_violation"
    assert out.get("evidence_policy_status") == "violation"
    assert out.get("evidence_policy_reason") == "evidence_policy_violation"
