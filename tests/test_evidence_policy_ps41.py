from __future__ import annotations

from apps.agent.nodes import (
    _evaluate_evidence_policy,
    _normalize_plan_steps,
    act,
    report,
)


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


def test_ps41_evidence_policy_rejects_missing_model_grounding_not_autofilled():
    """PS4.1: auto-fill must not mask steps that omit doc_ids/snippet_ids."""
    citations = [{"doc_id": "rb-power", "snippet_id": "s1", "content": "note"}]
    plan = [
        {
            "action": "Change thermal setpoint",
            "action_type": "change_config",
            "safe": False,
        }
    ]
    _normalize_plan_steps(plan, ["rb-power"], ["s1"], fill_grounding=False)
    ok, reason, detail = _evaluate_evidence_policy(
        {"citations": citations, "plan": plan}
    )
    assert ok is False
    assert reason == "evidence_policy_violation"
    assert "no grounding" in detail.lower()

    # Legacy fill_grounding=True would have bypassed policy — must not be used pre-check.
    plan2 = [
        {
            "action": "Change thermal setpoint",
            "action_type": "change_config",
            "safe": False,
        }
    ]
    _normalize_plan_steps(plan2, ["rb-power"], ["s1"], fill_grounding=True)
    ok2, _, _ = _evaluate_evidence_policy({"citations": citations, "plan": plan2})
    assert ok2 is True


def test_ps41_act_blocks_before_execution_when_plan_ungrounded():
    state = {
        "incident_id": "ps41-act",
        "trace_id": "a" * 32,
        "escalated": False,
        "citations": [{"doc_id": "rb-power", "snippet_id": "s1"}],
        "plan": [
            {
                "action": "Apply config",
                "action_type": "change_config",
                "safe": False,
            }
        ],
    }
    out = act(state)
    assert out.get("escalated") is True
    assert out.get("evidence_policy_status") == "violation"
    assert (out.get("escalation_packet") or {}).get(
        "reason"
    ) == "evidence_policy_violation"
    assert out.get("act_results") == []
    assert out.get("approval_requests") == []


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
